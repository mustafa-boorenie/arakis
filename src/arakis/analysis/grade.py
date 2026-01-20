"""GRADE assessment and Summary of Findings table generation.

Implements the GRADE approach for rating certainty of evidence and generates
publication-ready Summary of Findings tables.

Reference:
- Guyatt GH, et al. BMJ 2008;336:924-926 (GRADE introduction)
- Balshem H, et al. J Clin Epidemiol 2011;64:401-406 (GRADE guidelines)
- Schunemann HJ, et al. J Clin Epidemiol 2013;66:140-150 (GRADE guidelines)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from arakis.models.analysis import (
    ConfidenceInterval,
    EffectMeasure,
    MetaAnalysisResult,
    NarrativeSynthesisResult,
)
from arakis.models.grade import (
    CertaintyLevel,
    DomainRating,
    GRADEAssessment,
    GRADEDomain,
    GRADEEvidenceProfile,
    OutcomeData,
    RatingAction,
    SummaryOfFindings,
)
from arakis.models.risk_of_bias import RiskLevel, RiskOfBiasSummary
from arakis.models.visualization import Table
from arakis.traceability import DEFAULT_PRECISION


@dataclass
class GRADEConfig:
    """Configuration for GRADE assessment.

    Contains thresholds used for automated GRADE domain assessments.
    """

    # Risk of Bias thresholds
    rob_high_threshold: float = 0.25  # >25% studies high risk → serious
    rob_very_high_threshold: float = 0.50  # >50% studies high risk → very serious

    # Inconsistency (I²) thresholds (Higgins JPT, Thompson SG. BMJ 2002)
    i_squared_moderate: float = 50.0  # ≥50% → serious
    i_squared_high: float = 75.0  # ≥75% → very serious

    # Imprecision thresholds
    # Optimal Information Size (OIS): at least 400 events for binary, 400 participants for continuous
    ois_events: int = 400
    ois_participants: int = 400
    # CI crossing null and clinically important effect
    imprecision_null_crossing: bool = True  # Check if CI crosses 1.0 (ratio) or 0 (difference)

    # Large effect thresholds (for upgrading observational studies)
    large_effect_rr: float = 2.0  # RR > 2.0 or < 0.5
    very_large_effect_rr: float = 5.0  # RR > 5.0 or < 0.2

    # Publication bias
    egger_p_threshold: float = 0.10  # p < 0.10 suggests publication bias
    min_studies_egger: int = 10  # Minimum studies for Egger's test


class GRADEAssessor:
    """Automated GRADE assessment based on meta-analysis results.

    Assesses the five downgrade domains (risk of bias, inconsistency,
    indirectness, imprecision, publication bias) and three upgrade
    domains for observational studies (large effect, dose-response,
    plausible confounding).

    Note: This provides a starting point for GRADE assessment.
    Human review is recommended for final assessments, especially
    for indirectness which requires clinical judgment.
    """

    def __init__(self, config: Optional[GRADEConfig] = None) -> None:
        """Initialize the GRADE assessor.

        Args:
            config: Configuration for assessment thresholds.
        """
        self.config = config or GRADEConfig()

    def assess(
        self,
        meta_analysis: MetaAnalysisResult,
        study_design: str = "RCT",
        rob_summary: Optional[RiskOfBiasSummary] = None,
        indirectness_concerns: Optional[str] = None,
        baseline_risk: Optional[float] = None,
    ) -> GRADEAssessment:
        """Perform GRADE assessment on meta-analysis results.

        Args:
            meta_analysis: Meta-analysis result to assess.
            study_design: "RCT" or "observational".
            rob_summary: Risk of bias summary for included studies.
            indirectness_concerns: User-provided indirectness concerns (requires clinical judgment).
            baseline_risk: Baseline risk in control group per 1000 (for binary outcomes).

        Returns:
            Complete GRADE assessment.
        """
        # Assess each domain
        risk_of_bias = self._assess_risk_of_bias(meta_analysis, rob_summary)
        inconsistency = self._assess_inconsistency(meta_analysis)
        indirectness = self._assess_indirectness(indirectness_concerns)
        imprecision = self._assess_imprecision(meta_analysis)
        publication_bias = self._assess_publication_bias(meta_analysis)

        # Upgrade domains (only for observational studies)
        large_effect = None
        dose_response = None
        confounding = None

        if study_design.upper() not in ["RCT", "RANDOMIZED"]:
            large_effect = self._assess_large_effect(meta_analysis)
            # Dose-response and confounding require additional data
            dose_response = DomainRating(
                domain=GRADEDomain.DOSE_RESPONSE,
                action=RatingAction.NO_CHANGE,
                explanation="Dose-response assessment requires additional data; not assessed automatically.",
            )
            confounding = DomainRating(
                domain=GRADEDomain.CONFOUNDING,
                action=RatingAction.NO_CHANGE,
                explanation="Confounding assessment requires clinical judgment; not assessed automatically.",
            )

        assessment = GRADEAssessment(
            outcome_name=meta_analysis.outcome_name,
            study_design=study_design,
            n_studies=meta_analysis.studies_included,
            total_sample_size=meta_analysis.total_sample_size,
            risk_of_bias=risk_of_bias,
            inconsistency=inconsistency,
            indirectness=indirectness,
            imprecision=imprecision,
            publication_bias=publication_bias,
            large_effect=large_effect,
            dose_response=dose_response,
            confounding=confounding,
        )

        # Generate overall explanation
        assessment.overall_explanation = self._generate_explanation(assessment)

        return assessment

    def _assess_risk_of_bias(
        self,
        meta_analysis: MetaAnalysisResult,
        rob_summary: Optional[RiskOfBiasSummary],
    ) -> DomainRating:
        """Assess risk of bias domain.

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:407-415
        """
        if rob_summary is None:
            return DomainRating(
                domain=GRADEDomain.RISK_OF_BIAS,
                action=RatingAction.NO_CHANGE,
                explanation="Risk of bias assessment not provided; assume no serious concerns.",
            )

        percent_high = rob_summary.percent_high_risk

        if percent_high > self.config.rob_very_high_threshold * 100:
            return DomainRating(
                domain=GRADEDomain.RISK_OF_BIAS,
                action=RatingAction.DOWNGRADE_2,
                explanation=f"Very serious risk of bias: {percent_high:.1f}% of studies at high risk.",
                supporting_data={
                    "percent_high_risk": percent_high,
                    "percent_low_risk": rob_summary.percent_low_risk,
                    "n_studies": rob_summary.n_studies,
                },
            )
        elif percent_high > self.config.rob_high_threshold * 100:
            return DomainRating(
                domain=GRADEDomain.RISK_OF_BIAS,
                action=RatingAction.DOWNGRADE_1,
                explanation=f"Serious risk of bias: {percent_high:.1f}% of studies at high risk.",
                supporting_data={
                    "percent_high_risk": percent_high,
                    "percent_low_risk": rob_summary.percent_low_risk,
                    "n_studies": rob_summary.n_studies,
                },
            )
        else:
            return DomainRating(
                domain=GRADEDomain.RISK_OF_BIAS,
                action=RatingAction.NO_CHANGE,
                explanation=f"No serious risk of bias: {rob_summary.percent_low_risk:.1f}% of studies at low risk.",
                supporting_data={
                    "percent_high_risk": percent_high,
                    "percent_low_risk": rob_summary.percent_low_risk,
                    "n_studies": rob_summary.n_studies,
                },
            )

    def _assess_inconsistency(self, meta_analysis: MetaAnalysisResult) -> DomainRating:
        """Assess inconsistency (heterogeneity) domain.

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:1256-1262
        Based on I² statistic thresholds from Higgins JPT, Thompson SG. BMJ 2002.
        """
        i_squared = meta_analysis.heterogeneity.i_squared

        supporting_data = {
            "i_squared": i_squared,
            "tau_squared": meta_analysis.heterogeneity.tau_squared,
            "q_statistic": meta_analysis.heterogeneity.q_statistic,
            "q_p_value": meta_analysis.heterogeneity.q_p_value,
        }

        if i_squared >= self.config.i_squared_high:
            return DomainRating(
                domain=GRADEDomain.INCONSISTENCY,
                action=RatingAction.DOWNGRADE_2,
                explanation=f"Very serious inconsistency: I² = {i_squared:.1f}% indicates considerable heterogeneity.",
                supporting_data=supporting_data,
            )
        elif i_squared >= self.config.i_squared_moderate:
            return DomainRating(
                domain=GRADEDomain.INCONSISTENCY,
                action=RatingAction.DOWNGRADE_1,
                explanation=f"Serious inconsistency: I² = {i_squared:.1f}% indicates substantial heterogeneity.",
                supporting_data=supporting_data,
            )
        else:
            interpretation = DEFAULT_PRECISION.interpret_i_squared(i_squared)
            return DomainRating(
                domain=GRADEDomain.INCONSISTENCY,
                action=RatingAction.NO_CHANGE,
                explanation=f"No serious inconsistency: I² = {i_squared:.1f}% ({interpretation}).",
                supporting_data=supporting_data,
            )

    def _assess_indirectness(self, concerns: Optional[str]) -> DomainRating:
        """Assess indirectness domain.

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:1303-1310

        Note: Indirectness assessment requires clinical judgment about
        population, intervention, comparator, and outcome applicability.
        This cannot be fully automated.
        """
        if concerns is None:
            return DomainRating(
                domain=GRADEDomain.INDIRECTNESS,
                action=RatingAction.NO_CHANGE,
                explanation="No indirectness concerns specified; assume direct evidence.",
            )

        concerns_lower = concerns.lower()
        if "very serious" in concerns_lower or "major" in concerns_lower:
            return DomainRating(
                domain=GRADEDomain.INDIRECTNESS,
                action=RatingAction.DOWNGRADE_2,
                explanation=f"Very serious indirectness: {concerns}",
            )
        elif "serious" in concerns_lower or concerns.strip():
            return DomainRating(
                domain=GRADEDomain.INDIRECTNESS,
                action=RatingAction.DOWNGRADE_1,
                explanation=f"Serious indirectness: {concerns}",
            )
        else:
            return DomainRating(
                domain=GRADEDomain.INDIRECTNESS,
                action=RatingAction.NO_CHANGE,
                explanation="No serious indirectness.",
            )

    def _assess_imprecision(self, meta_analysis: MetaAnalysisResult) -> DomainRating:
        """Assess imprecision domain.

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:1283-1293

        Considers:
        1. Optimal Information Size (OIS)
        2. Confidence interval width and crossing of null/clinical thresholds
        """
        ci = meta_analysis.confidence_interval
        effect = meta_analysis.pooled_effect
        n = meta_analysis.total_sample_size
        effect_measure = meta_analysis.effect_measure

        supporting_data = {
            "pooled_effect": effect,
            "ci_lower": ci.lower,
            "ci_upper": ci.upper,
            "total_sample_size": n,
            "effect_measure": effect_measure.value,
        }

        # Check null crossing
        null_value = 0.0  # For MD, SMD
        if effect_measure in [EffectMeasure.ODDS_RATIO, EffectMeasure.RISK_RATIO]:
            null_value = 0.0  # On log scale; log(1) = 0

        crosses_null = ci.lower <= null_value <= ci.upper
        supporting_data["crosses_null"] = crosses_null

        # Check OIS
        # For simplicity, use total sample size vs threshold
        below_ois = n < self.config.ois_participants
        supporting_data["below_ois"] = below_ois

        # Calculate CI width relative to effect
        ci_width = ci.upper - ci.lower
        supporting_data["ci_width"] = ci_width

        # Very serious: crosses null AND below OIS
        # Serious: crosses null OR below OIS
        if crosses_null and below_ois:
            return DomainRating(
                domain=GRADEDomain.IMPRECISION,
                action=RatingAction.DOWNGRADE_2,
                explanation=(
                    f"Very serious imprecision: 95% CI [{ci.lower:.2f}, {ci.upper:.2f}] "
                    f"crosses the null and sample size ({n}) is below optimal information size."
                ),
                supporting_data=supporting_data,
            )
        elif crosses_null or below_ois:
            reason = "CI crosses the null" if crosses_null else f"sample size ({n}) is below optimal information size"
            return DomainRating(
                domain=GRADEDomain.IMPRECISION,
                action=RatingAction.DOWNGRADE_1,
                explanation=f"Serious imprecision: {reason}.",
                supporting_data=supporting_data,
            )
        else:
            return DomainRating(
                domain=GRADEDomain.IMPRECISION,
                action=RatingAction.NO_CHANGE,
                explanation=(
                    f"No serious imprecision: 95% CI [{ci.lower:.2f}, {ci.upper:.2f}] "
                    f"does not cross the null with adequate sample size ({n})."
                ),
                supporting_data=supporting_data,
            )

    def _assess_publication_bias(self, meta_analysis: MetaAnalysisResult) -> DomainRating:
        """Assess publication bias domain.

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:1311-1316

        Uses Egger's test p-value if available.
        """
        egger_p = meta_analysis.egger_test_p_value
        n_studies = meta_analysis.studies_included

        supporting_data = {
            "egger_test_p_value": egger_p,
            "n_studies": n_studies,
        }

        # Need at least 10 studies for reliable Egger's test
        if n_studies < self.config.min_studies_egger:
            return DomainRating(
                domain=GRADEDomain.PUBLICATION_BIAS,
                action=RatingAction.NO_CHANGE,
                explanation=(
                    f"Unable to assess publication bias: fewer than {self.config.min_studies_egger} "
                    f"studies ({n_studies} studies) limits ability to detect funnel plot asymmetry."
                ),
                supporting_data=supporting_data,
            )

        if egger_p is None:
            return DomainRating(
                domain=GRADEDomain.PUBLICATION_BIAS,
                action=RatingAction.NO_CHANGE,
                explanation="Publication bias assessment not performed (Egger's test not available).",
                supporting_data=supporting_data,
            )

        if egger_p < self.config.egger_p_threshold:
            return DomainRating(
                domain=GRADEDomain.PUBLICATION_BIAS,
                action=RatingAction.DOWNGRADE_1,
                explanation=(
                    f"Serious publication bias suspected: Egger's test p = {egger_p:.4f} "
                    f"suggests funnel plot asymmetry."
                ),
                supporting_data=supporting_data,
            )
        else:
            return DomainRating(
                domain=GRADEDomain.PUBLICATION_BIAS,
                action=RatingAction.NO_CHANGE,
                explanation=(
                    f"No serious publication bias detected: Egger's test p = {egger_p:.4f}."
                ),
                supporting_data=supporting_data,
            )

    def _assess_large_effect(self, meta_analysis: MetaAnalysisResult) -> DomainRating:
        """Assess large effect domain (for upgrading observational studies).

        Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:1311-1316
        """
        effect = meta_analysis.pooled_effect
        effect_measure = meta_analysis.effect_measure

        supporting_data = {
            "pooled_effect": effect,
            "effect_measure": effect_measure.value,
        }

        # Only applicable for ratio measures
        if effect_measure not in [EffectMeasure.ODDS_RATIO, EffectMeasure.RISK_RATIO]:
            return DomainRating(
                domain=GRADEDomain.LARGE_EFFECT,
                action=RatingAction.NO_CHANGE,
                explanation="Large effect assessment not applicable for non-ratio effect measures.",
                supporting_data=supporting_data,
            )

        # Effect is on log scale; convert to natural scale
        effect_natural = math.exp(effect)
        supporting_data["effect_natural_scale"] = effect_natural

        # Very large effect: RR > 5 or < 0.2
        if effect_natural > self.config.very_large_effect_rr or effect_natural < (1 / self.config.very_large_effect_rr):
            return DomainRating(
                domain=GRADEDomain.LARGE_EFFECT,
                action=RatingAction.UPGRADE_2,
                explanation=f"Very large effect: RR = {effect_natural:.2f} (upgrade by 2 levels).",
                supporting_data=supporting_data,
            )
        # Large effect: RR > 2 or < 0.5
        elif effect_natural > self.config.large_effect_rr or effect_natural < (1 / self.config.large_effect_rr):
            return DomainRating(
                domain=GRADEDomain.LARGE_EFFECT,
                action=RatingAction.UPGRADE_1,
                explanation=f"Large effect: RR = {effect_natural:.2f} (upgrade by 1 level).",
                supporting_data=supporting_data,
            )
        else:
            return DomainRating(
                domain=GRADEDomain.LARGE_EFFECT,
                action=RatingAction.NO_CHANGE,
                explanation=f"No large effect: RR = {effect_natural:.2f}.",
                supporting_data=supporting_data,
            )

    def _generate_explanation(self, assessment: GRADEAssessment) -> str:
        """Generate overall explanation for the assessment."""
        parts = []

        # Starting level
        start_level = "HIGH" if assessment.starting_level == 4 else "LOW"
        parts.append(
            f"Starting at {start_level} certainty ({assessment.study_design} evidence)."
        )

        # Downgrades
        downgrades = assessment.get_downgrade_summary()
        if downgrades:
            parts.append(f"Downgraded for: {'; '.join(downgrades)}.")

        # Upgrades
        upgrades = assessment.get_upgrade_summary()
        if upgrades:
            parts.append(f"Upgraded for: {'; '.join(upgrades)}.")

        # Final certainty
        certainty = assessment.overall_certainty
        if certainty:
            parts.append(f"Overall certainty: {certainty.value.upper()}.")

        return " ".join(parts)

    def create_outcome_data(
        self,
        meta_analysis: MetaAnalysisResult,
        assessment: GRADEAssessment,
        baseline_risk: Optional[float] = None,
        outcome_description: str = "",
        importance: str = "important",
    ) -> OutcomeData:
        """Create OutcomeData from meta-analysis and GRADE assessment.

        Args:
            meta_analysis: Meta-analysis result.
            assessment: GRADE assessment for the outcome.
            baseline_risk: Baseline risk per 1000 in control group (for absolute effects).
            outcome_description: Description of the outcome.
            importance: Importance level ("critical", "important", "not important").

        Returns:
            OutcomeData ready for Summary of Findings table.
        """
        # Convert log-scale effects to natural scale for ratio measures
        is_log_scale = meta_analysis.effect_measure in [
            EffectMeasure.ODDS_RATIO,
            EffectMeasure.RISK_RATIO,
        ]

        if is_log_scale:
            relative_effect = math.exp(meta_analysis.pooled_effect)
            ci_lower = math.exp(meta_analysis.confidence_interval.lower)
            ci_upper = math.exp(meta_analysis.confidence_interval.upper)
        else:
            relative_effect = meta_analysis.pooled_effect
            ci_lower = meta_analysis.confidence_interval.lower
            ci_upper = meta_analysis.confidence_interval.upper

        relative_ci = ConfidenceInterval(lower=ci_lower, upper=ci_upper)

        # Calculate absolute effect if baseline risk provided
        absolute_effect = None
        absolute_ci = None
        control_risk = None
        intervention_risk = None

        if baseline_risk is not None and is_log_scale:
            control_risk = baseline_risk
            # For RR: intervention_risk = baseline_risk * RR
            # Absolute difference = intervention_risk - control_risk
            intervention_risk = baseline_risk * relative_effect
            absolute_effect = intervention_risk - control_risk

            intervention_risk_lower = baseline_risk * ci_lower
            intervention_risk_upper = baseline_risk * ci_upper
            absolute_ci = ConfidenceInterval(
                lower=intervention_risk_lower - control_risk,
                upper=intervention_risk_upper - control_risk,
            )

        return OutcomeData(
            outcome_name=meta_analysis.outcome_name,
            outcome_description=outcome_description,
            n_studies=meta_analysis.studies_included,
            n_participants=meta_analysis.total_sample_size,
            relative_effect=relative_effect,
            relative_effect_ci=relative_ci,
            effect_measure=meta_analysis.effect_measure,
            control_risk=control_risk,
            intervention_risk=intervention_risk,
            absolute_effect=absolute_effect,
            absolute_effect_ci=absolute_ci,
            grade_assessment=assessment,
            importance=importance,
        )


class SummaryOfFindingsTableGenerator:
    """Generates GRADE Summary of Findings tables.

    Creates publication-ready tables in multiple formats (markdown, HTML).
    """

    def __init__(self) -> None:
        """Initialize the generator."""
        pass

    def generate_table(
        self,
        sof: SummaryOfFindings,
        include_certainty_symbols: bool = True,
        use_ascii: bool = False,
    ) -> Table:
        """Generate a Summary of Findings table.

        Args:
            sof: Summary of Findings data.
            include_certainty_symbols: Include visual certainty symbols.
            use_ascii: Use ASCII symbols instead of Unicode.

        Returns:
            Table object with formatted SoF table.
        """
        # Standard SoF table headers (GRADEpro format)
        headers = [
            "Outcomes",
            "No. of participants (studies)",
            "Relative effect (95% CI)",
            "Anticipated absolute effects* (95% CI)",
            "Certainty",
            "Comments",
        ]

        rows = []
        for outcome in sof.outcomes:
            row = self._format_outcome_row(outcome, include_certainty_symbols, use_ascii)
            rows.append(row)

        # Generate caption
        caption = self._generate_caption(sof)

        # Standard GRADE footnotes
        footnotes = [
            "*The risk in the intervention group (and its 95% confidence interval) is based on the assumed risk in the comparison group and the relative effect of the intervention (and its 95% CI).",
        ]
        footnotes.extend(sof.footnotes)

        # Add certainty rating explanations
        footnotes.extend([
            "GRADE certainty ratings: HIGH = very confident effect lies close to estimate; MODERATE = moderately confident, true effect likely close; LOW = limited confidence, true effect may be substantially different; VERY LOW = very little confidence.",
        ])

        return Table(
            id="sof_table",
            title=f"Summary of findings: {sof.intervention} compared to {sof.comparison}",
            caption=caption,
            headers=headers,
            rows=rows,
            footnotes=footnotes,
        )

    def _format_outcome_row(
        self,
        outcome: OutcomeData,
        include_symbols: bool,
        use_ascii: bool,
    ) -> list[str]:
        """Format a single outcome row for the SoF table."""
        # Outcomes column
        outcome_text = outcome.outcome_name
        if outcome.outcome_description:
            outcome_text += f" ({outcome.outcome_description})"

        # Participants column
        participants = f"{outcome.n_participants} ({outcome.n_studies} {'study' if outcome.n_studies == 1 else 'studies'})"

        # Relative effect column
        relative_effect = outcome.format_relative_effect()
        if outcome.effect_measure:
            measure_abbrev = self._get_effect_measure_abbrev(outcome.effect_measure)
            relative_effect = f"{measure_abbrev} {relative_effect}"

        # Absolute effects column
        absolute_text = self._format_absolute_effects(outcome)

        # Certainty column
        certainty_text = ""
        if outcome.certainty:
            if include_symbols:
                symbol = outcome.certainty.ascii_symbol if use_ascii else outcome.certainty.symbol
                certainty_text = f"{symbol} {outcome.certainty.value.upper()}"
            else:
                certainty_text = outcome.certainty.value.upper()

        # Comments column
        comments = outcome.comments if outcome.comments else ""

        return [outcome_text, participants, relative_effect, absolute_text, certainty_text, comments]

    def _format_absolute_effects(self, outcome: OutcomeData) -> str:
        """Format the anticipated absolute effects column."""
        if outcome.control_risk is None:
            return outcome.format_absolute_effect()

        # Two-column format: Control risk | Intervention risk (difference)
        control_text = f"{outcome.control_risk:.0f} per 1000"

        if outcome.intervention_risk is not None and outcome.absolute_effect is not None:
            direction = "fewer" if outcome.absolute_effect < 0 else "more"
            abs_val = abs(outcome.absolute_effect)

            intervention_text = f"{outcome.intervention_risk:.0f} per 1000 ({abs_val:.0f} {direction})"

            if outcome.absolute_effect_ci:
                ci_lower = abs(outcome.absolute_effect_ci.lower)
                ci_upper = abs(outcome.absolute_effect_ci.upper)
                intervention_text = f"{outcome.intervention_risk:.0f} per 1000 ({ci_lower:.0f} {direction} to {ci_upper:.0f} {direction})"

            return f"Control: {control_text} | Intervention: {intervention_text}"

        return f"Control: {control_text}"

    def _get_effect_measure_abbrev(self, measure: EffectMeasure) -> str:
        """Get abbreviation for effect measure."""
        abbrevs = {
            EffectMeasure.ODDS_RATIO: "OR",
            EffectMeasure.RISK_RATIO: "RR",
            EffectMeasure.RISK_DIFFERENCE: "RD",
            EffectMeasure.MEAN_DIFFERENCE: "MD",
            EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE: "SMD",
            EffectMeasure.CORRELATION: "r",
        }
        return abbrevs.get(measure, "")

    def _generate_caption(self, sof: SummaryOfFindings) -> str:
        """Generate table caption."""
        parts = [
            f"Population: {sof.population}",
            f"Intervention: {sof.intervention}",
            f"Comparison: {sof.comparison}",
        ]
        if sof.setting:
            parts.append(f"Setting: {sof.setting}")

        return " | ".join(parts)

    def generate_evidence_profile(
        self,
        sof: SummaryOfFindings,
        use_ascii: bool = False,
    ) -> Table:
        """Generate a GRADE Evidence Profile table.

        The evidence profile shows detailed domain-level assessments.

        Args:
            sof: Summary of Findings data with GRADE assessments.
            use_ascii: Use ASCII symbols instead of Unicode.

        Returns:
            Table object with formatted evidence profile.
        """
        headers = [
            "Outcome",
            "No. of studies",
            "Study design",
            "Risk of bias",
            "Inconsistency",
            "Indirectness",
            "Imprecision",
            "Other",
            "Effect (95% CI)",
            "Certainty",
        ]

        rows = []
        for outcome in sof.outcomes:
            row = self._format_evidence_profile_row(outcome, use_ascii)
            rows.append(row)

        footnotes = [
            "Risk of bias, inconsistency, indirectness, imprecision ratings: not serious, serious (-1), very serious (-2).",
            "Other considerations include publication bias, large effect, dose-response, and plausible confounding.",
        ]

        return Table(
            id="evidence_profile",
            title=f"GRADE Evidence Profile: {sof.intervention} vs {sof.comparison}",
            caption=self._generate_caption(sof),
            headers=headers,
            rows=rows,
            footnotes=footnotes,
        )

    def _format_evidence_profile_row(
        self,
        outcome: OutcomeData,
        use_ascii: bool,
    ) -> list[str]:
        """Format a single row for the evidence profile."""
        assessment = outcome.grade_assessment

        if assessment is None:
            return [
                outcome.outcome_name,
                str(outcome.n_studies),
                "—",
                "—",
                "—",
                "—",
                "—",
                "—",
                outcome.format_relative_effect(),
                "—",
            ]

        # Format domain ratings
        def format_rating(rating: DomainRating) -> str:
            if rating.action == RatingAction.NO_CHANGE:
                return "not serious"
            elif rating.action == RatingAction.DOWNGRADE_1:
                return "serious"
            elif rating.action == RatingAction.DOWNGRADE_2:
                return "very serious"
            elif rating.action in [RatingAction.UPGRADE_1, RatingAction.UPGRADE_2]:
                return "upgrade"
            return "—"

        # Other considerations column
        other_parts = []
        if assessment.publication_bias.action != RatingAction.NO_CHANGE:
            other_parts.append("publication bias")
        if assessment.large_effect and assessment.large_effect.action != RatingAction.NO_CHANGE:
            other_parts.append("large effect")
        if assessment.dose_response and assessment.dose_response.action != RatingAction.NO_CHANGE:
            other_parts.append("dose-response")
        if assessment.confounding and assessment.confounding.action != RatingAction.NO_CHANGE:
            other_parts.append("confounding")

        other = ", ".join(other_parts) if other_parts else "none"

        # Certainty with symbol
        certainty_text = ""
        if outcome.certainty:
            symbol = outcome.certainty.ascii_symbol if use_ascii else outcome.certainty.symbol
            certainty_text = f"{symbol} {outcome.certainty.value.upper()}"

        return [
            outcome.outcome_name,
            str(outcome.n_studies),
            assessment.study_design,
            format_rating(assessment.risk_of_bias),
            format_rating(assessment.inconsistency),
            format_rating(assessment.indirectness),
            format_rating(assessment.imprecision),
            other,
            outcome.format_relative_effect(),
            certainty_text,
        ]

    def generate_markdown(
        self,
        sof: SummaryOfFindings,
        include_evidence_profile: bool = False,
    ) -> str:
        """Generate complete markdown output with SoF table.

        Args:
            sof: Summary of Findings data.
            include_evidence_profile: Include detailed evidence profile table.

        Returns:
            Markdown string with formatted tables.
        """
        parts = []

        # Title
        parts.append(f"## Summary of Findings: {sof.intervention} compared to {sof.comparison}")
        parts.append("")

        # Patient/population info
        parts.append(f"**Population:** {sof.population}")
        parts.append(f"**Intervention:** {sof.intervention}")
        parts.append(f"**Comparison:** {sof.comparison}")
        if sof.setting:
            parts.append(f"**Setting:** {sof.setting}")
        parts.append("")

        # Main SoF table
        table = self.generate_table(sof, include_certainty_symbols=True, use_ascii=True)
        parts.append(table.markdown)
        parts.append("")

        # Evidence profile if requested
        if include_evidence_profile:
            parts.append("### GRADE Evidence Profile")
            parts.append("")
            profile_table = self.generate_evidence_profile(sof, use_ascii=True)
            parts.append(profile_table.markdown)
            parts.append("")

        # Certainty explanations
        parts.append("### Certainty of Evidence")
        parts.append("")
        for outcome in sof.outcomes:
            if outcome.grade_assessment:
                parts.append(f"**{outcome.outcome_name}:** {outcome.grade_assessment.overall_explanation}")
        parts.append("")

        return "\n".join(parts)

    def generate_html(
        self,
        sof: SummaryOfFindings,
        include_evidence_profile: bool = False,
    ) -> str:
        """Generate HTML output with SoF table.

        Args:
            sof: Summary of Findings data.
            include_evidence_profile: Include detailed evidence profile table.

        Returns:
            HTML string with formatted tables.
        """
        parts = []

        # Title
        parts.append(f"<h2>Summary of Findings: {sof.intervention} compared to {sof.comparison}</h2>")

        # Patient/population info
        parts.append("<div class='sof-header'>")
        parts.append(f"<p><strong>Population:</strong> {sof.population}</p>")
        parts.append(f"<p><strong>Intervention:</strong> {sof.intervention}</p>")
        parts.append(f"<p><strong>Comparison:</strong> {sof.comparison}</p>")
        if sof.setting:
            parts.append(f"<p><strong>Setting:</strong> {sof.setting}</p>")
        parts.append("</div>")

        # Main SoF table
        table = self.generate_table(sof, include_certainty_symbols=True, use_ascii=False)
        parts.append(table.html)

        # Evidence profile if requested
        if include_evidence_profile:
            parts.append("<h3>GRADE Evidence Profile</h3>")
            profile_table = self.generate_evidence_profile(sof, use_ascii=False)
            parts.append(profile_table.html)

        return "\n".join(parts)
