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
class StudySummary:
    """Summary of a single study for narrative synthesis."""

    study_id: str
    study_name: str = ""
    sample_size: Optional[int] = None
    study_design: Optional[str] = None
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcome_description: Optional[str] = None
    main_finding: Optional[str] = None
    effect_direction: Optional[str] = None  # "positive", "negative", "null", "mixed"
    effect_magnitude: Optional[str] = None  # "large", "moderate", "small", "negligible"
    quality_score: Optional[float] = None
    key_limitations: list[str] = field(default_factory=list)


@dataclass
class VoteCount:
    """Vote counting results for direction of effects."""

    positive: int = 0  # Studies showing beneficial/positive effect
    negative: int = 0  # Studies showing harmful/negative effect
    null: int = 0  # Studies showing no significant effect
    mixed: int = 0  # Studies with mixed or unclear results

    @property
    def total(self) -> int:
        """Total number of studies."""
        return self.positive + self.negative + self.null + self.mixed

    @property
    def predominant_direction(self) -> str:
        """Get the predominant direction of effect."""
        counts = {
            "positive": self.positive,
            "negative": self.negative,
            "null": self.null,
            "mixed": self.mixed,
        }
        max_count = max(counts.values())
        if max_count == 0:
            return "insufficient data"
        predominant = [k for k, v in counts.items() if v == max_count]
        if len(predominant) > 1:
            return "inconclusive"
        return predominant[0]

    @property
    def consistency(self) -> str:
        """Assess consistency of findings."""
        if self.total == 0:
            return "no studies"
        max_proportion = max(self.positive, self.negative, self.null, self.mixed) / self.total
        if max_proportion >= 0.75:
            return "consistent"
        elif max_proportion >= 0.5:
            return "moderately consistent"
        else:
            return "inconsistent"


@dataclass
class NarrativeSynthesisResult:
    """Result from narrative synthesis when meta-analysis is not feasible.

    Provides qualitative summary of findings across studies using
    structured narrative synthesis methods.
    """

    # Core synthesis
    outcome_name: str
    studies_included: int
    total_sample_size: int

    # Study summaries
    study_summaries: list[StudySummary] = field(default_factory=list)

    # Vote counting
    vote_count: Optional[VoteCount] = None

    # Synthesis narrative
    summary_of_findings: str = ""  # Overall summary paragraph
    heterogeneity_explanation: str = ""  # Why studies differ
    evidence_quality_assessment: str = ""  # GRADE-like assessment
    confidence_in_evidence: str = ""  # "high", "moderate", "low", "very low"

    # Patterns and themes
    patterns_identified: list[str] = field(default_factory=list)
    inconsistencies: list[str] = field(default_factory=list)
    gaps_in_evidence: list[str] = field(default_factory=list)

    # Why meta-analysis was not feasible
    meta_analysis_barriers: list[str] = field(default_factory=list)

    # Groupings (if studies were grouped for synthesis)
    subgroups: dict[str, list[str]] = field(default_factory=dict)  # group_name -> [study_ids]

    # Visualizations
    summary_table_path: Optional[str] = None
    effect_direction_chart_path: Optional[str] = None

    # Metadata
    synthesis_method: str = "narrative"  # Could be extended for other methods
    timestamp: str = ""
    analysis_time_ms: int = 0

    @property
    def has_sufficient_data(self) -> bool:
        """Check if there's sufficient data for meaningful synthesis."""
        return self.studies_included >= 2

    @property
    def effect_direction_summary(self) -> str:
        """Get a one-sentence summary of effect direction."""
        if self.vote_count is None or self.vote_count.total == 0:
            return "No studies available to assess effect direction."

        vc = self.vote_count
        if vc.consistency == "consistent":
            if vc.predominant_direction == "positive":
                return f"{vc.positive} of {vc.total} studies showed a beneficial effect."
            elif vc.predominant_direction == "negative":
                return f"{vc.negative} of {vc.total} studies showed a harmful effect."
            elif vc.predominant_direction == "null":
                return f"{vc.null} of {vc.total} studies showed no significant effect."
        return f"Results were {vc.consistency}: {vc.positive} positive, {vc.negative} negative, {vc.null} null, {vc.mixed} mixed."

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "outcome_name": self.outcome_name,
            "studies_included": self.studies_included,
            "total_sample_size": self.total_sample_size,
            "study_summaries": [
                {
                    "study_id": s.study_id,
                    "study_name": s.study_name,
                    "sample_size": s.sample_size,
                    "study_design": s.study_design,
                    "population": s.population,
                    "intervention": s.intervention,
                    "comparator": s.comparator,
                    "outcome_description": s.outcome_description,
                    "main_finding": s.main_finding,
                    "effect_direction": s.effect_direction,
                    "effect_magnitude": s.effect_magnitude,
                    "quality_score": s.quality_score,
                    "key_limitations": s.key_limitations,
                }
                for s in self.study_summaries
            ],
            "vote_count": {
                "positive": self.vote_count.positive,
                "negative": self.vote_count.negative,
                "null": self.vote_count.null,
                "mixed": self.vote_count.mixed,
                "total": self.vote_count.total,
                "predominant_direction": self.vote_count.predominant_direction,
                "consistency": self.vote_count.consistency,
            }
            if self.vote_count
            else None,
            "summary_of_findings": self.summary_of_findings,
            "heterogeneity_explanation": self.heterogeneity_explanation,
            "evidence_quality_assessment": self.evidence_quality_assessment,
            "confidence_in_evidence": self.confidence_in_evidence,
            "effect_direction_summary": self.effect_direction_summary,
            "patterns_identified": self.patterns_identified,
            "inconsistencies": self.inconsistencies,
            "gaps_in_evidence": self.gaps_in_evidence,
            "meta_analysis_barriers": self.meta_analysis_barriers,
            "subgroups": self.subgroups,
            "summary_table_path": self.summary_table_path,
            "effect_direction_chart_path": self.effect_direction_chart_path,
            "synthesis_method": self.synthesis_method,
            "timestamp": self.timestamp,
            "analysis_time_ms": self.analysis_time_ms,
        }


@dataclass
class ComprehensiveAnalysis:
    """Complete analysis of extracted data."""

    # Input
    extraction_result_path: str
    outcome_analyzed: str

    # Recommendations
    recommendation: Optional[AnalysisRecommendation] = None

    # Results - can be meta-analysis OR narrative synthesis
    primary_analysis: Optional[
        Union[AnalysisResult, MetaAnalysisResult, NarrativeSynthesisResult]
    ] = None
    secondary_analyses: list[AnalysisResult] = field(default_factory=list)

    # Metadata
    timestamp: str = ""
    analysis_time_ms: int = 0
    cost_usd: float = 0.0
