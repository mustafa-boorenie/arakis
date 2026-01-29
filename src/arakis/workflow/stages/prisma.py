"""PRISMA stage executor - generates PRISMA 2020 flow diagram.

Generates:
- PRISMA 2020 flow diagram (SVG programmatically generated - NO LLM)
- Flow data for inclusion in manuscript

NOTE: PRISMA is ALWAYS generated programmatically as SVG.
NO LLM is used for PRISMA generation in any mode.
This ensures 100% accuracy and zero API cost.
"""

import logging
import tempfile
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class PRISMAStageExecutor(BaseStageExecutor):
    """Generate PRISMA 2020 flow diagram.

    Creates:
    1. PRISMA flow data from search and screening results
    2. PRISMA 2020 diagram (uploaded to R2)
    """

    STAGE_NAME = "prisma"

    def __init__(self, workflow_id: str, db: AsyncSession):
        super().__init__(workflow_id, db)
        self.diagram_generator = PRISMADiagramGenerator()

    def get_required_stages(self) -> list[str]:
        """PRISMA requires search and screen data."""
        return ["search", "screen"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute PRISMA diagram generation.

        Args:
            input_data: Should contain:
                - search_results: dict with database results
                - screening_summary: dict with screening decisions
                - pdfs_fetched: int (optional)
                - pdfs_failed: int (optional)

        Returns:
            StageResult with PRISMA flow data and diagram URL
        """
        search_results = input_data.get("search_results", {})
        screening_summary = input_data.get("screening_summary", {})
        pdfs_fetched = input_data.get("pdfs_fetched", 0)
        pdfs_failed = input_data.get("pdfs_failed", 0)

        logger.info("[prisma] Generating PRISMA 2020 flow diagram")

        # Update workflow stage
        await self.update_workflow_stage("prisma")
        await self.save_checkpoint("in_progress")

        try:
            # Build PRISMA flow from data
            prisma_flow = self._build_prisma_flow(
                search_results, screening_summary, pdfs_fetched, pdfs_failed
            )

            # Generate diagram in temp directory (SVG format - programmatic, no LLM)
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generate SVG (primary format)
                diagram = self.diagram_generator.generate(
                    prisma_flow, 
                    output_filename="prisma_flow",
                    format="svg"
                )
                
                svg_path = f"{temp_dir}/prisma_flow.svg"
                with open(svg_path, "w") as f:
                    f.write(diagram.svg_content)

                # Upload SVG to R2
                prisma_url = await self.upload_figure_to_r2(
                    svg_path,
                    "prisma_flow",
                    title="PRISMA 2020 Flow Diagram",
                    caption="Flow diagram showing study selection process",
                )

            # Build output data
            output_data = {
                "prisma_url": prisma_url,
                "flow_data": {
                    "identification": {
                        "databases": prisma_flow.databases_searched,
                        "records_identified": prisma_flow.records_identified,
                        "duplicates_removed": prisma_flow.duplicates_removed,
                    },
                    "screening": {
                        "records_screened": prisma_flow.records_screened,
                        "records_excluded": prisma_flow.records_excluded,
                    },
                    "eligibility": {
                        "reports_sought": prisma_flow.reports_sought,
                        "reports_not_retrieved": prisma_flow.reports_not_retrieved,
                        "reports_assessed": prisma_flow.reports_assessed,
                        "reports_excluded": prisma_flow.reports_excluded,
                        "exclusion_reasons": prisma_flow.exclusion_reasons,
                    },
                    "included": {
                        "studies_included": prisma_flow.studies_included,
                        "reports_included": prisma_flow.reports_included,
                    },
                },
            }

            logger.info(
                f"[prisma] Generated PRISMA diagram: "
                f"{prisma_flow.records_identified} identified → "
                f"{prisma_flow.studies_included} included"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.0,  # PROGRAMMATIC - No LLM cost for PRISMA (always SVG, never LLM)
            )

        except Exception as e:
            logger.exception(f"[prisma] Diagram generation failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _build_prisma_flow(
        self,
        search_results: dict,
        screening_summary: dict,
        pdfs_fetched: int,
        pdfs_failed: int,
    ) -> PRISMAFlow:
        """Build PRISMA flow from stage results."""
        # Extract database-level data
        per_database = search_results.get("per_database", {})
        databases_searched = list(per_database.keys()) if per_database else []

        # Calculate totals
        total_identified = sum(
            db.get("total", 0) for db in per_database.values()
        ) if per_database else search_results.get("total_found", 0)

        duplicates_removed = search_results.get("duplicates_removed", 0)
        records_after_dedup = total_identified - duplicates_removed

        # Screening data
        total_screened = screening_summary.get("total_screened", records_after_dedup)
        excluded = screening_summary.get("excluded", 0)
        included = screening_summary.get("included", 0)
        maybe = screening_summary.get("maybe", 0)

        # Eligibility data
        reports_sought = included + maybe  # Papers that passed title/abstract screening
        reports_not_retrieved = pdfs_failed
        reports_assessed = pdfs_fetched

        # Build exclusion reasons from screening decisions
        exclusion_reasons = screening_summary.get("exclusion_reasons", {})
        if not exclusion_reasons and excluded > 0:
            exclusion_reasons = {"Did not meet inclusion criteria": excluded}

        return PRISMAFlow(
            databases_searched=databases_searched,
            records_identified=total_identified,
            duplicates_removed=duplicates_removed,
            records_screened=total_screened,
            records_excluded=excluded,
            reports_sought=reports_sought,
            reports_not_retrieved=reports_not_retrieved,
            reports_assessed=reports_assessed,
            reports_excluded=reports_assessed - included if reports_assessed > included else 0,
            exclusion_reasons=exclusion_reasons,
            studies_included=included,
            reports_included=included,
        )
