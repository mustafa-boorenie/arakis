from __future__ import annotations

"""Waterfall paper fetcher that tries multiple sources."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.arxiv import ArxivSource
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.retrieval.sources.biorxiv import BiorxivSource
from arakis.retrieval.sources.core import CORESource
from arakis.retrieval.sources.crossref import CrossrefSource
from arakis.retrieval.sources.europe_pmc import EuropePMCSource
from arakis.retrieval.sources.pmc import PMCSource
from arakis.retrieval.sources.semantic_scholar import SemanticScholarSource
from arakis.retrieval.sources.unpaywall import UnpaywallSource
from arakis.storage import get_storage_client


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

    Sources are tried in order of preference (optimized for speed and reliability):
    1. bioRxiv/medRxiv - instant DOI check for preprints
    2. arXiv - fast ID lookup for CS/physics preprints
    3. PMC - authoritative for biomedical papers
    4. Europe PMC - broader than US PMC
    5. Unpaywall - best OA aggregator
    6. Semantic Scholar - good CS/interdisciplinary coverage
    7. CORE - large repository (250M+ outputs)
    8. Crossref - publisher links as last resort

    The fetcher also checks:
    - Cache (S3/R2) first if configured
    - Pre-populated pdf_url from search phase

    The fetcher stops at the first successful source.
    PDFs can be cached to S3-compatible storage (R2, S3, MinIO).
    """

    def __init__(
        self,
        sources: list[BaseRetrievalSource] | None = None,
        cache_pdfs: bool = True,
    ):
        if sources is None:
            # Optimized waterfall order: fast/reliable sources first
            self.sources = [
                BiorxivSource(),  # Instant DOI check for 10.1101/* DOIs
                ArxivSource(),  # Fast ID-based lookup
                PMCSource(),  # Authoritative for biomedical
                EuropePMCSource(),  # Broader than US PMC
                UnpaywallSource(),  # Best OA aggregator
                SemanticScholarSource(),  # Good CS coverage
                CORESource(),  # Large but slower (requires API key)
                CrossrefSource(),  # Publisher links as last resort
            ]
        else:
            self.sources = sources

        self.cache_pdfs = cache_pdfs
        self._storage = None

    @property
    def storage(self):
        """Lazy-load storage client."""
        if self._storage is None:
            self._storage = get_storage_client()
        return self._storage

    async def fetch(
        self, paper: Paper, download: bool = False, extract_text: bool = False
    ) -> FetchResult:
        """
        Attempt to fetch a paper from multiple sources.

        First checks the cache (S3/R2), then falls back to external sources.
        Caches downloaded PDFs for future requests.

        Args:
            paper: Paper to fetch
            download: If True, download the actual content
            extract_text: If True AND download=True, extract text from PDF

        Returns:
            FetchResult with success status and retrieval details
        """
        sources_tried = []
        paper_id = paper.best_identifier or paper.id

        # Check cache first if storage is configured
        if self.cache_pdfs and self.storage.is_configured:
            cached_content, cache_result = self.storage.download_paper_pdf(paper_id)
            if cached_content:
                sources_tried.append("cache")
                # Create a retrieval result from cache
                cache_retrieval = RetrievalResult(
                    success=True,
                    source_name="cache",
                    content=cached_content if download else None,
                    content_url=cache_result.url,
                )
                paper.open_access = True

                # Extract text if requested
                if extract_text and download:
                    await self._extract_text_from_pdf(paper, cached_content)

                return FetchResult(
                    success=True,
                    paper=paper,
                    retrieval_result=cache_retrieval,
                    sources_tried=sources_tried,
                )

        # Check if paper already has a valid PDF URL from search phase
        if paper.pdf_url and paper.open_access:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.head(paper.pdf_url, follow_redirects=True)
                    if response.status_code == 200:
                        sources_tried.append("pre-populated")
                        result = RetrievalResult(
                            success=True,
                            paper_id=paper.id,
                            source_name="pre-populated",
                            content_url=paper.pdf_url,
                            content_type=ContentType.PDF,
                        )

                        # Download if requested
                        if download:
                            pdf_response = await client.get(paper.pdf_url, follow_redirects=True)
                            if pdf_response.status_code == 200:
                                result.content = pdf_response.content

                                # Cache the PDF
                                if self.cache_pdfs and self.storage.is_configured:
                                    self._cache_pdf(paper_id, result.content, "pre-populated")

                        # Extract text if requested
                        if extract_text and download and result.content:
                            await self._extract_text_from_pdf(paper, result.content)

                        return FetchResult(
                            success=True,
                            paper=paper,
                            retrieval_result=result,
                            sources_tried=sources_tried,
                        )
            except Exception:
                pass  # URL validation failed, continue to external sources

        # Try external sources
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

                # Cache the PDF if we downloaded it
                if self.cache_pdfs and download and result.content and self.storage.is_configured:
                    self._cache_pdf(paper_id, result.content, source.name)

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

    def _cache_pdf(self, paper_id: str, content: bytes, source: str) -> None:
        """Cache a PDF to storage (non-blocking, fire-and-forget)."""
        try:
            metadata = {"source": source, "paper_id": paper_id}
            self.storage.upload_paper_pdf(paper_id, content, metadata)
        except Exception:
            # Caching failure shouldn't break the fetch
            pass

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
