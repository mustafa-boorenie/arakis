"""Results stage executor - generates results section.

Generates:
- Study selection subsection
- Study characteristics subsection
- Risk of bias summary
- Synthesis of results (meta-analysis)
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.agents.results_writer import ResultsWriterAgent
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class ResultsStageExecutor(BaseStageExecutor):
    """Generate results section of the manuscript.

    Creates PRISMA 2020 compliant results section:
    1. Study Selection - PRISMA flow narrative
    2. Study Characteristics - summary of included studies
    3. Risk of Bias - summary of quality assessment
    4. Results of Individual Studies - effect estimates per study
    5. Results of Syntheses - meta-analysis results
    """

    STAGE_NAME = "results"

    def __init__(self, workflow_id: str, db: AsyncSession):
        super().__init__(workflow_id, db)
        self.writer = ResultsWriterAgent()

    def get_required_stages(self) -> list[str]:
        """Results requires all data stages."""
        return ["search", "screen", "pdf_fetch", "extract", "rob", "analysis", "prisma"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute results section writing.

        Args:
            input_data: Should contain:
                - search_results: dict with search summary
                - screening_summary: dict with screening decisions
                - extractions: list of extraction dicts
                - rob_summary: dict with RoB assessment
                - analysis_results: dict with meta-analysis results
                - prisma_flow: dict with PRISMA data

        Returns:
            StageResult with results section
        """
        search_results = input_data.get("search_results", {})
        screening_summary = input_data.get("screening_summary", {})
        extractions = input_data.get("extractions", [])
        rob_summary = input_data.get("rob_summary", {})
        analysis_results = input_data.get("analysis_results", {})
        prisma_flow = input_data.get("prisma_flow", {})

        logger.info(f"[results] Writing results for {len(extractions)} studies")

        # Update workflow stage
        await self.update_workflow_stage("results")
        await self.save_checkpoint("in_progress")

        try:
            sections = []

            # 1. Study Selection
            study_selection = self._write_study_selection(
                search_results, screening_summary, prisma_flow
            )
            sections.append(study_selection)

            # 2. Study Characteristics
            study_characteristics = self._write_study_characteristics(extractions)
            sections.append(study_characteristics)

            # 3. Risk of Bias
            if rob_summary and rob_summary.get("assessments"):
                rob_section = self._write_rob_results(rob_summary)
                sections.append(rob_section)

            # 4. Results of Individual Studies
            if extractions:
                individual_results = self._write_individual_results(extractions)
                sections.append(individual_results)

            # 5. Results of Syntheses (Meta-analysis)
            if analysis_results and analysis_results.get("meta_analysis_feasible"):
                synthesis_results = self._write_synthesis_results(analysis_results)
                sections.append(synthesis_results)
            elif analysis_results:
                # Narrative synthesis if meta-analysis not feasible
                narrative = self._write_narrative_synthesis(
                    analysis_results, extractions
                )
                sections.append(narrative)

            # Combine sections
            full_content = "\n\n".join([
                f"### {s['title']}\n\n{s['content']}" for s in sections
            ])

            word_count = len(full_content.split())

            output_data = {
                "title": "Results",
                "content": full_content,
                "subsections": sections,
                "word_count": word_count,
                "markdown": f"## Results\n\n{full_content}",
                "figures_referenced": [],
                "tables_referenced": [],
            }

            # Track figure and table references
            if analysis_results.get("forest_plot_url"):
                output_data["figures_referenced"].append("forest_plot")
            if analysis_results.get("funnel_plot_url"):
                output_data["figures_referenced"].append("funnel_plot")
            if prisma_flow.get("prisma_url"):
                output_data["figures_referenced"].append("prisma_flow")

            logger.info(
                f"[results] Completed: {word_count} words, {len(sections)} subsections"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.50,  # Estimated LLM cost if writer agent is used
            )

        except Exception as e:
            logger.exception(f"[results] Writing failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _write_study_selection(
        self, search_results: dict, screening_summary: dict, prisma_flow: dict
    ) -> dict:
        """Write study selection section."""
        # Get PRISMA numbers
        identified = prisma_flow.get("flow_data", {}).get(
            "identification", {}
        ).get("records_identified", search_results.get("total_found", 0))

        duplicates = prisma_flow.get("flow_data", {}).get(
            "identification", {}
        ).get("duplicates_removed", search_results.get("duplicates_removed", 0))

        screened = screening_summary.get("total_screened", 0)
        excluded_screening = screening_summary.get("excluded", 0)
        included = screening_summary.get("included", 0)

        content = (
            f"The database search identified {identified:,} records. After removing "
            f"{duplicates:,} duplicates, {screened:,} records were screened based on "
            f"title and abstract. Of these, {excluded_screening:,} records were excluded "
            f"for not meeting inclusion criteria. "
        )

        if included > 0:
            content += (
                f"A total of {included} studies were included in the final analysis. "
                f"The study selection process is summarized in the PRISMA flow diagram (Figure 1)."
            )
        else:
            content += "No studies met all inclusion criteria."

        return {
            "title": "Study Selection",
            "content": content,
        }

    def _write_study_characteristics(self, extractions: list[dict]) -> dict:
        """Write study characteristics section."""
        n_studies = len(extractions)

        if n_studies == 0:
            return {
                "title": "Study Characteristics",
                "content": "No studies were included for data extraction.",
            }

        # Aggregate characteristics
        years = []
        countries = set()
        designs = set()
        total_participants = 0

        for e in extractions:
            data = e.get("data", {})
            if data.get("publication_year"):
                years.append(data["publication_year"])
            if data.get("country"):
                countries.add(data["country"])
            if data.get("study_design"):
                designs.add(data["study_design"])
            if data.get("sample_size_total"):
                total_participants += data["sample_size_total"]

        # Build description
        parts = [f"A total of {n_studies} studies were included in this review."]

        if years:
            year_range = f"{min(years)} to {max(years)}"
            parts.append(f"Studies were published between {year_range}.")

        if countries:
            country_list = ", ".join(sorted(countries)[:5])
            if len(countries) > 5:
                country_list += f", and {len(countries) - 5} other countries"
            parts.append(f"Studies were conducted in {country_list}.")

        if total_participants > 0:
            parts.append(
                f"The total number of participants across all studies was {total_participants:,}."
            )

        if designs:
            design_list = ", ".join(sorted(designs))
            parts.append(f"Study designs included: {design_list}.")

        parts.append(
            "Detailed characteristics of included studies are presented in Table 1."
        )

        return {
            "title": "Study Characteristics",
            "content": " ".join(parts),
        }

    def _write_rob_results(self, rob_summary: dict) -> dict:
        """Write risk of bias results section."""
        n_studies = rob_summary.get("n_studies", 0)
        tool = rob_summary.get("tool_used", "appropriate tool")
        low_risk = rob_summary.get("percent_low_risk", 0)
        high_risk = rob_summary.get("percent_high_risk", 0)
        unclear = rob_summary.get("percent_unclear", 0)

        content = (
            f"Risk of bias was assessed for {n_studies} studies using {tool}. "
            f"Overall, {low_risk:.0f}% of studies were rated as low risk of bias, "
            f"{unclear:.0f}% had some concerns, and {high_risk:.0f}% were rated as "
            f"high risk of bias. "
        )

        # Add domain-specific findings if available
        assessments = rob_summary.get("assessments", [])
        if assessments:
            # Find most problematic domain
            domain_issues = {}
            for a in assessments:
                for d in a.get("domains", []):
                    domain_name = d.get("name", "Unknown")
                    if d.get("judgment") in ["high", "serious"]:
                        domain_issues[domain_name] = domain_issues.get(domain_name, 0) + 1

            if domain_issues:
                worst_domain = max(domain_issues, key=domain_issues.get)
                content += (
                    f"The most common source of bias was in the {worst_domain} domain. "
                )

        content += "The full risk of bias assessment is presented in Table 2."

        return {
            "title": "Risk of Bias in Studies",
            "content": content,
        }

    def _write_individual_results(self, extractions: list[dict]) -> dict:
        """Write results of individual studies section."""
        n_studies = len(extractions)

        # Summarize individual study findings
        content = (
            f"Individual study results are summarized in Table 1. "
            f"Effect estimates and confidence intervals for each study are "
            f"presented in the forest plot (Figure 2)."
        )

        return {
            "title": "Results of Individual Studies",
            "content": content,
        }

    def _write_synthesis_results(self, analysis_results: dict) -> dict:
        """Write synthesis results (meta-analysis) section."""
        n_studies = analysis_results.get("studies_included", 0)
        n_participants = analysis_results.get("total_sample_size", 0)
        pooled = analysis_results.get("pooled_effect", 0)
        ci = analysis_results.get("confidence_interval", {})
        ci_lower = ci.get("lower", 0)
        ci_upper = ci.get("upper", 0)
        p_value = analysis_results.get("p_value", 1)
        effect_measure = analysis_results.get("effect_measure", "MD")
        is_significant = analysis_results.get("is_significant", False)

        # Heterogeneity
        heterogeneity = analysis_results.get("heterogeneity", {})
        i_squared = heterogeneity.get("i_squared", 0)
        tau_squared = heterogeneity.get("tau_squared", 0)
        q_p_value = heterogeneity.get("q_p_value", 1)

        # Format effect estimate
        if effect_measure in ["OR", "RR", "HR"]:
            effect_str = f"{effect_measure} = {pooled:.2f} (95% CI: {ci_lower:.2f}–{ci_upper:.2f})"
        else:
            effect_str = f"{effect_measure} = {pooled:.2f} (95% CI: {ci_lower:.2f}–{ci_upper:.2f})"

        # Statistical significance
        sig_text = "statistically significant" if is_significant else "not statistically significant"

        content = (
            f"Meta-analysis of {n_studies} studies (n = {n_participants:,} participants) "
            f"showed a pooled effect of {effect_str}, which was {sig_text} "
            f"(p = {p_value:.3f}). "
        )

        # Heterogeneity interpretation
        if i_squared > 75:
            het_text = "substantial"
        elif i_squared > 50:
            het_text = "moderate"
        elif i_squared > 25:
            het_text = "low"
        else:
            het_text = "minimal"

        content += (
            f"Heterogeneity across studies was {het_text} "
            f"(I² = {i_squared:.0f}%, τ² = {tau_squared:.3f}, "
            f"Q test p = {q_p_value:.3f}). "
        )

        content += "Results are presented in the forest plot (Figure 2). "

        # Funnel plot if available
        if analysis_results.get("funnel_plot_url"):
            content += (
                "Visual inspection of the funnel plot (Figure 3) suggested "
                "no obvious publication bias. "
            )

        # Sensitivity analysis
        sensitivity = analysis_results.get("sensitivity_analysis", [])
        if sensitivity:
            content += (
                "Leave-one-out sensitivity analysis showed that the pooled effect "
                "remained consistent when each study was excluded individually, "
                "indicating robustness of the findings. "
            )

        return {
            "title": "Results of Syntheses",
            "content": content,
        }

    def _write_narrative_synthesis(
        self, analysis_results: dict, extractions: list[dict]
    ) -> dict:
        """Write narrative synthesis when meta-analysis not feasible."""
        reason = analysis_results.get("reason", "insufficient data")

        content = (
            f"Quantitative meta-analysis was not performed due to {reason}. "
            f"A narrative synthesis of the {len(extractions)} included studies "
            f"is presented below.\n\n"
        )

        # Add study-by-study summary
        for i, e in enumerate(extractions[:5], 1):  # First 5 studies
            data = e.get("data", {})
            study_name = data.get("first_author", f"Study {i}")
            year = data.get("publication_year", "")
            outcome = data.get("primary_outcome_result", "reported outcomes")

            content += f"**{study_name} ({year})**: {outcome}\n\n"

        if len(extractions) > 5:
            content += f"*{len(extractions) - 5} additional studies summarized in Table 1.*"

        return {
            "title": "Synthesis Without Meta-analysis",
            "content": content,
        }
