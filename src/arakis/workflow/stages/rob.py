"""Risk of Bias stage executor - automated quality assessment.

Auto-detects appropriate tool based on study design:
- RoB 2: For RCTs
- ROBINS-I: For observational studies
- QUADAS-2: For diagnostic studies
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.analysis.risk_of_bias import RiskOfBiasAssessor, RiskOfBiasTableGenerator
from arakis.models.extraction import ExtractionResult, ExtractedData
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class RiskOfBiasStageExecutor(BaseStageExecutor):
    """Assess Risk of Bias for included studies.

    Auto-detects the appropriate assessment tool:
    - RoB 2 for randomized controlled trials
    - ROBINS-I for cohort/case-control studies
    - QUADAS-2 for diagnostic accuracy studies
    """

    STAGE_NAME = "rob"

    def __init__(self, workflow_id: str, db: AsyncSession):
        super().__init__(workflow_id, db)
        self.assessor = RiskOfBiasAssessor()
        self.table_generator = RiskOfBiasTableGenerator()

    def get_required_stages(self) -> list[str]:
        """RoB requires extraction data."""
        return ["search", "screen", "pdf_fetch", "extract"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute Risk of Bias assessment.

        Args:
            input_data: Should contain:
                - extractions: list of extraction dicts from extract stage
                - schema_used: str (rct, cohort, etc.)

        Returns:
            StageResult with RoB assessments and table
        """
        extractions_data = input_data.get("extractions", [])
        schema_used = input_data.get("schema_used", "rct")

        if not extractions_data:
            return StageResult(
                success=True,
                output_data={
                    "message": "No extractions to assess",
                    "n_studies": 0,
                },
                cost=0.0,
            )

        logger.info(
            f"[rob] Assessing Risk of Bias for {len(extractions_data)} studies "
            f"(schema: {schema_used})"
        )

        # Update workflow stage
        await self.update_workflow_stage("rob")
        await self.save_checkpoint("in_progress")

        try:
            # Convert extraction dicts to ExtractedData objects
            extracted_data_list = []
            for e in extractions_data:
                ed = ExtractedData(
                    paper_id=e["paper_id"],
                    schema_name=e.get("schema_name", schema_used),
                    extraction_method=e.get("extraction_method", "single_pass"),
                    data=e.get("data", {}),
                    confidence=e.get("confidence", {}),
                    extraction_quality=e.get("extraction_quality", 0.5),
                    needs_human_review=e.get("needs_human_review", False),
                )
                extracted_data_list.append(ed)

            # Create ExtractionResult wrapper
            extraction_result = ExtractionResult(
                extractions=extracted_data_list,
                schema_name=schema_used,
            )

            # Auto-detect and run RoB assessment
            rob_summary = self.assessor.assess_studies(extraction_result)

            # Generate RoB table
            rob_table = self.table_generator.generate_table(rob_summary)

            # Save table to database
            await self.save_table(
                table_type="risk_of_bias",
                headers=rob_table.headers,
                rows=rob_table.rows,
                title=rob_table.title,
                caption=rob_table.caption,
                footnotes=rob_table.footnotes,
            )

            # Build output data
            output_data = {
                "n_studies": rob_summary.n_studies,
                "tool_used": rob_summary.tool.value,
                "percent_low_risk": rob_summary.percent_low_risk,
                "percent_high_risk": rob_summary.percent_high_risk,
                "percent_unclear": rob_summary.percent_unclear,
                "assessments": [
                    {
                        "study_id": a.study_id,
                        "overall_judgment": a.overall_judgment.value,
                        "domains": [
                            {
                                "name": d.domain_name,
                                "judgment": d.judgment.value,
                                "support": d.support,
                            }
                            for d in a.domains
                        ],
                    }
                    for a in rob_summary.assessments
                ],
                "table": {
                    "title": rob_table.title,
                    "headers": rob_table.headers,
                    "rows": rob_table.rows,
                    "footnotes": rob_table.footnotes,
                },
            }

            logger.info(
                f"[rob] Completed: {rob_summary.n_studies} studies assessed with "
                f"{rob_summary.tool.value}, "
                f"{rob_summary.percent_low_risk:.0f}% low risk"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.0,  # No LLM cost for RoB (rule-based)
            )

        except Exception as e:
            logger.exception(f"[rob] Assessment failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )
