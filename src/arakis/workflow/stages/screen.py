"""Screen stage executor - AI-powered paper screening.

IMPORTANT: This stage processes ALL papers - no artificial limit.
The previous 50-paper limit has been removed per PRD requirements.

Supports cost mode configuration for quality/cost trade-offs.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.agents.screener import ScreeningAgent
from arakis.config import ModeConfig
from arakis.models.paper import Author, Paper, PaperSource
from arakis.models.screening import ScreeningCriteria
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class ScreenStageExecutor(BaseStageExecutor):
    """Execute AI-powered paper screening.

    Screens ALL papers against inclusion/exclusion criteria.
    NO ARTIFICIAL LIMIT - processes every paper found.

    Uses cost mode configuration for dual/single review selection.
    """

    STAGE_NAME = "screen"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.screener = ScreeningAgent(mode_config=self.mode_config)
        logger.info(
            f"[screen] Using model: {self.mode_config.screening_model}, "
            f"dual_review: {self.mode_config.screening_dual_review}"
        )

    def get_required_stages(self) -> list[str]:
        """Screen requires search to be completed."""
        return ["search"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute paper screening.

        Args:
            input_data: Should contain:
                - papers: list of paper dicts from search stage
                - inclusion_criteria: list[str]
                - exclusion_criteria: list[str]
                - fast_mode: bool (default False, enables single-pass screening)

        Returns:
            StageResult with screening decisions
        """
        papers_data = input_data.get("papers", [])
        inclusion_criteria = input_data.get("inclusion_criteria", [])
        exclusion_criteria = input_data.get("exclusion_criteria", [])
        fast_mode = input_data.get("fast_mode", False)

        if not papers_data:
            return StageResult(
                success=False,
                error="No papers to screen",
            )

        if not inclusion_criteria:
            return StageResult(
                success=False,
                error="Missing inclusion_criteria",
            )

        # Convert paper dicts to Paper objects
        papers = []
        for p in papers_data:
            authors = []
            if p.get("authors"):
                for a in p["authors"]:
                    if isinstance(a, dict):
                        authors.append(Author(name=a.get("name", "Unknown")))
                    else:
                        authors.append(Author(name=str(a)))

            paper = Paper(
                id=p["id"],
                title=p.get("title", ""),
                abstract=p.get("abstract"),
                year=p.get("year"),
                authors=authors,
                doi=p.get("doi"),
                pmid=p.get("pmid"),
                source=PaperSource(p.get("source", "pubmed")),
            )
            papers.append(paper)

        # IMPORTANT: NO LIMIT - process ALL papers
        # The old code had: max_screen = min(len(papers), 50)
        # This has been REMOVED per PRD requirements
        total_papers = len(papers)

        logger.info(f"[screen] Screening ALL {total_papers} papers (dual_review={not fast_mode})")

        # Update workflow stage
        await self.update_workflow_stage("screen")
        await self.save_checkpoint("in_progress")

        try:
            criteria = ScreeningCriteria(
                inclusion=inclusion_criteria,
                exclusion=exclusion_criteria,
            )

            # Screen ALL papers with progress tracking
            decisions = await self.screener.screen_batch(
                papers=papers,
                criteria=criteria,
                dual_review=not fast_mode,
                human_review=False,
                progress_callback=self._progress_callback,
            )

            # Summarize results
            summary = self.screener.summarize_screening(decisions)

            # Update workflow stats
            workflow = await self.get_workflow()
            workflow.papers_screened = len(decisions)
            workflow.papers_included = summary["included"]
            await self.db.commit()

            # Build output data
            output_data = {
                "total_screened": len(decisions),
                "included": summary["included"],
                "excluded": summary["excluded"],
                "maybe": summary["maybe"],
                "conflicts": summary.get("conflicts", 0),
                "decisions": [
                    {
                        "paper_id": d.paper_id,
                        "status": d.status.value,
                        "reason": d.reason,
                        "confidence": d.confidence,
                        "matched_inclusion": d.matched_inclusion,
                        "matched_exclusion": d.matched_exclusion,
                        "is_conflict": d.is_conflict,
                    }
                    for d in decisions
                ],
                "included_paper_ids": [
                    d.paper_id for d in decisions if d.status.value == "INCLUDE"
                ],
            }

            # Estimate cost: ~$0.02 per paper for dual review
            cost_per_paper = 0.04 if not fast_mode else 0.02
            total_cost = len(decisions) * cost_per_paper

            logger.info(
                f"[screen] Completed screening: "
                f"{summary['included']} included, "
                f"{summary['excluded']} excluded, "
                f"{summary['maybe']} maybe"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=total_cost,
            )

        except Exception as e:
            logger.exception(f"[screen] Screening failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _progress_callback(self, current: int, total: int, paper: Paper, decision):
        """Log screening progress."""
        if current % 10 == 0 or current == total:
            logger.info(
                f"[screen] Progress: {current}/{total} papers screened ({current * 100 // total}%)"
            )
