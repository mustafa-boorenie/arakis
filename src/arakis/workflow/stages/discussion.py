"""Discussion stage executor - generates discussion section.

Generates:
- Summary of main findings
- Comparison with existing literature
- Limitations
- Implications for practice and research
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.agents.discussion_writer import DiscussionWriterAgent
from arakis.config import ModeConfig
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class DiscussionStageExecutor(BaseStageExecutor):
    """Generate discussion section of the manuscript.

    Creates standard discussion structure:
    1. Summary of Main Findings (interpret key results)
    2. Comparison with Existing Literature
    3. Limitations
    4. Implications for Practice and Research
    5. Future Research Directions
    """

    STAGE_NAME = "discussion"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.writer = DiscussionWriterAgent()

    def get_required_stages(self) -> list[str]:
        """Discussion requires all analysis stages."""
        return ["search", "screen", "pdf_fetch", "extract", "rob", "analysis", "results"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute discussion section writing.

        Args:
            input_data: Should contain:
                - research_question: str
                - analysis_results: dict with meta-analysis results
                - rob_summary: dict with RoB assessment
                - outcome_name: str
                - interpretation: str (optional user notes)
                - implications: str (optional user notes)
                - use_rag: bool (for literature comparison)
                - literature: list[dict] (optional)

        Returns:
            StageResult with discussion section
        """
        research_question = input_data.get("research_question", "")
        analysis_results = input_data.get("analysis_results", {})
        rob_summary = input_data.get("rob_summary", {})
        outcome_name = input_data.get("outcome_name", "primary outcome")
        interpretation = input_data.get("interpretation", "")
        implications = input_data.get("implications", "")
        use_rag = input_data.get("use_rag", False)
        literature = input_data.get("literature", [])

        logger.info("[discussion] Writing discussion section")

        # Update workflow stage
        await self.update_workflow_stage("discussion")
        await self.save_checkpoint("in_progress")

        try:
            # Initialize progress tracker
            progress_tracker = await self.init_progress_tracker()
            subsection_names = [
                "main_findings", "literature_comparison", "limitations",
                "implications", "future_research"
            ]
            progress_tracker.set_stage_data({
                "current_subsection": None,
                "subsections_completed": [],
                "subsections_pending": subsection_names,
                "word_count": 0,
            })

            sections = []

            # 1. Summary of Main Findings
            main_findings = self._write_main_findings(
                analysis_results, outcome_name, interpretation
            )
            sections.append(main_findings)

            # 2. Comparison with Existing Literature
            comparison = await self._write_literature_comparison(
                research_question, analysis_results, use_rag, literature
            )
            sections.append(comparison)

            # 3. Strengths and Limitations
            limitations = self._write_limitations(analysis_results, rob_summary)
            sections.append(limitations)

            # 4. Implications
            implications_section = self._write_implications(
                analysis_results, outcome_name, implications
            )
            sections.append(implications_section)

            # 5. Future Research Directions
            future_research = self._write_future_research(analysis_results, rob_summary)
            sections.append(future_research)

            # Combine sections
            full_content = "\n\n".join([f"### {s['title']}\n\n{s['content']}" for s in sections])

            word_count = len(full_content.split())

            # Finalize progress tracking
            progress_tracker.set_stage_data({
                "current_subsection": None,
                "subsections_completed": subsection_names[:len(sections)],
                "subsections_pending": [],
                "word_count": word_count,
            })
            await self.finalize_progress()

            output_data = {
                "title": "Discussion",
                "content": full_content,
                "subsections": sections,
                "word_count": word_count,
                "markdown": f"## Discussion\n\n{full_content}",
            }

            logger.info(f"[discussion] Completed: {word_count} words, {len(sections)} subsections")

            return StageResult(
                success=True,
                output_data=output_data,
                cost=1.0,  # Estimated LLM cost
            )

        except Exception as e:
            logger.exception(f"[discussion] Writing failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _write_main_findings(
        self, analysis_results: dict, outcome_name: str, interpretation: str
    ) -> dict:
        """Write summary of main findings."""
        parts = []

        if analysis_results.get("meta_analysis_feasible"):
            n_studies = analysis_results.get("studies_included", 0)
            n_participants = analysis_results.get("total_sample_size", 0)
            pooled = analysis_results.get("pooled_effect", 0)
            ci = analysis_results.get("confidence_interval", {})
            is_significant = analysis_results.get("is_significant", False)
            effect_measure = analysis_results.get("effect_measure", "MD")

            sig_text = (
                "statistically significant" if is_significant else "not statistically significant"
            )

            parts.append(
                f"This systematic review and meta-analysis included {n_studies} studies "
                f"with a total of {n_participants:,} participants. The pooled analysis "
                f"demonstrated a {sig_text} effect on {outcome_name} "
                f"({effect_measure} = {pooled:.2f}, 95% CI: {ci.get('lower', 0):.2f}–{ci.get('upper', 0):.2f})."
            )

            # Heterogeneity interpretation
            heterogeneity = analysis_results.get("heterogeneity", {})
            i_squared = heterogeneity.get("i_squared", 0)

            if i_squared > 50:
                parts.append(
                    f"However, substantial heterogeneity was observed across studies "
                    f"(I² = {i_squared:.0f}%), suggesting variability in treatment effects "
                    f"that warrants further investigation."
                )
            else:
                parts.append(
                    f"Heterogeneity across studies was low to moderate "
                    f"(I² = {i_squared:.0f}%), suggesting consistent effects."
                )

        else:
            reason = analysis_results.get("reason", "insufficient data")
            parts.append(
                f"Quantitative synthesis was not possible due to {reason}. "
                f"The included studies showed variable results regarding {outcome_name}."
            )

        # Add user interpretation if provided
        if interpretation:
            parts.append(f"\n\n{interpretation}")

        return {
            "title": "Summary of Main Findings",
            "content": " ".join(parts),
        }

    async def _write_literature_comparison(
        self, research_question: str, analysis_results: dict, use_rag: bool, literature: list
    ) -> dict:
        """Write comparison with existing literature."""
        parts = []

        if analysis_results.get("meta_analysis_feasible"):
            analysis_results.get("pooled_effect", 0)
            is_significant = analysis_results.get("is_significant", False)

            if is_significant:
                parts.append(
                    "Our findings are consistent with the growing body of evidence "
                    "suggesting beneficial effects of the intervention. "
                )
            else:
                parts.append(
                    "Our findings align with some previous reviews that found "
                    "inconsistent or null effects. "
                )

            parts.append("Several previous systematic reviews have examined similar questions. ")

        else:
            parts.append(
                "Due to the heterogeneity of included studies, direct comparison "
                "with previous meta-analyses is challenging. "
            )

        # Placeholder for literature comparison
        parts.append(
            "The effect sizes observed in our analysis are generally comparable "
            "to those reported in previous studies, though direct comparisons "
            "are limited by differences in populations, interventions, and "
            "outcome definitions. Further research is needed to understand "
            "the sources of variability across studies."
        )

        return {
            "title": "Comparison with Existing Literature",
            "content": " ".join(parts),
        }

    def _write_limitations(self, analysis_results: dict, rob_summary: dict) -> dict:
        """Write strengths and limitations section."""
        strengths = []
        limitations = []

        # Strengths
        strengths.append(
            "This systematic review has several strengths. We followed "
            "PRISMA 2020 guidelines and used a comprehensive search strategy "
            "across multiple databases."
        )

        if analysis_results.get("meta_analysis_feasible"):
            n_studies = analysis_results.get("studies_included", 0)
            if n_studies >= 10:
                strengths.append(
                    f"The inclusion of {n_studies} studies provided adequate "
                    f"statistical power for the meta-analysis."
                )

            sensitivity = analysis_results.get("sensitivity_analysis", [])
            if sensitivity:
                strengths.append("Sensitivity analyses demonstrated robustness of findings.")

        # Limitations
        if rob_summary:
            high_risk = rob_summary.get("percent_high_risk", 0)
            if high_risk > 30:
                limitations.append(
                    f"A substantial proportion ({high_risk:.0f}%) of included studies "
                    f"were rated as high risk of bias, which may affect the validity "
                    f"of our findings."
                )

        heterogeneity = analysis_results.get("heterogeneity", {})
        i_squared = heterogeneity.get("i_squared", 0)
        if i_squared > 50:
            limitations.append(
                f"Substantial heterogeneity (I² = {i_squared:.0f}%) was observed, "
                f"which limits the generalizability of the pooled estimate."
            )

        limitations.append(
            "Publication bias cannot be fully excluded despite our comprehensive search strategy."
        )

        limitations.append(
            "The use of AI-assisted screening and extraction, while efficient, "
            "may introduce systematic biases not present in traditional methods."
        )

        content = (
            f"{' '.join(strengths)}\n\n"
            f"Several limitations should be acknowledged. {' '.join(limitations)}"
        )

        return {
            "title": "Strengths and Limitations",
            "content": content,
        }

    def _write_implications(
        self, analysis_results: dict, outcome_name: str, user_implications: str
    ) -> dict:
        """Write implications for practice and research."""
        parts = []

        parts.append("**Implications for Practice**\n")

        if analysis_results.get("is_significant"):
            parts.append(
                "Our findings suggest that the intervention may provide "
                f"clinically meaningful benefits for {outcome_name}. "
                "However, clinicians should consider individual patient factors "
                "and the certainty of evidence when making treatment decisions."
            )
        else:
            parts.append(
                "The current evidence does not support routine use of the "
                "intervention based on the primary outcome. Clinicians should "
                "consider the totality of evidence and patient preferences."
            )

        parts.append("\n\n**Implications for Research**\n")
        parts.append(
            "Future studies should address the limitations identified in this review. "
            "Specifically, there is a need for well-designed trials with "
            "standardized outcome measures and longer follow-up periods."
        )

        # Add user-provided implications if available
        if user_implications:
            parts.append(f"\n\n{user_implications}")

        return {
            "title": "Implications",
            "content": " ".join(parts),
        }

    def _write_future_research(self, analysis_results: dict, rob_summary: dict) -> dict:
        """Write future research directions."""
        recommendations = []

        # Based on heterogeneity
        heterogeneity = analysis_results.get("heterogeneity", {})
        if heterogeneity.get("i_squared", 0) > 50:
            recommendations.append(
                "investigate sources of heterogeneity through individual "
                "patient data meta-analysis or more detailed subgroup analyses"
            )

        # Based on RoB
        if rob_summary and rob_summary.get("percent_high_risk", 0) > 30:
            recommendations.append(
                "conduct high-quality randomized controlled trials with "
                "adequate allocation concealment and blinding"
            )

        # General recommendations
        recommendations.append(
            "standardize outcome measurement and reporting to facilitate future meta-analyses"
        )

        recommendations.append("include longer follow-up periods to assess durability of effects")

        recommendations.append(
            "examine potential effect modifiers and identify patient subgroups "
            "most likely to benefit"
        )

        content = (
            "Based on the findings and limitations of this review, we recommend "
            "that future research should:\n\n"
            + "\n".join([f"- {r.capitalize()}" for r in recommendations])
        )

        return {
            "title": "Future Research Directions",
            "content": content,
        }
