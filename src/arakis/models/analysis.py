"""Data models for statistical analysis.

Models for statistical tests, analysis results, and meta-analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class TestType(str, Enum):
    """Type of statistical test."""

    PARAMETRIC = "parametric"
    NON_PARAMETRIC = "non_parametric"
    META_ANALYSIS = "meta_analysis"
    DESCRIPTIVE = "descriptive"


class AnalysisMethod(str, Enum):
    """Meta-analysis method."""

    RANDOM_EFFECTS = "random_effects"
    FIXED_EFFECTS = "fixed_effects"


class EffectMeasure(str, Enum):
    """Type of effect measure."""

    MEAN_DIFFERENCE = "mean_difference"
    STANDARDIZED_MEAN_DIFFERENCE = "standardized_mean_difference"
    ODDS_RATIO = "odds_ratio"
    RISK_RATIO = "risk_ratio"
    RISK_DIFFERENCE = "risk_difference"
    CORRELATION = "correlation"


@dataclass
class StatisticalTest:
    """Statistical test specification."""

    test_name: str  # e.g., "t-test", "chi-square", "random-effects-ma"
    test_type: TestType
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ConfidenceInterval:
    """Confidence interval."""

    lower: float
    upper: float
    level: float = 0.95  # Confidence level (e.g., 0.95 for 95% CI)


@dataclass
class Heterogeneity:
    """Heterogeneity statistics for meta-analysis."""

    i_squared: float  # I² statistic (0-100%)
    tau_squared: float  # Between-study variance
    q_statistic: float  # Cochran's Q
    q_p_value: float  # P-value for Q test
    prediction_interval: Optional[ConfidenceInterval] = None


@dataclass
class AnalysisResult:
    """Result from a statistical test."""

    test_name: str
    test_type: TestType
    test_statistic: Optional[float] = None
    p_value: Optional[float] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    effect_size: Optional[float] = None
    effect_measure: Optional[EffectMeasure] = None
    interpretation: str = ""
    visualization_path: Optional[str] = None
    additional_stats: dict[str, Any] = field(default_factory=dict)

    @property
    def is_significant(self) -> bool:
        """Check if result is statistically significant (p < 0.05)."""
        if self.p_value is None:
            return False
        return self.p_value < 0.05


@dataclass
class StudyData:
    """Data from a single study for meta-analysis."""

    study_id: str
    study_name: str = ""

    # Effect estimate and precision
    effect: Optional[float] = None
    standard_error: Optional[float] = None
    confidence_interval: Optional[ConfidenceInterval] = None

    # Or raw data for calculation
    intervention_n: Optional[int] = None
    intervention_events: Optional[int] = None
    intervention_mean: Optional[float] = None
    intervention_sd: Optional[float] = None

    control_n: Optional[int] = None
    control_events: Optional[int] = None
    control_mean: Optional[float] = None
    control_sd: Optional[float] = None

    # Study characteristics
    weight: Optional[float] = None
    year: Optional[int] = None
    sample_size: Optional[int] = None
    quality_score: Optional[float] = None


@dataclass
class MetaAnalysisResult:
    """Result from a meta-analysis."""

    outcome_name: str
    studies_included: int
    total_sample_size: int

    # Pooled effect
    pooled_effect: float
    confidence_interval: ConfidenceInterval
    effect_measure: EffectMeasure

    # Heterogeneity
    heterogeneity: Heterogeneity

    # Statistical significance
    z_statistic: float
    p_value: float

    # Analysis method
    analysis_method: AnalysisMethod

    # Study data
    studies: list[StudyData] = field(default_factory=list)

    # Visualizations
    forest_plot_path: Optional[str] = None
    funnel_plot_path: Optional[str] = None

    # Publication bias
    egger_test_p_value: Optional[float] = None

    # Subgroup/sensitivity analyses
    subgroup_analyses: list[dict[str, Any]] = field(default_factory=list)
    sensitivity_analyses: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_significant(self) -> bool:
        """Check if result is statistically significant (p < 0.05)."""
        return self.p_value < 0.05

    @property
    def has_high_heterogeneity(self) -> bool:
        """Check if heterogeneity is substantial (I² > 50%)."""
        return self.heterogeneity.i_squared > 50.0


@dataclass
class AnalysisRecommendation:
    """LLM recommendation for statistical analysis."""

    recommended_tests: list[StatisticalTest]
    rationale: str
    data_characteristics: dict[str, Any] = field(default_factory=dict)
    assumptions_checked: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ComprehensiveAnalysis:
    """Complete analysis of extracted data."""

    # Input
    extraction_result_path: str
    outcome_analyzed: str

    # Recommendations
    recommendation: Optional[AnalysisRecommendation] = None

    # Results
    primary_analysis: Optional[Union[AnalysisResult, MetaAnalysisResult]] = None
    secondary_analyses: list[AnalysisResult] = field(default_factory=list)

    # Metadata
    timestamp: str = ""
    analysis_time_ms: int = 0
    cost_usd: float = 0.0
