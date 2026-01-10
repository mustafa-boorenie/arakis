"""Meta-analysis computations.

Implements fixed-effects and random-effects meta-analysis with heterogeneity
assessment and publication bias detection.
"""

import math
from typing import Callable

import numpy as np
from scipy import stats

from arakis.models.analysis import (
    AnalysisMethod,
    ConfidenceInterval,
    EffectMeasure,
    Heterogeneity,
    MetaAnalysisResult,
    StudyData,
)


class MetaAnalysisEngine:
    """Engine for meta-analysis computations."""

    def __init__(self, confidence_level: float = 0.95):
        """Initialize meta-analysis engine.

        Args:
            confidence_level: Confidence level for intervals (default 0.95)
        """
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    def calculate_pooled_effect(
        self,
        studies: list[StudyData],
        method: AnalysisMethod = AnalysisMethod.RANDOM_EFFECTS,
        effect_measure: EffectMeasure = EffectMeasure.MEAN_DIFFERENCE,
    ) -> MetaAnalysisResult:
        """Calculate pooled effect estimate from multiple studies.

        Args:
            studies: List of study data
            method: Analysis method (fixed or random effects)
            effect_measure: Type of effect measure

        Returns:
            MetaAnalysisResult with pooled effect and statistics
        """
        if len(studies) < 2:
            raise ValueError("Meta-analysis requires at least 2 studies")

        # Calculate individual study effects if not provided
        studies = self._calculate_study_effects(studies, effect_measure)

        # Calculate heterogeneity
        heterogeneity = self._calculate_heterogeneity(studies)

        # Choose method based on heterogeneity if using random effects
        if method == AnalysisMethod.RANDOM_EFFECTS:
            if heterogeneity.i_squared > 50:
                # High heterogeneity - use random effects
                pooled_effect, ci, weights = self._random_effects_meta_analysis(studies, heterogeneity)
            else:
                # Low heterogeneity - random effects reduces to fixed effects
                pooled_effect, ci, weights = self._fixed_effects_meta_analysis(studies)
        else:
            # Fixed effects
            pooled_effect, ci, weights = self._fixed_effects_meta_analysis(studies)

        # Update study weights
        for study, weight in zip(studies, weights):
            study.weight = weight

        # Calculate z-statistic and p-value
        se = (ci.upper - ci.lower) / (2 * stats.norm.ppf(1 - self.alpha / 2))
        z_statistic = pooled_effect / se if se > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))

        # Calculate total sample size
        total_n = sum(
            (s.intervention_n or 0) + (s.control_n or 0)
            for s in studies
            if s.intervention_n and s.control_n
        )
        if total_n == 0:
            total_n = sum(s.sample_size or 0 for s in studies)

        return MetaAnalysisResult(
            outcome_name="Pooled Analysis",
            studies_included=len(studies),
            total_sample_size=total_n,
            pooled_effect=pooled_effect,
            confidence_interval=ci,
            effect_measure=effect_measure,
            heterogeneity=heterogeneity,
            z_statistic=z_statistic,
            p_value=p_value,
            analysis_method=method,
            studies=studies,
        )

    def _calculate_study_effects(
        self, studies: list[StudyData], effect_measure: EffectMeasure
    ) -> list[StudyData]:
        """Calculate effect estimates and standard errors for each study.

        Args:
            studies: List of study data
            effect_measure: Type of effect measure

        Returns:
            Updated studies with effect and SE calculated
        """
        updated_studies = []

        for study in studies:
            # If effect already provided, use it
            if study.effect is not None and study.standard_error is not None:
                updated_studies.append(study)
                continue

            # Calculate based on raw data
            if effect_measure == EffectMeasure.MEAN_DIFFERENCE:
                effect, se = self._calculate_mean_difference_effect(study)
            elif effect_measure == EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE:
                effect, se = self._calculate_smd_effect(study)
            elif effect_measure == EffectMeasure.ODDS_RATIO:
                effect, se = self._calculate_odds_ratio_effect(study)
            elif effect_measure == EffectMeasure.RISK_RATIO:
                effect, se = self._calculate_risk_ratio_effect(study)
            elif effect_measure == EffectMeasure.RISK_DIFFERENCE:
                effect, se = self._calculate_risk_difference_effect(study)
            else:
                raise ValueError(f"Unsupported effect measure: {effect_measure}")

            study.effect = effect
            study.standard_error = se
            updated_studies.append(study)

        return updated_studies

    def _calculate_mean_difference_effect(self, study: StudyData) -> tuple[float, float]:
        """Calculate mean difference and standard error."""
        if not all(
            [
                study.intervention_mean is not None,
                study.control_mean is not None,
                study.intervention_sd is not None,
                study.control_sd is not None,
                study.intervention_n is not None,
                study.control_n is not None,
            ]
        ):
            raise ValueError(f"Study {study.study_id} missing data for mean difference calculation")

        md = study.intervention_mean - study.control_mean  # type: ignore
        se = math.sqrt(
            (study.intervention_sd**2 / study.intervention_n)  # type: ignore
            + (study.control_sd**2 / study.control_n)  # type: ignore
        )

        return md, se

    def _calculate_smd_effect(self, study: StudyData) -> tuple[float, float]:
        """Calculate standardized mean difference (Hedges' g) and standard error."""
        if not all(
            [
                study.intervention_mean is not None,
                study.control_mean is not None,
                study.intervention_sd is not None,
                study.control_sd is not None,
                study.intervention_n is not None,
                study.control_n is not None,
            ]
        ):
            raise ValueError(f"Study {study.study_id} missing data for SMD calculation")

        n1, n2 = study.intervention_n, study.control_n  # type: ignore
        m1, m2 = study.intervention_mean, study.control_mean  # type: ignore
        sd1, sd2 = study.intervention_sd, study.control_sd  # type: ignore

        # Pooled standard deviation
        pooled_sd = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))

        # Cohen's d
        cohens_d = (m1 - m2) / pooled_sd

        # Correction factor for small samples (Hedges' g)
        correction = 1 - (3 / (4 * (n1 + n2 - 2) - 1))
        hedges_g = cohens_d * correction

        # Standard error
        se = math.sqrt(((n1 + n2) / (n1 * n2)) + (hedges_g**2 / (2 * (n1 + n2))))

        return hedges_g, se

    def _calculate_odds_ratio_effect(self, study: StudyData) -> tuple[float, float]:
        """Calculate log odds ratio and standard error."""
        if not all(
            [
                study.intervention_events is not None,
                study.intervention_n is not None,
                study.control_events is not None,
                study.control_n is not None,
            ]
        ):
            raise ValueError(f"Study {study.study_id} missing data for odds ratio calculation")

        a = study.intervention_events  # type: ignore
        b = study.intervention_n - study.intervention_events  # type: ignore
        c = study.control_events  # type: ignore
        d = study.control_n - study.control_events  # type: ignore

        # Continuity correction for zero cells
        if any(x == 0 for x in [a, b, c, d]):
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5

        # Log odds ratio
        log_or = math.log((a * d) / (b * c))

        # Standard error
        se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)

        return log_or, se

    def _calculate_risk_ratio_effect(self, study: StudyData) -> tuple[float, float]:
        """Calculate log risk ratio and standard error."""
        if not all(
            [
                study.intervention_events is not None,
                study.intervention_n is not None,
                study.control_events is not None,
                study.control_n is not None,
            ]
        ):
            raise ValueError(f"Study {study.study_id} missing data for risk ratio calculation")

        a = study.intervention_events  # type: ignore
        n1 = study.intervention_n  # type: ignore
        c = study.control_events  # type: ignore
        n2 = study.control_n  # type: ignore

        # Avoid division by zero
        if a == 0:
            a = 0.5
        if c == 0:
            c = 0.5

        risk1 = a / n1
        risk2 = c / n2

        # Log risk ratio
        log_rr = math.log(risk1 / risk2)

        # Standard error
        se = math.sqrt((1 / a - 1 / n1) + (1 / c - 1 / n2))

        return log_rr, se

    def _calculate_risk_difference_effect(self, study: StudyData) -> tuple[float, float]:
        """Calculate risk difference and standard error."""
        if not all(
            [
                study.intervention_events is not None,
                study.intervention_n is not None,
                study.control_events is not None,
                study.control_n is not None,
            ]
        ):
            raise ValueError(f"Study {study.study_id} missing data for risk difference calculation")

        a = study.intervention_events  # type: ignore
        n1 = study.intervention_n  # type: ignore
        c = study.control_events  # type: ignore
        n2 = study.control_n  # type: ignore

        risk1 = a / n1
        risk2 = c / n2

        rd = risk1 - risk2

        # Standard error
        se = math.sqrt((risk1 * (1 - risk1) / n1) + (risk2 * (1 - risk2) / n2))

        return rd, se

    def _fixed_effects_meta_analysis(
        self, studies: list[StudyData]
    ) -> tuple[float, ConfidenceInterval, list[float]]:
        """Perform fixed-effects meta-analysis using inverse variance weights.

        Args:
            studies: List of studies with effect and SE

        Returns:
            Tuple of (pooled_effect, confidence_interval, weights)
        """
        # Calculate weights (inverse variance)
        weights = [1 / (s.standard_error**2) for s in studies]  # type: ignore
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate pooled effect
        pooled_effect = sum(s.effect * w for s, w in zip(studies, normalized_weights))  # type: ignore

        # Calculate standard error
        pooled_se = math.sqrt(1 / total_weight)

        # Calculate confidence interval
        z_crit = stats.norm.ppf(1 - self.alpha / 2)
        ci = ConfidenceInterval(
            lower=pooled_effect - z_crit * pooled_se,
            upper=pooled_effect + z_crit * pooled_se,
            level=self.confidence_level,
        )

        return pooled_effect, ci, normalized_weights

    def _random_effects_meta_analysis(
        self, studies: list[StudyData], heterogeneity: Heterogeneity
    ) -> tuple[float, ConfidenceInterval, list[float]]:
        """Perform random-effects meta-analysis (DerSimonian-Laird).

        Args:
            studies: List of studies with effect and SE
            heterogeneity: Heterogeneity statistics containing tau²

        Returns:
            Tuple of (pooled_effect, confidence_interval, weights)
        """
        tau_squared = heterogeneity.tau_squared

        # Calculate weights (inverse of total variance)
        weights = [1 / (s.standard_error**2 + tau_squared) for s in studies]  # type: ignore
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate pooled effect
        pooled_effect = sum(s.effect * w for s, w in zip(studies, normalized_weights))  # type: ignore

        # Calculate standard error
        pooled_se = math.sqrt(1 / total_weight)

        # Calculate confidence interval
        z_crit = stats.norm.ppf(1 - self.alpha / 2)
        ci = ConfidenceInterval(
            lower=pooled_effect - z_crit * pooled_se,
            upper=pooled_effect + z_crit * pooled_se,
            level=self.confidence_level,
        )

        # Calculate prediction interval
        prediction_se = math.sqrt(pooled_se**2 + tau_squared)
        prediction_interval = ConfidenceInterval(
            lower=pooled_effect - z_crit * prediction_se,
            upper=pooled_effect + z_crit * prediction_se,
            level=self.confidence_level,
        )
        heterogeneity.prediction_interval = prediction_interval

        return pooled_effect, ci, normalized_weights

    def _calculate_heterogeneity(self, studies: list[StudyData]) -> Heterogeneity:
        """Calculate heterogeneity statistics (Q, I², tau²).

        Args:
            studies: List of studies with effect and SE

        Returns:
            Heterogeneity object with all statistics
        """
        k = len(studies)  # Number of studies

        # Calculate fixed-effects pooled estimate for Q statistic
        weights = [1 / (s.standard_error**2) for s in studies]  # type: ignore
        total_weight = sum(weights)
        pooled_effect = sum(s.effect * w for s, w in zip(studies, weights)) / total_weight  # type: ignore

        # Calculate Q statistic
        q_statistic = sum(w * (s.effect - pooled_effect) ** 2 for s, w in zip(studies, weights))  # type: ignore

        # Degrees of freedom
        df = k - 1

        # P-value for Q test
        q_p_value = 1 - stats.chi2.cdf(q_statistic, df) if df > 0 else 1.0

        # Calculate I² (percentage of variation due to heterogeneity)
        i_squared = max(0, ((q_statistic - df) / q_statistic) * 100) if q_statistic > 0 else 0

        # Calculate tau² (between-study variance) using DerSimonian-Laird method
        c = total_weight - sum(w**2 for w in weights) / total_weight
        tau_squared = max(0, (q_statistic - df) / c) if c > 0 and df > 0 else 0

        return Heterogeneity(
            i_squared=i_squared,
            tau_squared=tau_squared,
            q_statistic=q_statistic,
            q_p_value=q_p_value,
        )

    def egger_test(self, studies: list[StudyData]) -> float:
        """Perform Egger's test for publication bias.

        Args:
            studies: List of studies with effect and SE

        Returns:
            P-value for Egger's test
        """
        if len(studies) < 3:
            raise ValueError("Egger's test requires at least 3 studies")

        # Prepare data
        effects = np.array([s.effect for s in studies])
        ses = np.array([s.standard_error for s in studies])
        precisions = 1 / ses

        # Linear regression: effect/SE ~ 1/SE
        standardized_effects = effects / ses

        # Perform regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(precisions, standardized_effects)

        # Egger's test p-value is the p-value for the intercept
        # We use the t-statistic for the intercept
        t_stat = intercept / std_err
        df = len(studies) - 2
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

        return p_value

    def subgroup_analysis(
        self,
        studies: list[StudyData],
        subgroup_func: Callable[[StudyData], str],
        method: AnalysisMethod = AnalysisMethod.RANDOM_EFFECTS,
        effect_measure: EffectMeasure = EffectMeasure.MEAN_DIFFERENCE,
    ) -> dict[str, MetaAnalysisResult]:
        """Perform subgroup meta-analysis.

        Args:
            studies: List of studies
            subgroup_func: Function that assigns each study to a subgroup
            method: Analysis method
            effect_measure: Effect measure

        Returns:
            Dictionary mapping subgroup name to meta-analysis result
        """
        # Group studies by subgroup
        subgroups: dict[str, list[StudyData]] = {}
        for study in studies:
            subgroup_name = subgroup_func(study)
            if subgroup_name not in subgroups:
                subgroups[subgroup_name] = []
            subgroups[subgroup_name].append(study)

        # Perform meta-analysis for each subgroup
        results = {}
        for subgroup_name, subgroup_studies in subgroups.items():
            if len(subgroup_studies) >= 2:
                result = self.calculate_pooled_effect(subgroup_studies, method, effect_measure)
                result.outcome_name = f"Subgroup: {subgroup_name}"
                results[subgroup_name] = result

        return results

    def leave_one_out_analysis(
        self,
        studies: list[StudyData],
        method: AnalysisMethod = AnalysisMethod.RANDOM_EFFECTS,
        effect_measure: EffectMeasure = EffectMeasure.MEAN_DIFFERENCE,
    ) -> list[MetaAnalysisResult]:
        """Perform leave-one-out sensitivity analysis.

        Args:
            studies: List of studies
            method: Analysis method
            effect_measure: Effect measure

        Returns:
            List of meta-analysis results, each excluding one study
        """
        results = []

        for i, excluded_study in enumerate(studies):
            remaining_studies = [s for j, s in enumerate(studies) if j != i]
            if len(remaining_studies) >= 2:
                result = self.calculate_pooled_effect(remaining_studies, method, effect_measure)
                result.outcome_name = f"Excluding {excluded_study.study_id}"
                results.append(result)

        return results
