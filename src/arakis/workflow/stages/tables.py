"""Tables stage executor - generates manuscript tables.

Generates:
- Study characteristics table
- Risk of Bias summary table
- GRADE Summary of Findings table
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import ModeConfig
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class TablesStageExecutor(BaseStageExecutor):
    """Generate all manuscript tables.

    Creates:
    1. Table 1: Study Characteristics
    2. Table 2: Risk of Bias Summary
    3. Table 3: GRADE Summary of Findings
    """

    STAGE_NAME = "tables"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)

    def get_required_stages(self) -> list[str]:
        """Tables require extraction, RoB, and analysis."""
        return ["search", "screen", "pdf_fetch", "extract", "rob", "analysis"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute table generation.

        Args:
            input_data: Should contain:
                - extractions: list of extraction dicts
                - rob_summary: dict with RoB assessment results
                - analysis_results: dict with meta-analysis results
                - schema_used: str (rct, cohort, etc.)

        Returns:
            StageResult with table data
        """
        extractions = input_data.get("extractions", [])
        rob_summary = input_data.get("rob_summary", {})
        analysis_results = input_data.get("analysis_results", {})
        schema_used = input_data.get("schema_used", "rct")

        logger.info(f"[tables] Generating tables for {len(extractions)} studies")

        # Update workflow stage
        await self.update_workflow_stage("tables")
        await self.save_checkpoint("in_progress")

        try:
            tables_generated = []

            # Table 1: Study Characteristics
            characteristics_table = self._generate_characteristics_table(
                extractions, schema_used
            )
            await self.save_table(
                table_type="study_characteristics",
                headers=characteristics_table["headers"],
                rows=characteristics_table["rows"],
                title="Table 1. Characteristics of Included Studies",
                caption="Summary of study characteristics for included studies.",
                footnotes=characteristics_table.get("footnotes", []),
            )
            tables_generated.append("study_characteristics")

            # Table 2: Risk of Bias Summary
            if rob_summary and rob_summary.get("assessments"):
                rob_table = self._generate_rob_table(rob_summary)
                await self.save_table(
                    table_type="risk_of_bias",
                    headers=rob_table["headers"],
                    rows=rob_table["rows"],
                    title="Table 2. Risk of Bias Assessment",
                    caption=f"Risk of bias assessed using {rob_summary.get('tool_used', 'appropriate tool')}.",
                    footnotes=rob_table.get("footnotes", []),
                )
                tables_generated.append("risk_of_bias")

            # Table 3: GRADE Summary of Findings
            if analysis_results and analysis_results.get("meta_analysis_feasible"):
                grade_table = self._generate_grade_table(
                    analysis_results, rob_summary, extractions
                )
                await self.save_table(
                    table_type="grade_sof",
                    headers=grade_table["headers"],
                    rows=grade_table["rows"],
                    title="Table 3. GRADE Summary of Findings",
                    caption="Summary of findings and certainty of evidence assessment.",
                    footnotes=grade_table.get("footnotes", []),
                )
                tables_generated.append("grade_sof")

            output_data = {
                "tables_generated": tables_generated,
                "characteristics_table": characteristics_table,
            }

            if "risk_of_bias" in tables_generated:
                output_data["rob_table"] = rob_table

            if "grade_sof" in tables_generated:
                output_data["grade_table"] = grade_table

            logger.info(f"[tables] Generated {len(tables_generated)} tables")

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.0,  # No LLM cost for table generation
            )

        except Exception as e:
            logger.exception(f"[tables] Table generation failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _generate_characteristics_table(
        self, extractions: list[dict], schema_used: str
    ) -> dict:
        """Generate study characteristics table."""
        # Define headers based on schema
        if schema_used == "rct":
            headers = [
                "Study",
                "Year",
                "Country",
                "Design",
                "N",
                "Intervention",
                "Control",
                "Outcomes",
                "Follow-up",
            ]
        elif schema_used == "cohort":
            headers = [
                "Study",
                "Year",
                "Country",
                "Design",
                "N",
                "Exposure",
                "Comparator",
                "Outcomes",
                "Follow-up",
            ]
        elif schema_used == "diagnostic":
            headers = [
                "Study",
                "Year",
                "Country",
                "N",
                "Index Test",
                "Reference Standard",
                "Target Condition",
            ]
        else:
            headers = [
                "Study",
                "Year",
                "Country",
                "Design",
                "N",
                "Intervention/Exposure",
                "Comparator",
                "Outcomes",
            ]

        rows = []
        for e in extractions:
            data = e.get("data", {})
            paper_id = e.get("paper_id", "Unknown")

            row = self._extract_row_data(data, schema_used, paper_id)
            rows.append(row)

        # Sort by year descending
        rows.sort(key=lambda r: r[1] if len(r) > 1 else "", reverse=True)

        return {
            "headers": headers,
            "rows": rows,
            "footnotes": [
                "N = sample size",
                "NR = not reported",
            ],
        }

    def _extract_row_data(self, data: dict, schema_used: str, paper_id: str) -> list:
        """Extract row data based on schema."""
        study_name = data.get("first_author", paper_id.split("_")[0] if "_" in paper_id else paper_id)
        year = str(data.get("publication_year", "NR"))
        country = data.get("country", "NR")
        design = data.get("study_design", "NR")
        n = str(data.get("sample_size_total", "NR"))

        if schema_used == "rct":
            intervention = data.get("intervention_description", "NR")
            control = data.get("control_description", "NR")
            outcomes = data.get("primary_outcome", "NR")
            followup = data.get("follow_up_duration", "NR")
            return [study_name, year, country, design, n, intervention, control, outcomes, followup]

        elif schema_used == "cohort":
            exposure = data.get("exposure_description", "NR")
            comparator = data.get("comparator_description", "NR")
            outcomes = data.get("primary_outcome", "NR")
            followup = data.get("follow_up_duration", "NR")
            return [study_name, year, country, design, n, exposure, comparator, outcomes, followup]

        elif schema_used == "diagnostic":
            index_test = data.get("index_test", "NR")
            reference = data.get("reference_standard", "NR")
            target = data.get("target_condition", "NR")
            return [study_name, year, country, n, index_test, reference, target]

        else:
            intervention = data.get("intervention_description", data.get("exposure_description", "NR"))
            comparator = data.get("control_description", data.get("comparator_description", "NR"))
            outcomes = data.get("primary_outcome", "NR")
            return [study_name, year, country, design, n, intervention, comparator, outcomes]

    def _generate_rob_table(self, rob_summary: dict) -> dict:
        """Generate Risk of Bias summary table."""
        tool_used = rob_summary.get("tool_used", "RoB 2")
        assessments = rob_summary.get("assessments", [])

        # Define headers based on tool
        if tool_used == "rob2":
            headers = [
                "Study",
                "D1: Randomization",
                "D2: Deviations",
                "D3: Missing Data",
                "D4: Measurement",
                "D5: Selection",
                "Overall",
            ]
        elif tool_used == "robins_i":
            headers = [
                "Study",
                "D1: Confounding",
                "D2: Selection",
                "D3: Classification",
                "D4: Deviations",
                "D5: Missing Data",
                "D6: Measurement",
                "D7: Selection of Results",
                "Overall",
            ]
        elif tool_used == "quadas2":
            headers = [
                "Study",
                "Patient Selection",
                "Index Test",
                "Reference Standard",
                "Flow and Timing",
                "Overall",
            ]
        else:
            headers = ["Study", "Overall Risk"]

        rows = []
        for a in assessments:
            study_id = a.get("study_id", "Unknown")
            overall = a.get("overall_judgment", "unclear")

            # Get domain judgments
            domains = a.get("domains", [])
            domain_judgments = [d.get("judgment", "unclear") for d in domains]

            if len(headers) > 2:
                row = [study_id] + domain_judgments + [overall]
                # Pad if needed
                while len(row) < len(headers):
                    row.insert(-1, "NR")
            else:
                row = [study_id, overall]

            rows.append(row)

        return {
            "headers": headers,
            "rows": rows,
            "footnotes": [
                "Green/Low = Low risk of bias",
                "Yellow/Some concerns = Some concerns",
                "Red/High = High risk of bias",
            ],
        }

    def _generate_grade_table(
        self, analysis_results: dict, rob_summary: dict, extractions: list
    ) -> dict:
        """Generate GRADE Summary of Findings table."""
        headers = [
            "Outcome",
            "№ of Studies",
            "№ of Participants",
            "Effect Estimate (95% CI)",
            "Certainty",
            "Comments",
        ]

        rows = []

        # Primary outcome from meta-analysis
        if analysis_results.get("meta_analysis_feasible"):
            n_studies = analysis_results.get("studies_included", 0)
            n_participants = analysis_results.get("total_sample_size", 0)
            pooled = analysis_results.get("pooled_effect", 0)
            ci = analysis_results.get("confidence_interval", {})
            ci_lower = ci.get("lower", 0)
            ci_upper = ci.get("upper", 0)
            effect_measure = analysis_results.get("effect_measure", "MD")

            # Format effect estimate
            if effect_measure in ["OR", "RR", "HR"]:
                effect_str = f"{pooled:.2f} ({ci_lower:.2f} to {ci_upper:.2f})"
            else:
                effect_str = f"{pooled:.2f} ({ci_lower:.2f} to {ci_upper:.2f})"

            # Determine certainty based on RoB and heterogeneity
            certainty = self._assess_grade_certainty(analysis_results, rob_summary)

            # Comments based on heterogeneity
            heterogeneity = analysis_results.get("heterogeneity", {})
            i_squared = heterogeneity.get("i_squared", 0)
            comments = []
            if i_squared > 75:
                comments.append("Substantial heterogeneity")
            elif i_squared > 50:
                comments.append("Moderate heterogeneity")

            if analysis_results.get("is_significant"):
                comments.append("Statistically significant")
            else:
                comments.append("Not statistically significant")

            rows.append([
                "Primary outcome",
                str(n_studies),
                str(n_participants),
                effect_str,
                certainty,
                "; ".join(comments) if comments else "-",
            ])

        return {
            "headers": headers,
            "rows": rows,
            "footnotes": [
                "CI: Confidence Interval",
                "Certainty assessed using GRADE approach",
                "⊕⊕⊕⊕ High, ⊕⊕⊕◯ Moderate, ⊕⊕◯◯ Low, ⊕◯◯◯ Very Low",
            ],
        }

    def _assess_grade_certainty(self, analysis_results: dict, rob_summary: dict) -> str:
        """Assess GRADE certainty of evidence."""
        # Start with high certainty for RCTs
        certainty_level = 4  # High

        # Downgrade for risk of bias
        percent_high_risk = rob_summary.get("percent_high_risk", 0)
        if percent_high_risk > 50:
            certainty_level -= 2  # Serious concerns
        elif percent_high_risk > 25:
            certainty_level -= 1

        # Downgrade for heterogeneity
        heterogeneity = analysis_results.get("heterogeneity", {})
        i_squared = heterogeneity.get("i_squared", 0)
        if i_squared > 75:
            certainty_level -= 2
        elif i_squared > 50:
            certainty_level -= 1

        # Downgrade for imprecision (wide CI)
        ci = analysis_results.get("confidence_interval", {})
        ci_width = abs(ci.get("upper", 0) - ci.get("lower", 0))
        pooled = abs(analysis_results.get("pooled_effect", 1))
        if pooled > 0 and ci_width / pooled > 1.5:
            certainty_level -= 1

        # Map to GRADE symbols
        certainty_level = max(1, min(4, certainty_level))
        certainty_map = {
            4: "⊕⊕⊕⊕ High",
            3: "⊕⊕⊕◯ Moderate",
            2: "⊕⊕◯◯ Low",
            1: "⊕◯◯◯ Very Low",
        }

        return certainty_map.get(certainty_level, "⊕⊕◯◯ Low")
