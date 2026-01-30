"""Methods stage executor - generates methods section.

Generates:
- Protocol and registration
- Eligibility criteria
- Information sources
- Search strategy
- Selection process
- Data collection process
- Data items
- Study risk of bias assessment
- Effect measures
- Synthesis methods
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import ModeConfig
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class MethodsStageExecutor(BaseStageExecutor):
    """Generate methods section of the manuscript.

    Creates PRISMA 2020 compliant methods section with all required subsections:
    - Protocol and registration
    - Eligibility criteria
    - Information sources
    - Search strategy
    - Selection process
    - Data collection process
    - Risk of bias assessment
    - Effect measures
    - Synthesis methods
    """

    STAGE_NAME = "methods"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)

    def get_required_stages(self) -> list[str]:
        """Methods can be written after search and screening setup."""
        return ["search", "screen"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute methods section writing.

        Args:
            input_data: Should contain:
                - research_question: str
                - inclusion_criteria: list[str]
                - exclusion_criteria: list[str]
                - databases_searched: list[str]
                - search_strategy: dict with query details
                - screening_method: str (dual_review, single_pass)
                - extraction_schema: str (rct, cohort, etc.)
                - rob_tool: str (rob2, robins_i, quadas2)
                - analysis_method: str (random_effects, fixed_effects)

        Returns:
            StageResult with methods section
        """
        input_data.get("research_question", "")
        inclusion_criteria = input_data.get("inclusion_criteria", [])
        exclusion_criteria = input_data.get("exclusion_criteria", [])
        databases_searched = input_data.get("databases_searched", [])
        search_strategy = input_data.get("search_strategy", {})
        screening_method = input_data.get("screening_method", "dual_review")
        extraction_schema = input_data.get("extraction_schema", "auto")
        rob_tool = input_data.get("rob_tool", "auto")
        analysis_method = input_data.get("analysis_method", "random_effects")

        logger.info("[methods] Generating methods section")

        # Update workflow stage
        await self.update_workflow_stage("methods")
        await self.save_checkpoint("in_progress")

        try:
            # Initialize progress tracker (methods is template-based so runs fast)
            progress_tracker = await self.init_progress_tracker()
            subsection_names = [
                "protocol", "eligibility", "information_sources", "search_strategy",
                "selection_process", "data_collection", "rob_assessment",
                "effect_measures", "synthesis_methods"
            ]
            progress_tracker.set_stage_data({
                "current_subsection": None,
                "subsections_completed": [],
                "subsections_pending": subsection_names,
                "word_count": 0,
            })

            # Build methods sections
            sections = []

            # 1. Protocol and Registration
            sections.append(
                {
                    "title": "Protocol and Registration",
                    "content": self._write_protocol_section(),
                }
            )

            # 2. Eligibility Criteria
            sections.append(
                {
                    "title": "Eligibility Criteria",
                    "content": self._write_eligibility_section(
                        inclusion_criteria, exclusion_criteria
                    ),
                }
            )

            # 3. Information Sources
            sections.append(
                {
                    "title": "Information Sources",
                    "content": self._write_information_sources(databases_searched),
                }
            )

            # 4. Search Strategy
            sections.append(
                {
                    "title": "Search Strategy",
                    "content": self._write_search_strategy(search_strategy),
                }
            )

            # 5. Selection Process
            sections.append(
                {
                    "title": "Selection Process",
                    "content": self._write_selection_process(screening_method),
                }
            )

            # 6. Data Collection Process
            sections.append(
                {
                    "title": "Data Collection Process",
                    "content": self._write_data_collection(extraction_schema),
                }
            )

            # 7. Risk of Bias Assessment
            sections.append(
                {
                    "title": "Risk of Bias Assessment",
                    "content": self._write_rob_methods(rob_tool, extraction_schema),
                }
            )

            # 8. Effect Measures
            sections.append(
                {
                    "title": "Effect Measures",
                    "content": self._write_effect_measures(extraction_schema),
                }
            )

            # 9. Synthesis Methods
            sections.append(
                {
                    "title": "Synthesis Methods",
                    "content": self._write_synthesis_methods(analysis_method),
                }
            )

            # Combine into full methods section
            full_content = "\n\n".join([f"### {s['title']}\n\n{s['content']}" for s in sections])

            # Calculate word count
            word_count = len(full_content.split())

            # Finalize progress tracking
            progress_tracker.set_stage_data({
                "current_subsection": None,
                "subsections_completed": subsection_names,
                "subsections_pending": [],
                "word_count": word_count,
            })
            await self.finalize_progress()

            output_data = {
                "title": "Methods",
                "content": full_content,
                "subsections": sections,
                "word_count": word_count,
                "markdown": f"## Methods\n\n{full_content}",
            }

            logger.info(f"[methods] Completed: {word_count} words, {len(sections)} subsections")

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.0,  # Template-based, no LLM cost
            )

        except Exception as e:
            logger.exception(f"[methods] Writing failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _write_protocol_section(self) -> str:
        """Write protocol and registration section."""
        return (
            "This systematic review was conducted in accordance with the Preferred "
            "Reporting Items for Systematic Reviews and Meta-Analyses (PRISMA) 2020 "
            "guidelines. The protocol was not registered prior to conducting the review."
        )

    def _write_eligibility_section(self, inclusion: list[str], exclusion: list[str]) -> str:
        """Write eligibility criteria section."""
        parts = []

        if inclusion:
            inc_text = "\n".join([f"- {c}" for c in inclusion])
            parts.append(f"**Inclusion criteria:**\n{inc_text}")

        if exclusion:
            exc_text = "\n".join([f"- {c}" for c in exclusion])
            parts.append(f"**Exclusion criteria:**\n{exc_text}")

        if not parts:
            return "Eligibility criteria were defined based on the research question."

        return "\n\n".join(parts)

    def _write_information_sources(self, databases: list[str]) -> str:
        """Write information sources section."""
        if not databases:
            databases = ["PubMed", "OpenAlex", "Semantic Scholar"]

        db_text = (
            ", ".join(databases[:-1]) + f", and {databases[-1]}"
            if len(databases) > 1
            else databases[0]
        )

        return (
            f"We searched the following electronic databases: {db_text}. "
            "The search was conducted using an AI-assisted systematic review pipeline "
            "that generates database-specific queries optimized with controlled vocabulary "
            "(MeSH terms for PubMed). No date restrictions were applied to the search."
        )

    def _write_search_strategy(self, search_strategy: dict) -> str:
        """Write search strategy section."""
        query = search_strategy.get("query", "")
        pico = search_strategy.get("pico", {})

        parts = [
            "The search strategy was developed using an AI-powered query generator "
            "that extracts PICO elements from the research question and generates "
            "database-specific queries with appropriate Boolean operators and "
            "controlled vocabulary terms."
        ]

        if pico:
            pico_text = []
            if pico.get("population"):
                pico_text.append(f"Population: {pico['population']}")
            if pico.get("intervention"):
                pico_text.append(f"Intervention: {pico['intervention']}")
            if pico.get("comparator"):
                pico_text.append(f"Comparator: {pico['comparator']}")
            if pico.get("outcome"):
                pico_text.append(f"Outcome: {pico['outcome']}")

            if pico_text:
                parts.append("\n\n**PICO elements:**\n" + "\n".join([f"- {p}" for p in pico_text]))

        if query:
            parts.append(f"\n\n**Example search query (PubMed):**\n```\n{query}\n```")

        return "".join(parts)

    def _write_selection_process(self, screening_method: str) -> str:
        """Write selection process section."""
        if screening_method == "dual_review":
            return (
                "Study selection was performed using an AI-assisted dual-review screening process. "
                "Each study was independently evaluated twice using different model parameters "
                "(temperatures 0.3 and 0.7) to ensure reliability. Conflicts between the two "
                "reviews were automatically flagged and resolved conservatively (defaulting to "
                "inclusion for further review). Studies were evaluated against predefined "
                "inclusion and exclusion criteria based on title and abstract."
            )
        else:
            return (
                "Study selection was performed using an AI-assisted single-pass screening process. "
                "Each study was evaluated against predefined inclusion and exclusion criteria "
                "based on title and abstract."
            )

    def _write_data_collection(self, schema: str) -> str:
        """Write data collection process section."""
        schema_desc = {
            "rct": "randomized controlled trials",
            "cohort": "cohort studies",
            "case_control": "case-control studies",
            "diagnostic": "diagnostic accuracy studies",
        }.get(schema, "included studies")

        return (
            f"Data extraction was performed using an AI-assisted triple-review process "
            f"optimized for {schema_desc}. Each study was processed three times using "
            f"different model parameters (temperatures 0.2, 0.5, and 0.8), with majority "
            f"voting used to resolve discrepancies. Extracted data included study "
            f"characteristics, participant demographics, interventions, comparators, "
            f"outcomes, and results. Fields with low agreement were flagged for manual review."
        )

    def _write_rob_methods(self, rob_tool: str, schema: str) -> str:
        """Write risk of bias assessment methods."""
        tool_map = {
            "rob2": "Risk of Bias 2 (RoB 2) tool for randomized trials",
            "robins_i": "Risk Of Bias In Non-randomised Studies of Interventions (ROBINS-I)",
            "quadas2": "Quality Assessment of Diagnostic Accuracy Studies (QUADAS-2)",
        }

        if rob_tool == "auto":
            return (
                "Risk of bias was assessed using the appropriate tool based on study design: "
                "Risk of Bias 2 (RoB 2) for randomized trials, ROBINS-I for non-randomized "
                "studies of interventions, and QUADAS-2 for diagnostic accuracy studies. "
                "The assessment was performed automatically based on extracted study "
                "characteristics, with each domain rated as low risk, some concerns, or high risk."
            )
        else:
            tool_name = tool_map.get(rob_tool, rob_tool)
            return (
                f"Risk of bias was assessed using the {tool_name}. Each domain was rated "
                f"as low risk, some concerns, or high risk of bias based on the extracted "
                f"study characteristics."
            )

    def _write_effect_measures(self, schema: str) -> str:
        """Write effect measures section."""
        if schema == "diagnostic":
            return (
                "For diagnostic accuracy studies, we calculated sensitivity, specificity, "
                "positive and negative likelihood ratios, and diagnostic odds ratios where "
                "sufficient data were available."
            )
        else:
            return (
                "For continuous outcomes, we calculated mean differences (MD) or standardized "
                "mean differences (SMD, Hedges' g) with 95% confidence intervals. For "
                "dichotomous outcomes, we calculated odds ratios (OR) or risk ratios (RR) "
                "with 95% confidence intervals."
            )

    def _write_synthesis_methods(self, analysis_method: str) -> str:
        """Write synthesis methods section."""
        method_desc = {
            "random_effects": "random-effects model using the DerSimonian-Laird method",
            "fixed_effects": "fixed-effects model using inverse variance weighting",
        }.get(analysis_method, "random-effects model")

        return (
            f"Meta-analysis was performed using a {method_desc} when studies were "
            f"sufficiently homogeneous. Statistical heterogeneity was assessed using "
            f"the I² statistic, with values >50% indicating substantial heterogeneity. "
            f"We also calculated τ² (between-study variance) and Cochran's Q statistic. "
            f"Publication bias was assessed using funnel plots and Egger's test when "
            f"≥10 studies were available. Sensitivity analyses included leave-one-out "
            f"analysis to assess the influence of individual studies. Subgroup analyses "
            f"were planned based on study characteristics when sufficient data were available."
        )
