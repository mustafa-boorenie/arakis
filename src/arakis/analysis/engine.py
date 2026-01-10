"""Statistical computation engine.

Pure Python statistical computations using scipy/statsmodels (NO LLM COST).
"""

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from arakis.models.analysis import (
    AnalysisResult,
    ConfidenceInterval,
    EffectMeasure,
    TestType,
)


class StatisticalEngine:
    """Engine for statistical test computations."""

    def __init__(self, confidence_level: float = 0.95):
        """Initialize statistical engine.

        Args:
            confidence_level: Confidence level for intervals (default 0.95 for 95% CI)
        """
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    # === Basic Parametric Tests ===

    def independent_t_test(
        self,
        group1: list[float] | np.ndarray,
        group2: list[float] | np.ndarray,
        equal_variance: bool = True,
    ) -> AnalysisResult:
        """Perform independent samples t-test.

        Args:
            group1: Data from first group
            group2: Data from second group
            equal_variance: If True, assume equal variance (Student's t-test),
                          otherwise use Welch's t-test

        Returns:
            AnalysisResult with t-statistic, p-value, effect size (Cohen's d), and CI
        """
        group1 = np.array(group1)
        group2 = np.array(group2)

        # Perform t-test
        statistic, p_value = stats.ttest_ind(group1, group2, equal_var=equal_variance)

        # Calculate Cohen's d
        cohens_d = self._calculate_cohens_d(group1, group2)

        # Calculate confidence interval for mean difference
        mean_diff = np.mean(group1) - np.mean(group2)
        se_diff = np.sqrt(np.var(group1, ddof=1) / len(group1) + np.var(group2, ddof=1) / len(group2))
        df = len(group1) + len(group2) - 2
        t_crit = stats.t.ppf(1 - self.alpha / 2, df)
        ci = ConfidenceInterval(
            lower=mean_diff - t_crit * se_diff,
            upper=mean_diff + t_crit * se_diff,
            level=self.confidence_level,
        )

        test_name = "Welch's t-test" if not equal_variance else "Student's t-test"

        return AnalysisResult(
            test_name=test_name,
            test_type=TestType.PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            confidence_interval=ci,
            effect_size=cohens_d,
            effect_measure=EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE,
            additional_stats={
                "mean_difference": float(mean_diff),
                "group1_mean": float(np.mean(group1)),
                "group2_mean": float(np.mean(group2)),
                "group1_sd": float(np.std(group1, ddof=1)),
                "group2_sd": float(np.std(group2, ddof=1)),
                "group1_n": len(group1),
                "group2_n": len(group2),
            },
        )

    def paired_t_test(
        self, before: list[float] | np.ndarray, after: list[float] | np.ndarray
    ) -> AnalysisResult:
        """Perform paired samples t-test.

        Args:
            before: Measurements before intervention
            after: Measurements after intervention

        Returns:
            AnalysisResult with t-statistic, p-value, and effect size
        """
        before = np.array(before)
        after = np.array(after)

        if len(before) != len(after):
            raise ValueError("Before and after groups must have same length for paired t-test")

        # Perform paired t-test
        statistic, p_value = stats.ttest_rel(before, after)

        # Calculate effect size (Cohen's d for paired samples)
        differences = after - before
        cohens_d = np.mean(differences) / np.std(differences, ddof=1)

        # Calculate confidence interval
        mean_diff = np.mean(differences)
        se = stats.sem(differences)
        df = len(differences) - 1
        t_crit = stats.t.ppf(1 - self.alpha / 2, df)
        ci = ConfidenceInterval(
            lower=mean_diff - t_crit * se, upper=mean_diff + t_crit * se, level=self.confidence_level
        )

        return AnalysisResult(
            test_name="Paired t-test",
            test_type=TestType.PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            confidence_interval=ci,
            effect_size=cohens_d,
            effect_measure=EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE,
            additional_stats={
                "mean_difference": float(mean_diff),
                "before_mean": float(np.mean(before)),
                "after_mean": float(np.mean(after)),
                "n_pairs": len(before),
            },
        )

    def one_way_anova(self, *groups: list[float] | np.ndarray) -> AnalysisResult:
        """Perform one-way ANOVA.

        Args:
            *groups: Variable number of groups to compare

        Returns:
            AnalysisResult with F-statistic and p-value
        """
        if len(groups) < 2:
            raise ValueError("ANOVA requires at least 2 groups")

        # Perform ANOVA
        statistic, p_value = stats.f_oneway(*groups)

        # Calculate eta-squared (effect size)
        grand_mean = np.mean([val for group in groups for val in group])
        ss_between = sum(len(group) * (np.mean(group) - grand_mean) ** 2 for group in groups)
        ss_total = sum((val - grand_mean) ** 2 for group in groups for val in group)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0

        return AnalysisResult(
            test_name="One-way ANOVA",
            test_type=TestType.PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            effect_size=eta_squared,
            additional_stats={
                "n_groups": len(groups),
                "group_means": [float(np.mean(g)) for g in groups],
                "group_sizes": [len(g) for g in groups],
            },
        )

    # === Non-Parametric Tests ===

    def mann_whitney_u(
        self, group1: list[float] | np.ndarray, group2: list[float] | np.ndarray
    ) -> AnalysisResult:
        """Perform Mann-Whitney U test (non-parametric alternative to t-test).

        Args:
            group1: Data from first group
            group2: Data from second group

        Returns:
            AnalysisResult with U-statistic and p-value
        """
        group1 = np.array(group1)
        group2 = np.array(group2)

        statistic, p_value = stats.mannwhitneyu(group1, group2, alternative="two-sided")

        # Calculate rank-biserial correlation (effect size)
        rank_biserial = 1 - (2 * statistic) / (len(group1) * len(group2))

        return AnalysisResult(
            test_name="Mann-Whitney U test",
            test_type=TestType.NON_PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            effect_size=rank_biserial,
            additional_stats={
                "group1_median": float(np.median(group1)),
                "group2_median": float(np.median(group2)),
                "group1_n": len(group1),
                "group2_n": len(group2),
            },
        )

    def wilcoxon_signed_rank(
        self, before: list[float] | np.ndarray, after: list[float] | np.ndarray
    ) -> AnalysisResult:
        """Perform Wilcoxon signed-rank test (non-parametric paired test).

        Args:
            before: Measurements before intervention
            after: Measurements after intervention

        Returns:
            AnalysisResult with test statistic and p-value
        """
        before = np.array(before)
        after = np.array(after)

        if len(before) != len(after):
            raise ValueError("Before and after groups must have same length")

        statistic, p_value = stats.wilcoxon(before, after)

        return AnalysisResult(
            test_name="Wilcoxon signed-rank test",
            test_type=TestType.NON_PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            additional_stats={
                "before_median": float(np.median(before)),
                "after_median": float(np.median(after)),
                "n_pairs": len(before),
            },
        )

    def kruskal_wallis(self, *groups: list[float] | np.ndarray) -> AnalysisResult:
        """Perform Kruskal-Wallis H test (non-parametric alternative to ANOVA).

        Args:
            *groups: Variable number of groups to compare

        Returns:
            AnalysisResult with H-statistic and p-value
        """
        if len(groups) < 2:
            raise ValueError("Kruskal-Wallis test requires at least 2 groups")

        statistic, p_value = stats.kruskal(*groups)

        return AnalysisResult(
            test_name="Kruskal-Wallis H test",
            test_type=TestType.NON_PARAMETRIC,
            test_statistic=float(statistic),
            p_value=float(p_value),
            additional_stats={
                "n_groups": len(groups),
                "group_medians": [float(np.median(g)) for g in groups],
                "group_sizes": [len(g) for g in groups],
            },
        )

    # === Categorical Tests ===

    def chi_square_test(
        self, observed: list[list[int]] | np.ndarray, correction: bool = True
    ) -> AnalysisResult:
        """Perform chi-square test of independence.

        Args:
            observed: 2D contingency table (rows x columns)
            correction: Apply Yates' correction for 2x2 tables

        Returns:
            AnalysisResult with chi-square statistic, p-value, and Cramér's V
        """
        observed = np.array(observed)

        # Perform chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(observed, correction=correction)

        # Calculate Cramér's V (effect size)
        n = np.sum(observed)
        min_dim = min(observed.shape[0], observed.shape[1]) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0

        return AnalysisResult(
            test_name="Chi-square test",
            test_type=TestType.PARAMETRIC,
            test_statistic=float(chi2),
            p_value=float(p_value),
            effect_size=cramers_v,
            additional_stats={
                "degrees_of_freedom": int(dof),
                "observed": observed.tolist(),
                "expected": expected.tolist(),
                "sample_size": int(n),
            },
        )

    def fishers_exact_test(self, table: list[list[int]]) -> AnalysisResult:
        """Perform Fisher's exact test (for 2x2 tables).

        Args:
            table: 2x2 contingency table [[a, b], [c, d]]

        Returns:
            AnalysisResult with odds ratio and p-value
        """
        table = np.array(table)

        if table.shape != (2, 2):
            raise ValueError("Fisher's exact test requires a 2x2 table")

        odds_ratio, p_value = stats.fisher_exact(table)

        return AnalysisResult(
            test_name="Fisher's exact test",
            test_type=TestType.PARAMETRIC,
            p_value=float(p_value),
            effect_size=float(odds_ratio),
            effect_measure=EffectMeasure.ODDS_RATIO,
            additional_stats={"contingency_table": table.tolist()},
        )

    # === Effect Sizes ===

    def _calculate_cohens_d(
        self, group1: np.ndarray, group2: np.ndarray, pooled: bool = True
    ) -> float:
        """Calculate Cohen's d effect size.

        Args:
            group1: First group data
            group2: Second group data
            pooled: Use pooled standard deviation (True) or control group SD (False)

        Returns:
            Cohen's d value
        """
        mean_diff = np.mean(group1) - np.mean(group2)

        if pooled:
            # Pooled standard deviation
            n1, n2 = len(group1), len(group2)
            var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
            pooled_sd = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
            return mean_diff / pooled_sd if pooled_sd > 0 else 0
        else:
            # Use control group (group2) SD
            sd2 = np.std(group2, ddof=1)
            return mean_diff / sd2 if sd2 > 0 else 0

    def calculate_odds_ratio(
        self, table: list[list[int]], confidence_level: float | None = None
    ) -> tuple[float, ConfidenceInterval]:
        """Calculate odds ratio and confidence interval.

        Args:
            table: 2x2 contingency table [[a, b], [c, d]]
            confidence_level: Confidence level (default uses engine's level)

        Returns:
            Tuple of (odds_ratio, confidence_interval)
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        table = np.array(table)
        a, b, c, d = table[0, 0], table[0, 1], table[1, 0], table[1, 1]

        # Add continuity correction if any cell is zero
        if any(x == 0 for x in [a, b, c, d]):
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5

        odds_ratio = (a * d) / (b * c)

        # Calculate CI using log transformation
        log_or = np.log(odds_ratio)
        se_log_or = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)

        ci = ConfidenceInterval(
            lower=np.exp(log_or - z * se_log_or),
            upper=np.exp(log_or + z * se_log_or),
            level=confidence_level,
        )

        return float(odds_ratio), ci

    def calculate_risk_ratio(
        self, table: list[list[int]], confidence_level: float | None = None
    ) -> tuple[float, ConfidenceInterval]:
        """Calculate risk ratio (relative risk) and confidence interval.

        Args:
            table: 2x2 contingency table [[a, b], [c, d]]
            confidence_level: Confidence level (default uses engine's level)

        Returns:
            Tuple of (risk_ratio, confidence_interval)
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        table = np.array(table)
        a, b, c, d = table[0, 0], table[0, 1], table[1, 0], table[1, 1]

        risk1 = a / (a + b)
        risk2 = c / (c + d)
        risk_ratio = risk1 / risk2 if risk2 > 0 else float("inf")

        # Calculate CI using log transformation
        log_rr = np.log(risk_ratio)
        se_log_rr = np.sqrt((1 / a - 1 / (a + b)) + (1 / c - 1 / (c + d)))
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)

        ci = ConfidenceInterval(
            lower=np.exp(log_rr - z * se_log_rr),
            upper=np.exp(log_rr + z * se_log_rr),
            level=confidence_level,
        )

        return float(risk_ratio), ci

    def calculate_mean_difference(
        self,
        group1_mean: float,
        group1_sd: float,
        group1_n: int,
        group2_mean: float,
        group2_sd: float,
        group2_n: int,
        confidence_level: float | None = None,
    ) -> tuple[float, ConfidenceInterval]:
        """Calculate mean difference and confidence interval.

        Args:
            group1_mean: Mean of first group
            group1_sd: Standard deviation of first group
            group1_n: Sample size of first group
            group2_mean: Mean of second group
            group2_sd: Standard deviation of second group
            group2_n: Sample size of second group
            confidence_level: Confidence level (default uses engine's level)

        Returns:
            Tuple of (mean_difference, confidence_interval)
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        mean_diff = group1_mean - group2_mean
        se = np.sqrt((group1_sd**2 / group1_n) + (group2_sd**2 / group2_n))

        df = group1_n + group2_n - 2
        t_crit = stats.t.ppf(1 - (1 - confidence_level) / 2, df)

        ci = ConfidenceInterval(
            lower=mean_diff - t_crit * se, upper=mean_diff + t_crit * se, level=confidence_level
        )

        return float(mean_diff), ci

    # === Correlation ===

    def pearson_correlation(
        self, x: list[float] | np.ndarray, y: list[float] | np.ndarray
    ) -> AnalysisResult:
        """Calculate Pearson correlation coefficient.

        Args:
            x: First variable
            y: Second variable

        Returns:
            AnalysisResult with correlation coefficient and p-value
        """
        x = np.array(x)
        y = np.array(y)

        r, p_value = stats.pearsonr(x, y)

        # Calculate confidence interval using Fisher z-transformation
        z = np.arctanh(r)
        se = 1 / np.sqrt(len(x) - 3)
        z_crit = stats.norm.ppf(1 - self.alpha / 2)
        ci_z = (z - z_crit * se, z + z_crit * se)
        ci = ConfidenceInterval(
            lower=np.tanh(ci_z[0]), upper=np.tanh(ci_z[1]), level=self.confidence_level
        )

        return AnalysisResult(
            test_name="Pearson correlation",
            test_type=TestType.PARAMETRIC,
            test_statistic=float(r),
            p_value=float(p_value),
            confidence_interval=ci,
            effect_size=float(r),
            effect_measure=EffectMeasure.CORRELATION,
            additional_stats={"n": len(x)},
        )

    def spearman_correlation(
        self, x: list[float] | np.ndarray, y: list[float] | np.ndarray
    ) -> AnalysisResult:
        """Calculate Spearman rank correlation coefficient (non-parametric).

        Args:
            x: First variable
            y: Second variable

        Returns:
            AnalysisResult with correlation coefficient and p-value
        """
        x = np.array(x)
        y = np.array(y)

        rho, p_value = stats.spearmanr(x, y)

        return AnalysisResult(
            test_name="Spearman correlation",
            test_type=TestType.NON_PARAMETRIC,
            test_statistic=float(rho),
            p_value=float(p_value),
            effect_size=float(rho),
            effect_measure=EffectMeasure.CORRELATION,
            additional_stats={"n": len(x)},
        )

    # === Normality Tests ===

    def shapiro_wilk_test(self, data: list[float] | np.ndarray) -> AnalysisResult:
        """Perform Shapiro-Wilk test for normality.

        Args:
            data: Sample data

        Returns:
            AnalysisResult with test statistic and p-value
        """
        data = np.array(data)

        if len(data) < 3:
            raise ValueError("Shapiro-Wilk test requires at least 3 observations")

        statistic, p_value = stats.shapiro(data)

        interpretation = (
            "Data appears normally distributed (p > 0.05)"
            if p_value > 0.05
            else "Data deviates from normality (p < 0.05)"
        )

        return AnalysisResult(
            test_name="Shapiro-Wilk test",
            test_type=TestType.DESCRIPTIVE,
            test_statistic=float(statistic),
            p_value=float(p_value),
            interpretation=interpretation,
            additional_stats={"n": len(data)},
        )
