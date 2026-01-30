"""Search stage executor - multi-database literature search."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import ModeConfig
from arakis.orchestrator import SearchOrchestrator
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class SearchStageExecutor(BaseStageExecutor):
    """Execute literature search across multiple databases.

    Searches PubMed, OpenAlex, Semantic Scholar, and other databases
    using AI-generated queries optimized for each database.
    """

    STAGE_NAME = "search"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.orchestrator = SearchOrchestrator()

    def get_required_stages(self) -> list[str]:
        """Search is the first stage - no dependencies."""
        return []

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute literature search.

        Args:
            input_data: Should contain:
                - research_question: str
                - databases: list[str] (e.g., ["pubmed", "openalex"])
                - max_results_per_query: int (default 100)

        Returns:
            StageResult with papers found
        """
        research_question = input_data.get("research_question")
        databases = input_data.get("databases", ["pubmed", "openalex"])
        max_results = input_data.get("max_results_per_query", 100)

        if not research_question:
            return StageResult(
                success=False,
                error="Missing research_question in input_data",
            )

        logger.info(f"[search] Searching {databases} for: {research_question[:100]}...")

        # Update workflow stage
        await self.update_workflow_stage("search")
        await self.save_checkpoint("in_progress")

        try:
            # Initialize progress tracker
            progress_tracker = await self.init_progress_tracker()
            progress_tracker.set_stage_data({
                "phase": "generating_queries",
                "databases_completed": [],
                "queries": {},
                "results_per_database": {},
            })

            # Create progress callback for orchestrator
            async def search_progress_callback(stage: str, detail: str):
                """Handle progress updates from orchestrator."""
                if stage == "query_generation":
                    await progress_tracker.emit_phase_change(
                        "generating_queries",
                        {"thought_process": detail}
                    )
                elif stage == "searching":
                    # Extract database name from detail if available
                    db_name = detail.split()[0] if detail else None
                    progress_tracker.set_stage_data({
                        "phase": "searching",
                        "current_database": db_name,
                    })
                    await progress_tracker.emit_thought(f"Searching {db_name}...")
                elif stage == "database_complete":
                    # Detail format: "database_name: N results"
                    parts = detail.split(":")
                    if len(parts) >= 2:
                        db_name = parts[0].strip()
                        try:
                            count = int(parts[1].strip().split()[0])
                            progress_tracker._stage_data.setdefault("databases_completed", []).append(db_name)
                            progress_tracker._stage_data.setdefault("results_per_database", {})[db_name] = count
                        except (ValueError, IndexError):
                            pass
                elif stage == "deduplication":
                    await progress_tracker.emit_phase_change(
                        "deduplicating",
                        {"thought_process": "Removing duplicate papers..."}
                    )

            # Run comprehensive search with progress tracking
            search_result = await self.orchestrator.comprehensive_search(
                research_question=research_question,
                databases=databases,
                max_results_per_query=max_results,
                validate_queries=False,  # Skip validation for speed
                progress_callback=search_progress_callback,
            )

            # Finalize progress
            await self.finalize_progress()

            # Update workflow with paper count
            workflow = await self.get_workflow()
            workflow.papers_found = len(search_result.papers)
            await self.db.commit()

            # Build output data
            output_data = {
                "papers_found": len(search_result.papers),
                "duplicates_removed": search_result.prisma_flow.duplicates_removed,
                "records_identified": dict(search_result.prisma_flow.records_identified),
                "papers": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "doi": p.doi,
                        "pmid": p.pmid,
                        "year": p.year,
                        "source": p.source.value if hasattr(p.source, "value") else str(p.source),
                        "abstract": p.abstract[:500] if p.abstract else None,
                    }
                    for p in search_result.papers
                ],
            }

            logger.info(
                f"[search] Found {len(search_result.papers)} unique papers "
                f"(removed {search_result.prisma_flow.duplicates_removed} duplicates)"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.10,  # Estimate for query generation
            )

        except Exception as e:
            logger.exception(f"[search] Search failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )
