"""Extract stage executor - structured data extraction from papers.

IMPORTANT: Uses FULL TEXT by default per PRD requirements.

Supports cost mode configuration for quality/cost trade-offs.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.agents.extractor import DataExtractionAgent
from arakis.config import ModeConfig
from arakis.extraction.schemas import detect_schema, get_schema
from arakis.models.paper import Paper, PaperSource
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class ExtractStageExecutor(BaseStageExecutor):
    """Extract structured data from papers.

    Uses AI to extract study characteristics, outcomes, and other
    structured data from paper full text.

    FULL TEXT extraction is ENABLED by default in all modes.
    Uses cost mode configuration for triple/single review selection.
    """

    STAGE_NAME = "extract"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.extractor = DataExtractionAgent(mode_config=self.mode_config)
        logger.info(
            f"[extract] Using model: {self.mode_config.extraction_model}, "
            f"triple_review: {self.mode_config.extraction_triple_review}"
        )

    def get_required_stages(self) -> list[str]:
        """Extract requires search, screen, and pdf_fetch."""
        return ["search", "screen", "pdf_fetch"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute data extraction.

        Args:
            input_data: Should contain:
                - papers: list of paper dicts with full_text from pdf_fetch
                - schema: str (auto, rct, cohort, case_control, diagnostic)
                - fast_mode: bool (default False, enables single-pass extraction)
                - use_full_text: bool (default True - ENABLED by default)
                - research_question: str (for auto schema detection)
                - inclusion_criteria: list[str] (for auto schema detection)

        Returns:
            StageResult with extraction results
        """
        papers_data = input_data.get("papers", [])
        schema_name = input_data.get("schema", "auto")
        fast_mode = input_data.get("fast_mode", False)
        use_full_text = input_data.get("use_full_text", True)  # DEFAULT: True
        research_question = input_data.get("research_question", "")
        inclusion_criteria = input_data.get("inclusion_criteria", [])

        # Filter to papers with data (either full text or abstract)
        papers_with_text = [p for p in papers_data if p.get("has_full_text") or p.get("abstract")]
        papers_without_text = [
            p for p in papers_data if not (p.get("has_full_text") or p.get("abstract"))
        ]

        if papers_without_text:
            logger.warning(
                f"[extract] {len(papers_without_text)} papers have no text and will be skipped: "
                f"{[p['id'] for p in papers_without_text[:5]]}"
            )

        if not papers_with_text:
            return StageResult(
                success=False,
                error="No papers with text available for extraction",
            )

        # Auto-detect schema if needed
        if schema_name == "auto":
            detection_text = f"{research_question} {' '.join(inclusion_criteria)}"
            detected_schema, confidence = detect_schema(detection_text)
            schema_name = detected_schema
            logger.info(
                f"[extract] Auto-detected schema: {schema_name} (confidence: {confidence:.0%})"
            )

        try:
            extraction_schema = get_schema(schema_name)
        except ValueError as e:
            return StageResult(
                success=False,
                error=f"Invalid schema: {e}",
            )

        # Convert to Paper objects with full text
        papers = []
        for p in papers_with_text:
            paper = Paper(
                id=p["id"],
                title=p.get("title", ""),
                abstract=p.get("abstract"),
                doi=p.get("doi"),
                source=PaperSource(p.get("source", "pubmed")),
            )
            if p.get("full_text") and use_full_text:
                paper.full_text = p["full_text"]
            papers.append(paper)

        logger.info(
            f"[extract] Extracting from {len(papers)} papers "
            f"(schema={schema_name}, full_text={use_full_text}, "
            f"triple_review={not fast_mode})"
        )

        # Update workflow stage
        await self.update_workflow_stage("extract")
        await self.save_checkpoint("in_progress")

        try:
            # Run extraction - USE FULL TEXT by default
            extraction_result = await self.extractor.extract_batch(
                papers=papers,
                schema=extraction_schema,
                triple_review=not fast_mode,
                use_full_text=use_full_text,  # DEFAULT: True
                progress_callback=self._progress_callback,
            )

            # Build output data
            output_data = {
                "total_papers": extraction_result.total_papers,
                "successful": extraction_result.successful_extractions,
                "failed": extraction_result.failed_extractions,
                "average_quality": extraction_result.average_quality,
                "schema_used": schema_name,
                "extractions": [
                    {
                        "paper_id": e.paper_id,
                        "data": e.data,
                        "confidence": e.confidence,
                        "extraction_quality": e.extraction_quality,
                        "needs_human_review": e.needs_human_review,
                        "low_confidence_fields": e.low_confidence_fields,
                    }
                    for e in extraction_result.extractions
                ],
            }

            logger.info(
                f"[extract] Completed: {extraction_result.successful_extractions}/"
                f"{extraction_result.total_papers} successful, "
                f"quality={extraction_result.average_quality:.2f}"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=extraction_result.estimated_cost,
            )

        except Exception as e:
            logger.exception(f"[extract] Extraction failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _progress_callback(self, current: int, total: int):
        """Log extraction progress."""
        if current % 3 == 0 or current == total:
            logger.info(f"[extract] Progress: {current}/{total} papers extracted")
