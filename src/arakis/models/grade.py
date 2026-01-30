"""Data models for GRADE (Grading of Recommendations Assessment, Development and Evaluation).

GRADE is a systematic approach for rating the certainty of evidence and strength
of recommendations in systematic reviews and clinical practice guidelines.

Reference:
- Guyatt GH, et al. BMJ 2008;336:924-926 (GRADE introduction)
- Balshem H, et al. J Clin Epidemiol 2011;64:401-406 (GRADE guidelines)
- Schunemann HJ, et al. J Clin Epidemiol 2013;66:140-150 (GRADE guidelines series)
- GRADEpro GDT: https://gradepro.org/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from arakis.models.analysis import ConfidenceInterval, EffectMeasure


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CertaintyLevel(str, Enum):
    """GRADE certainty of evidence levels.

    Reference: Balshem H, et al. J Clin Epidemiol 2011;64:401-406
    """

    HIGH = "high"  # Very confident effect lies close to estimate
    MODERATE = "moderate"  # Moderately confident; true effect likely close
    LOW = "low"  # Limited confidence; true effect may be substantially different
    VERY_LOW = "very_low"  # Very little confidence; true effect likely substantially different

    @property
    def symbol(self) -> str:
        """Return symbol representation for tables."""
        symbols = {
            CertaintyLevel.HIGH: "⊕⊕⊕⊕",
            CertaintyLevel.MODERATE: "⊕⊕⊕◯",
            CertaintyLevel.LOW: "⊕⊕◯◯",
            CertaintyLevel.VERY_LOW: "⊕◯◯◯",
        }
        return symbols[self]

    @property
    def ascii_symbol(self) -> str:
        """Return ASCII-safe symbol representation."""
        symbols = {
            CertaintyLevel.HIGH: "++++",
            CertaintyLevel.MODERATE: "+++O",
            CertaintyLevel.LOW: "++OO",
            CertaintyLevel.VERY_LOW: "+OOO",
        }
        return symbols[self]

    @property
    def html_symbol(self) -> str:
        """Return HTML symbol representation with colors."""
        filled = '<span style="color:#2e7d32;">&#x2295;</span>'  # Green filled
        empty = '<span style="color:#9e9e9e;">&#x25CB;</span>'  # Gray empty
        counts = {
            CertaintyLevel.HIGH: (4, 0),
            CertaintyLevel.MODERATE: (3, 1),
            CertaintyLevel.LOW: (2, 2),
            CertaintyLevel.VERY_LOW: (1, 3),
        }
        filled_count, empty_count = counts[self]
        return filled * filled_count + empty * empty_count

    @classmethod
    def from_rating(cls, rating: int) -> CertaintyLevel:
        """Convert numeric rating (1-4) to certainty level.

        Args:
            rating: 4=high, 3=moderate, 2=low, 1=very low

        Returns:
            CertaintyLevel
        """
        mapping = {
            4: cls.HIGH,
            3: cls.MODERATE,
            2: cls.LOW,
            1: cls.VERY_LOW,
        }
        return mapping.get(rating, cls.VERY_LOW)


class GRADEDomain(str, Enum):
    """GRADE domains for rating down or rating up evidence.

    Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:383-394
    """

    # Domains for rating DOWN (limitations)
    RISK_OF_BIAS = "risk_of_bias"  # Study limitations
    INCONSISTENCY = "inconsistency"  # Heterogeneity of results
    INDIRECTNESS = "indirectness"  # Applicability to target population
    IMPRECISION = "imprecision"  # Wide confidence intervals
    PUBLICATION_BIAS = "publication_bias"  # Selective reporting

    # Domains for rating UP (only for observational studies)
    LARGE_EFFECT = "large_effect"  # Large magnitude of effect
    DOSE_RESPONSE = "dose_response"  # Dose-response gradient
    CONFOUNDING = "confounding"  # Plausible confounding would reduce effect


GRADE_DOMAIN_DESCRIPTIONS = {
    GRADEDomain.RISK_OF_BIAS: "Risk of bias in included studies",
    GRADEDomain.INCONSISTENCY: "Unexplained heterogeneity in results",
    GRADEDomain.INDIRECTNESS: "Differences from target population/intervention/outcome",
    GRADEDomain.IMPRECISION: "Wide confidence intervals crossing clinical thresholds",
    GRADEDomain.PUBLICATION_BIAS: "Systematic underestimation or overestimation due to selective publication",
    GRADEDomain.LARGE_EFFECT: "Large magnitude of effect (RR > 2 or < 0.5)",
    GRADEDomain.DOSE_RESPONSE: "Evidence of dose-response gradient",
    GRADEDomain.CONFOUNDING: "Plausible confounding would reduce demonstrated effect",
}


class RatingAction(str, Enum):
    """Rating modification action."""

    NO_CHANGE = "no_change"
    DOWNGRADE_1 = "downgrade_1"  # Serious concern
    DOWNGRADE_2 = "downgrade_2"  # Very serious concern
    UPGRADE_1 = "upgrade_1"  # For observational studies only
    UPGRADE_2 = "upgrade_2"  # For observational studies only


@dataclass
class DomainRating:
    """Rating for a single GRADE domain.

    Captures the assessment of one domain and its effect on certainty.
    """

    domain: GRADEDomain
    action: RatingAction
    explanation: str = ""
    supporting_data: dict[str, Any] = field(default_factory=dict)

    @property
    def level_change(self) -> int:
        """Get the level change (negative = downgrade, positive = upgrade)."""
        changes = {
            RatingAction.NO_CHANGE: 0,
            RatingAction.DOWNGRADE_1: -1,
            RatingAction.DOWNGRADE_2: -2,
            RatingAction.UPGRADE_1: 1,
            RatingAction.UPGRADE_2: 2,
        }
        return changes[self.action]

    @property
    def concern_level(self) -> str:
        """Get human-readable concern level."""
        levels = {
            RatingAction.NO_CHANGE: "not serious",
            RatingAction.DOWNGRADE_1: "serious",
            RatingAction.DOWNGRADE_2: "very serious",
            RatingAction.UPGRADE_1: "upgrade",
            RatingAction.UPGRADE_2: "strong upgrade",
        }
        return levels[self.action]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain.value,
            "action": self.action.value,
            "explanation": self.explanation,
            "supporting_data": self.supporting_data,
            "level_change": self.level_change,
            "concern_level": self.concern_level,
        }


@dataclass
class GRADEAssessment:
    """Complete GRADE assessment for a single outcome.

    Combines domain ratings to determine overall certainty of evidence.
    """

    outcome_name: str
    study_design: str  # "RCT" or "observational" (determines starting level)
    n_studies: int
    total_sample_size: int

    # Domain ratings
    risk_of_bias: DomainRating
    inconsistency: DomainRating
    indirectness: DomainRating
    imprecision: DomainRating
    publication_bias: DomainRating

    # Upgrade domains (only applicable for observational studies)
    large_effect: DomainRating | None = None
    dose_response: DomainRating | None = None
    confounding: DomainRating | None = None

    # Overall
    overall_certainty: CertaintyLevel | None = None
    overall_explanation: str = ""

    # Metadata
    assessed_at: datetime = field(default_factory=_utc_now)
    assessed_by: str = "GRADEAssessor"

    def __post_init__(self) -> None:
        """Calculate overall certainty if not provided."""
        if self.overall_certainty is None:
            self.overall_certainty = self._calculate_certainty()

    @property
    def starting_level(self) -> int:
        """Get starting certainty level based on study design.

        RCTs start at HIGH (4), observational studies start at LOW (2).
        """
        return 4 if self.study_design.upper() in ["RCT", "RANDOMIZED"] else 2

    @property
    def domain_ratings(self) -> list[DomainRating]:
        """Get all domain ratings as a list."""
        ratings = [
            self.risk_of_bias,
            self.inconsistency,
            self.indirectness,
            self.imprecision,
            self.publication_bias,
        ]
        # Add upgrade domains if present
        if self.large_effect:
            ratings.append(self.large_effect)
        if self.dose_response:
            ratings.append(self.dose_response)
        if self.confounding:
            ratings.append(self.confounding)
        return ratings

    @property
    def total_downgrades(self) -> int:
        """Total number of levels downgraded."""
        return abs(sum(r.level_change for r in self.domain_ratings if r.level_change < 0))

    @property
    def total_upgrades(self) -> int:
        """Total number of levels upgraded."""
        return sum(r.level_change for r in self.domain_ratings if r.level_change > 0)

    def _calculate_certainty(self) -> CertaintyLevel:
        """Calculate overall certainty from domain ratings.

        Starting level:
        - RCTs: HIGH (4)
        - Observational: LOW (2)

        Then apply downgrades and upgrades, bounded by [1, 4].
        """
        level = self.starting_level

        # Apply all level changes
        for rating in self.domain_ratings:
            level += rating.level_change

        # Bound the result
        level = max(1, min(4, level))

        return CertaintyLevel.from_rating(level)

    def get_downgrade_summary(self) -> list[str]:
        """Get summary of all downgrades."""
        summaries = []
        for rating in self.domain_ratings:
            if rating.level_change < 0:
                summaries.append(
                    f"{rating.domain.value.replace('_', ' ').title()}: "
                    f"{rating.concern_level} ({abs(rating.level_change)} level{'s' if abs(rating.level_change) > 1 else ''})"
                )
        return summaries

    def get_upgrade_summary(self) -> list[str]:
        """Get summary of all upgrades."""
        summaries = []
        for rating in self.domain_ratings:
            if rating.level_change > 0:
                summaries.append(
                    f"{rating.domain.value.replace('_', ' ').title()}: "
                    f"{rating.concern_level} ({rating.level_change} level{'s' if rating.level_change > 1 else ''})"
                )
        return summaries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "outcome_name": self.outcome_name,
            "study_design": self.study_design,
            "n_studies": self.n_studies,
            "total_sample_size": self.total_sample_size,
            "starting_level": self.starting_level,
            "risk_of_bias": self.risk_of_bias.to_dict(),
            "inconsistency": self.inconsistency.to_dict(),
            "indirectness": self.indirectness.to_dict(),
            "imprecision": self.imprecision.to_dict(),
            "publication_bias": self.publication_bias.to_dict(),
            "large_effect": self.large_effect.to_dict() if self.large_effect else None,
            "dose_response": self.dose_response.to_dict() if self.dose_response else None,
            "confounding": self.confounding.to_dict() if self.confounding else None,
            "total_downgrades": self.total_downgrades,
            "total_upgrades": self.total_upgrades,
            "overall_certainty": self.overall_certainty.value if self.overall_certainty else None,
            "overall_explanation": self.overall_explanation,
            "assessed_at": self.assessed_at.isoformat(),
            "assessed_by": self.assessed_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GRADEAssessment:
        """Create from dictionary."""

        def parse_rating(d: dict[str, Any]) -> DomainRating:
            return DomainRating(
                domain=GRADEDomain(d["domain"]),
                action=RatingAction(d["action"]),
                explanation=d.get("explanation", ""),
                supporting_data=d.get("supporting_data", {}),
            )

        assessment = cls(
            outcome_name=data["outcome_name"],
            study_design=data["study_design"],
            n_studies=data["n_studies"],
            total_sample_size=data["total_sample_size"],
            risk_of_bias=parse_rating(data["risk_of_bias"]),
            inconsistency=parse_rating(data["inconsistency"]),
            indirectness=parse_rating(data["indirectness"]),
            imprecision=parse_rating(data["imprecision"]),
            publication_bias=parse_rating(data["publication_bias"]),
            large_effect=parse_rating(data["large_effect"]) if data.get("large_effect") else None,
            dose_response=parse_rating(data["dose_response"])
            if data.get("dose_response")
            else None,
            confounding=parse_rating(data["confounding"]) if data.get("confounding") else None,
            overall_certainty=CertaintyLevel(data["overall_certainty"])
            if data.get("overall_certainty")
            else None,
            overall_explanation=data.get("overall_explanation", ""),
            assessed_by=data.get("assessed_by", "GRADEAssessor"),
        )
        return assessment


@dataclass
class OutcomeData:
    """Data for a single outcome in the Summary of Findings table.

    Contains effect estimates, absolute effects, and GRADE assessment.
    """

    outcome_name: str
    outcome_description: str = ""

    # Number of studies and participants
    n_studies: int = 0
    n_participants: int = 0

    # Relative effect (from meta-analysis)
    relative_effect: float | None = None  # e.g., OR, RR, MD, SMD
    relative_effect_ci: ConfidenceInterval | None = None
    effect_measure: EffectMeasure | None = None

    # Absolute effect (events per 1000 or mean difference)
    control_risk: float | None = None  # Baseline risk in control group (per 1000)
    intervention_risk: float | None = None  # Expected risk with intervention (per 1000)
    absolute_effect: float | None = None  # Difference (per 1000 or actual units)
    absolute_effect_ci: ConfidenceInterval | None = None

    # GRADE assessment
    grade_assessment: GRADEAssessment | None = None

    # Importance
    importance: str = ""  # "critical", "important", "not important"

    # Comments
    comments: str = ""

    @property
    def certainty(self) -> CertaintyLevel | None:
        """Get certainty level from GRADE assessment."""
        return self.grade_assessment.overall_certainty if self.grade_assessment else None

    def format_relative_effect(self) -> str:
        """Format relative effect with CI."""
        if self.relative_effect is None:
            return "—"

        from arakis.traceability import DEFAULT_PRECISION

        # Format based on effect measure
        is_log_scale = self.effect_measure in [
            EffectMeasure.ODDS_RATIO,
            EffectMeasure.RISK_RATIO,
        ]

        effect_str = DEFAULT_PRECISION.format_effect(self.relative_effect, is_log_scale)

        if self.relative_effect_ci:
            ci_str = DEFAULT_PRECISION.format_ci(
                self.relative_effect_ci.lower,
                self.relative_effect_ci.upper,
            )
            return f"{effect_str} {ci_str}"
        return effect_str

    def format_absolute_effect(self) -> str:
        """Format absolute effect."""
        if self.absolute_effect is None:
            return "—"

        from arakis.traceability import DEFAULT_PRECISION

        # Format as "X fewer/more per 1000" for binary outcomes
        if self.effect_measure in [
            EffectMeasure.ODDS_RATIO,
            EffectMeasure.RISK_RATIO,
            EffectMeasure.RISK_DIFFERENCE,
        ]:
            direction = "fewer" if self.absolute_effect < 0 else "more"
            abs_val = abs(self.absolute_effect)
            effect_str = f"{abs_val:.0f} {direction} per 1000"

            if self.absolute_effect_ci:
                ci_lower = abs(self.absolute_effect_ci.lower)
                ci_upper = abs(self.absolute_effect_ci.upper)
                effect_str += f" ({ci_lower:.0f} to {ci_upper:.0f})"
            return effect_str

        # For continuous outcomes
        effect_str = DEFAULT_PRECISION.format_effect(self.absolute_effect)
        if self.absolute_effect_ci:
            ci_str = DEFAULT_PRECISION.format_ci(
                self.absolute_effect_ci.lower,
                self.absolute_effect_ci.upper,
            )
            return f"{effect_str} {ci_str}"
        return effect_str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "outcome_name": self.outcome_name,
            "outcome_description": self.outcome_description,
            "n_studies": self.n_studies,
            "n_participants": self.n_participants,
            "relative_effect": self.relative_effect,
            "relative_effect_ci": {
                "lower": self.relative_effect_ci.lower,
                "upper": self.relative_effect_ci.upper,
            }
            if self.relative_effect_ci
            else None,
            "effect_measure": self.effect_measure.value if self.effect_measure else None,
            "control_risk": self.control_risk,
            "intervention_risk": self.intervention_risk,
            "absolute_effect": self.absolute_effect,
            "absolute_effect_ci": {
                "lower": self.absolute_effect_ci.lower,
                "upper": self.absolute_effect_ci.upper,
            }
            if self.absolute_effect_ci
            else None,
            "grade_assessment": self.grade_assessment.to_dict() if self.grade_assessment else None,
            "certainty": self.certainty.value if self.certainty else None,
            "importance": self.importance,
            "comments": self.comments,
        }


@dataclass
class SummaryOfFindings:
    """GRADE Summary of Findings table.

    Standard format for presenting evidence across multiple outcomes.
    Reference: Guyatt GH, et al. J Clin Epidemiol 2011;64:383-394
    """

    # Review information
    review_title: str
    population: str
    intervention: str
    comparison: str
    setting: str = ""

    # Outcomes
    outcomes: list[OutcomeData] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=_utc_now)
    footnotes: list[str] = field(default_factory=list)

    @property
    def n_outcomes(self) -> int:
        """Number of outcomes in the table."""
        return len(self.outcomes)

    @property
    def certainty_distribution(self) -> dict[CertaintyLevel, int]:
        """Distribution of certainty levels across outcomes."""
        dist: dict[CertaintyLevel, int] = {level: 0 for level in CertaintyLevel}
        for outcome in self.outcomes:
            if outcome.certainty:
                dist[outcome.certainty] += 1
        return dist

    def add_outcome(self, outcome: OutcomeData) -> None:
        """Add an outcome to the table."""
        self.outcomes.append(outcome)

    def add_footnote(self, footnote: str) -> None:
        """Add a footnote to the table."""
        self.footnotes.append(footnote)

    def get_outcome(self, name: str) -> OutcomeData | None:
        """Get outcome by name."""
        return next((o for o in self.outcomes if o.outcome_name == name), None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_title": self.review_title,
            "population": self.population,
            "intervention": self.intervention,
            "comparison": self.comparison,
            "setting": self.setting,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "certainty_distribution": {k.value: v for k, v in self.certainty_distribution.items()},
            "n_outcomes": self.n_outcomes,
            "created_at": self.created_at.isoformat(),
            "footnotes": self.footnotes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummaryOfFindings:
        """Create from dictionary."""
        outcomes = []
        for o_data in data.get("outcomes", []):
            grade_data = o_data.get("grade_assessment")
            grade_assessment = GRADEAssessment.from_dict(grade_data) if grade_data else None

            outcome = OutcomeData(
                outcome_name=o_data["outcome_name"],
                outcome_description=o_data.get("outcome_description", ""),
                n_studies=o_data.get("n_studies", 0),
                n_participants=o_data.get("n_participants", 0),
                relative_effect=o_data.get("relative_effect"),
                relative_effect_ci=ConfidenceInterval(
                    lower=o_data["relative_effect_ci"]["lower"],
                    upper=o_data["relative_effect_ci"]["upper"],
                )
                if o_data.get("relative_effect_ci")
                else None,
                effect_measure=EffectMeasure(o_data["effect_measure"])
                if o_data.get("effect_measure")
                else None,
                control_risk=o_data.get("control_risk"),
                intervention_risk=o_data.get("intervention_risk"),
                absolute_effect=o_data.get("absolute_effect"),
                absolute_effect_ci=ConfidenceInterval(
                    lower=o_data["absolute_effect_ci"]["lower"],
                    upper=o_data["absolute_effect_ci"]["upper"],
                )
                if o_data.get("absolute_effect_ci")
                else None,
                grade_assessment=grade_assessment,
                importance=o_data.get("importance", ""),
                comments=o_data.get("comments", ""),
            )
            outcomes.append(outcome)

        return cls(
            review_title=data["review_title"],
            population=data["population"],
            intervention=data["intervention"],
            comparison=data["comparison"],
            setting=data.get("setting", ""),
            outcomes=outcomes,
            footnotes=data.get("footnotes", []),
        )


@dataclass
class GRADEEvidenceProfile:
    """GRADE Evidence Profile (detailed version of Summary of Findings).

    Shows detailed domain-level assessments for each outcome.
    """

    # Review information
    review_title: str
    comparison: str  # "Intervention vs Control"

    # Outcomes with assessments
    outcomes: list[OutcomeData] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=_utc_now)
    footnotes: list[str] = field(default_factory=list)

    def add_outcome(self, outcome: OutcomeData) -> None:
        """Add an outcome to the profile."""
        self.outcomes.append(outcome)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_title": self.review_title,
            "comparison": self.comparison,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "created_at": self.created_at.isoformat(),
            "footnotes": self.footnotes,
        }
