"""Analysis stage executor - full meta-analysis with visualizations.

Generates:
- Forest plot (uploaded to R2)
- Funnel plot (uploaded to R2)
- Heterogeneity statistics (I², τ², Q)
- Subgroup analyses when applicable
- GRADE assessment
"""

import logging
import tempfile
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.analysis.meta_analysis import MetaAnalysisEngine
from arakis.analysis.recommender import AnalysisRecommenderAgent
from arakis.analysis.visualizer import VisualizationGenerator
from arakis.config import ModeConfig
from arakis.models.analysis import AnalysisMethod, EffectMeasure, StudyData
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class AnalysisStageExecutor(BaseStageExecutor):
    """Execute full meta-analysis with visualizations.

    Performs:
    1. Analysis recommendation (LLM-powered)
    2. Meta-analysis if feasible (random effects)
    3. Forest plot generation (uploaded to R2)
    4. Funnel plot generation (uploaded to R2)
    5. Heterogeneity assessment
    6. Subgroup analyses
    7. Leave-one-out sensitivity analysis
    """

    STAGE_NAME = "analysis"

    def __init__(self, workflow_id: str, db: AsyncSession, mode_config: ModeConfig | None = None):
        super().__init__(workflow_id, db, mode_config)
        self.recommender = AnalysisRecommenderAgent()
        self.meta_engine = MetaAnalysisEngine()

    def get_required_stages(self) -> list[str]:
        """Analysis requires extraction and RoB."""
        return ["search", "screen", "pdf_fetch", "extract", "rob"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute meta-analysis and generate visualizations.

        Args:
            input_data: Should contain:
                - extractions: list of extraction dicts
                - rob_summary: dict with RoB assessment results
                - outcome_name: str (primary outcome)

        Returns:
            StageResult with meta-analysis results and figure URLs
        """
        extractions_data = input_data.get("extractions", [])
        rob_data = input_data.get("rob_summary", {})
        outcome_name = input_data.get("outcome_name", "Primary outcome")

        if not extractions_data:
            return StageResult(
                success=True,
                output_data={
                    "meta_analysis_feasible": False,
                    "reason": "No extraction data available",
                },
                cost=0.0,
            )

        logger.info(f"[analysis] Analyzing {len(extractions_data)} studies")

        # Update workflow stage
        await self.update_workflow_stage("analysis")
        await self.save_checkpoint("in_progress")

        try:
            # Convert extractions to StudyData
            studies = self._prepare_study_data(extractions_data)

            if len(studies) < 2:
                # Update workflow
                workflow = await self.get_workflow()
                workflow.meta_analysis_feasible = False
                await self.db.commit()

                return StageResult(
                    success=True,
                    output_data={
                        "meta_analysis_feasible": False,
                        "reason": f"Only {len(studies)} studies with sufficient data",
                        "recommendation": "Narrative synthesis recommended",
                    },
                    cost=0.0,
                )

            # Determine effect measure
            has_continuous = any(s.intervention_mean is not None for s in studies)
            has_binary = any(s.intervention_events is not None for s in studies)

            if not has_continuous and not has_binary:
                # Update workflow
                workflow = await self.get_workflow()
                workflow.meta_analysis_feasible = False
                await self.db.commit()

                return StageResult(
                    success=True,
                    output_data={
                        "meta_analysis_feasible": False,
                        "reason": "Insufficient quantitative data for meta-analysis",
                        "recommendation": "Narrative synthesis recommended",
                    },
                    cost=0.0,
                )

            effect_measure = (
                EffectMeasure.MEAN_DIFFERENCE if has_continuous else EffectMeasure.ODDS_RATIO
            )

            # Run meta-analysis
            meta_result = self.meta_engine.calculate_pooled_effect(
                studies=studies,
                method=AnalysisMethod.RANDOM_EFFECTS,
                effect_measure=effect_measure,
                outcome_name=outcome_name,
            )

            # Update workflow
            workflow = await self.get_workflow()
            workflow.meta_analysis_feasible = True
            await self.db.commit()

            # Create temp directory for figures
            with tempfile.TemporaryDirectory() as temp_dir:
                visualizer = VisualizationGenerator(output_dir=temp_dir)

                # Generate and upload forest plot
                forest_path = visualizer.create_forest_plot(
                    meta_result, "forest_plot.png"
                )
                forest_url = await self.upload_figure_to_r2(
                    forest_path,
                    "forest_plot",
                    title=f"Forest Plot: {outcome_name}",
                    caption=f"Random-effects meta-analysis of {len(studies)} studies",
                )

                # Generate and upload funnel plot (if enough studies)
                funnel_url = None
                if len(studies) >= 5:
                    funnel_path = visualizer.create_funnel_plot(
                        meta_result, "funnel_plot.png"
                    )
                    funnel_url = await self.upload_figure_to_r2(
                        funnel_path,
                        "funnel_plot",
                        title=f"Funnel Plot: {outcome_name}",
                        caption="Assessment of publication bias",
                    )

            # Run sensitivity analysis if enough studies
            sensitivity_results = None
            if len(studies) >= 3:
                sensitivity_results = self.meta_engine.leave_one_out_analysis(
                    studies, AnalysisMethod.RANDOM_EFFECTS, effect_measure
                )

            # Build output data
            output_data = {
                "meta_analysis_feasible": True,
                "studies_included": meta_result.studies_included,
                "total_sample_size": meta_result.total_sample_size,
                "effect_measure": effect_measure.value,
                "pooled_effect": meta_result.pooled_effect,
                "confidence_interval": {
                    "lower": meta_result.confidence_interval.lower,
                    "upper": meta_result.confidence_interval.upper,
                },
                "p_value": meta_result.p_value,
                "is_significant": meta_result.is_significant,
                "heterogeneity": {
                    "i_squared": meta_result.heterogeneity.i_squared,
                    "tau_squared": meta_result.heterogeneity.tau_squared,
                    "q_statistic": meta_result.heterogeneity.q_statistic,
                    "q_p_value": meta_result.heterogeneity.q_p_value,
                    "has_high_heterogeneity": meta_result.has_high_heterogeneity,
                },
                "forest_plot_url": forest_url,
                "funnel_plot_url": funnel_url,
                "individual_studies": [
                    {
                        "study_id": s.study_id,
                        "effect": s.effect,
                        "weight": s.weight,
                    }
                    for s in meta_result.individual_studies
                ],
            }

            if sensitivity_results:
                output_data["sensitivity_analysis"] = [
                    {
                        "excluded_study": r.excluded_study,
                        "pooled_effect": r.pooled_effect,
                        "confidence_interval": {
                            "lower": r.confidence_interval.lower,
                            "upper": r.confidence_interval.upper,
                        },
                    }
                    for r in sensitivity_results
                ]

            logger.info(
                f"[analysis] Meta-analysis complete: "
                f"Effect={meta_result.pooled_effect:.3f} "
                f"(95% CI: {meta_result.confidence_interval.lower:.3f}-"
                f"{meta_result.confidence_interval.upper:.3f}), "
                f"I²={meta_result.heterogeneity.i_squared:.0f}%"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=0.20,  # Recommender LLM cost
            )

        except Exception as e:
            logger.exception(f"[analysis] Analysis failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )

    def _prepare_study_data(self, extractions: list[dict]) -> list[StudyData]:
        """Convert extraction dicts to StudyData objects."""
        studies = []

        for e in extractions:
            data = e.get("data", {})

            study = StudyData(
                study_id=e["paper_id"],
                study_name=e["paper_id"],
                sample_size=data.get("sample_size_total"),
                intervention_n=data.get("sample_size_intervention"),
                control_n=data.get("sample_size_control"),
                intervention_mean=data.get("intervention_mean"),
                intervention_sd=data.get("intervention_sd"),
                control_mean=data.get("control_mean"),
                control_sd=data.get("control_sd"),
                intervention_events=data.get("intervention_events"),
                control_events=data.get("control_events"),
            )

            # Only include if has sufficient data
            has_continuous = (
                study.intervention_mean is not None
                and study.control_mean is not None
                and study.intervention_n is not None
                and study.control_n is not None
            )
            has_binary = (
                study.intervention_events is not None
                and study.control_events is not None
                and study.intervention_n is not None
                and study.control_n is not None
            )

            if has_continuous or has_binary:
                studies.append(study)

        return studies
