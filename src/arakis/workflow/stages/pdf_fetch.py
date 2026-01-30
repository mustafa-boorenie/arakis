"""PDF Fetch stage executor - download PDFs and extract text.

IMPORTANT: Text extraction is ENABLED by default per PRD requirements.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import ModeConfig
from arakis.models.paper import Paper, PaperSource
from arakis.retrieval.fetcher import PaperFetcher
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class PDFFetchStageExecutor(BaseStageExecutor):
    """Fetch PDFs and extract full text.

    Downloads PDFs from open access sources (Unpaywall, PMC, arXiv)
    and extracts text for data extraction stage.

    Text extraction is ENABLED by default.
    """

    STAGE_NAME = "pdf_fetch"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.fetcher = PaperFetcher(cache_pdfs=True)

    def get_required_stages(self) -> list[str]:
        """PDF fetch requires search and screening."""
        return ["search", "screen"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Fetch PDFs and extract text.

        Args:
            input_data: Should contain:
                - papers: list of paper dicts from search stage
                - included_paper_ids: list of paper IDs to fetch
                - extract_text: bool (default True - ENABLED by default)

        Returns:
            StageResult with fetch results and extracted text
        """
        papers_data = input_data.get("papers", [])
        included_ids = input_data.get("included_paper_ids", [])
        extract_text = input_data.get("extract_text", True)  # DEFAULT: True

        if not included_ids:
            return StageResult(
                success=True,
                output_data={
                    "pdfs_fetched": 0,
                    "texts_extracted": 0,
                    "message": "No included papers to fetch",
                },
                cost=0.0,
            )

        # Filter to included papers only
        included_papers_data = [p for p in papers_data if p["id"] in included_ids]

        # Convert to Paper objects
        papers = []
        for p in included_papers_data:
            paper = Paper(
                id=p["id"],
                title=p.get("title", ""),
                abstract=p.get("abstract"),
                doi=p.get("doi"),
                pmid=p.get("pmid"),
                pmcid=p.get("pmcid"),
                arxiv_id=p.get("arxiv_id"),
                source=PaperSource(p.get("source", "pubmed")),
            )
            papers.append(paper)

        logger.info(f"[pdf_fetch] Fetching {len(papers)} PDFs (extract_text={extract_text})")

        # Update workflow stage
        await self.update_workflow_stage("pdf_fetch")
        await self.save_checkpoint("in_progress")

        try:
            # Fetch PDFs with text extraction ENABLED by default
            fetch_results = await self.fetcher.fetch_batch(
                papers=papers,
                download=True,
                extract_text=extract_text,  # DEFAULT: True
                progress_callback=self._progress_callback,
            )

            # Count successes
            pdfs_fetched = sum(1 for r in fetch_results if r.success)
            texts_extracted = sum(1 for r in fetch_results if r.success and r.paper.has_full_text)

            # Build output data with extracted text
            papers_with_text = []
            for result in fetch_results:
                paper_data = {
                    "id": result.paper.id,
                    "title": result.paper.title,
                    "pdf_url": result.pdf_url,
                    "success": result.success,
                    "has_full_text": result.paper.has_full_text if result.success else False,
                }
                if result.success and result.paper.has_full_text:
                    paper_data["full_text"] = result.paper.full_text
                    paper_data["text_quality_score"] = result.paper.text_quality_score
                papers_with_text.append(paper_data)

            output_data = {
                "pdfs_fetched": pdfs_fetched,
                "texts_extracted": texts_extracted,
                "success_rate": pdfs_fetched / len(papers) if papers else 0,
                "papers": papers_with_text,
            }

            logger.info(
                f"[pdf_fetch] Fetched {pdfs_fetched}/{len(papers)} PDFs, "
                f"extracted text from {texts_extracted}"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.0,  # No LLM cost for PDF fetch
            )

        except Exception as e:
            logger.exception(f"[pdf_fetch] Fetch failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _progress_callback(self, current: int, total: int, paper: Paper):
        """Log fetch progress."""
        if current % 5 == 0 or current == total:
            logger.info(f"[pdf_fetch] Progress: {current}/{total} papers fetched")
