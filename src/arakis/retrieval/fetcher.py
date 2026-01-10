from __future__ import annotations
"""Waterfall paper fetcher that tries multiple sources."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, RetrievalResult
from arakis.retrieval.sources.unpaywall import UnpaywallSource
from arakis.retrieval.sources.pmc import PMCSource
from arakis.retrieval.sources.arxiv import ArxivSource


@dataclass
class FetchResult:
    """Result of fetching a paper."""

    success: bool
    paper: Paper
    retrieval_result: RetrievalResult | None = None
    sources_tried: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def pdf_url(self) -> str | None:
        """Get PDF URL if available."""
        if self.retrieval_result and self.retrieval_result.success:
            return self.retrieval_result.content_url
        return None


class PaperFetcher:
    """
    Waterfall fetcher that tries multiple sources to retrieve papers.

    Sources are tried in order of preference:
    1. Unpaywall - finds legal OA versions
    2. PMC - free biomedical papers
    3. arXiv - preprints

    The fetcher stops at the first successful source.
    """

    def __init__(self, sources: list[BaseRetrievalSource] | None = None):
        if sources is None:
            # Default waterfall order
            self.sources = [
                UnpaywallSource(),
                PMCSource(),
                ArxivSource(),
            ]
        else:
            self.sources = sources

    async def fetch(
        self, paper: Paper, download: bool = False, extract_text: bool = False
    ) -> FetchResult:
        """
        Attempt to fetch a paper from multiple sources.

        Args:
            paper: Paper to fetch
            download: If True, download the actual content
            extract_text: If True AND download=True, extract text from PDF

        Returns:
            FetchResult with success status and retrieval details
        """
        sources_tried = []

        for source in self.sources:
            # Check if source can handle this paper
            if not await source.can_retrieve(paper):
                continue

            sources_tried.append(source.name)

            # Try to retrieve
            result = await source.retrieve(paper, download)

            if result.success:
                # Update paper with PDF URL
                if result.content_url:
                    paper.pdf_url = result.content_url
                    paper.open_access = True

                # Extract text from PDF if requested
                if extract_text and download and result.content:
                    await self._extract_text_from_pdf(paper, result.content)

                return FetchResult(
                    success=True,
                    paper=paper,
                    retrieval_result=result,
                    sources_tried=sources_tried,
                )

        # All sources failed
        return FetchResult(
            success=False,
            paper=paper,
            retrieval_result=None,
            sources_tried=sources_tried,
        )

    async def fetch_batch(
        self,
        papers: list[Paper],
        download: bool = False,
        extract_text: bool = False,
        progress_callback: callable = None,
    ) -> list[FetchResult]:
        """
        Fetch multiple papers.

        Args:
            papers: List of papers to fetch
            download: If True, download actual content
            extract_text: If True AND download=True, extract text from PDFs
            progress_callback: Optional callback(current, total, paper)

        Returns:
            List of FetchResults
        """
        results = []

        for i, paper in enumerate(papers):
            result = await self.fetch(paper, download, extract_text)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(papers), paper)

        return results

    def summarize_batch(self, results: list[FetchResult]) -> dict[str, Any]:
        """Summarize batch fetch results."""
        total = len(results)
        successful = sum(1 for r in results if r.success)

        # Count by source
        source_counts: dict[str, int] = {}
        for result in results:
            if result.success and result.retrieval_result:
                source = result.retrieval_result.source_name
                source_counts[source] = source_counts.get(source, 0) + 1

        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "by_source": source_counts,
        }

    async def _extract_text_from_pdf(self, paper: Paper, pdf_content: bytes) -> None:
        """
        Extract text from PDF content and update paper.

        Args:
            paper: Paper to update
            pdf_content: PDF file content as bytes
        """
        try:
            from arakis.text_extraction.pdf_parser import PDFParser

            parser = PDFParser(clean=True, remove_repeating=True)
            result = await parser.extract_text(pdf_content)

            if result.success and result.text:
                paper.full_text = result.text
                paper.full_text_extracted_at = datetime.utcnow()
                paper.text_extraction_method = result.extraction_method
                paper.text_quality_score = result.quality_score
        except Exception:
            # Silently fail - text extraction is optional
            # Paper will still have pdf_url even if extraction fails
            pass
