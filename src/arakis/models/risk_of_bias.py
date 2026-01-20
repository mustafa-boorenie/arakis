"""Data models for Risk of Bias assessment.

Implements standardized risk of bias assessment tools:
- RoB 2 for randomized controlled trials (Cochrane RoB 2.0)
- ROBINS-I for non-randomized studies of interventions
- QUADAS-2 for diagnostic accuracy studies

Reference:
- Sterne JAC, et al. BMJ 2019;366:l4898 (RoB 2)
- Sterne JAC, et al. BMJ 2016;355:i4919 (ROBINS-I)
- Whiting PF, et al. Ann Intern Med 2011;155:529-536 (QUADAS-2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RiskLevel(str, Enum):
    """Risk of bias judgment levels."""

    LOW = "low"
    SOME_CONCERNS = "some_concerns"  # RoB 2 terminology
    HIGH = "high"
    UNCLEAR = "unclear"  # For incomplete information
    NOT_APPLICABLE = "not_applicable"

    @property
    def symbol(self) -> str:
        """Return traffic light symbol for visualization."""
        symbols = {
            RiskLevel.LOW: "+",
            RiskLevel.SOME_CONCERNS: "?",
            RiskLevel.HIGH: "-",
            RiskLevel.UNCLEAR: "?",
            RiskLevel.NOT_APPLICABLE: "NA",
        }
        return symbols[self]

    @property
    def color(self) -> str:
        """Return color for traffic light visualization."""
        colors = {
            RiskLevel.LOW: "#00a65a",  # Green
            RiskLevel.SOME_CONCERNS: "#f39c12",  # Yellow/Orange
            RiskLevel.HIGH: "#dd4b39",  # Red
            RiskLevel.UNCLEAR: "#f39c12",  # Yellow
            RiskLevel.NOT_APPLICABLE: "#d2d6de",  # Gray
        }
        return colors[self]


class RoBTool(str, Enum):
    """Available risk of bias assessment tools."""

    ROB_2 = "rob_2"  # For RCTs (Cochrane RoB 2.0)
    ROBINS_I = "robins_i"  # For non-randomized studies
    QUADAS_2 = "quadas_2"  # For diagnostic accuracy studies


# =============================================================================
# RoB 2 Domains (for RCTs)
# =============================================================================


class RoB2Domain(str, Enum):
    """RoB 2 domains for randomized controlled trials.

    Reference: Sterne JAC, et al. BMJ 2019;366:l4898
    """

    D1_RANDOMIZATION = "D1"  # Bias arising from the randomization process
    D2_DEVIATIONS = "D2"  # Bias due to deviations from intended interventions
    D3_MISSING_DATA = "D3"  # Bias due to missing outcome data
    D4_MEASUREMENT = "D4"  # Bias in measurement of the outcome
    D5_SELECTION = "D5"  # Bias in selection of the reported result
    OVERALL = "overall"


ROB2_DOMAIN_DESCRIPTIONS = {
    RoB2Domain.D1_RANDOMIZATION: "Bias arising from the randomization process",
    RoB2Domain.D2_DEVIATIONS: "Bias due to deviations from intended interventions",
    RoB2Domain.D3_MISSING_DATA: "Bias due to missing outcome data",
    RoB2Domain.D4_MEASUREMENT: "Bias in measurement of the outcome",
    RoB2Domain.D5_SELECTION: "Bias in selection of the reported result",
    RoB2Domain.OVERALL: "Overall risk of bias",
}

ROB2_DOMAIN_SHORT_NAMES = {
    RoB2Domain.D1_RANDOMIZATION: "Randomization",
    RoB2Domain.D2_DEVIATIONS: "Deviations",
    RoB2Domain.D3_MISSING_DATA: "Missing data",
    RoB2Domain.D4_MEASUREMENT: "Measurement",
    RoB2Domain.D5_SELECTION: "Selection",
    RoB2Domain.OVERALL: "Overall",
}


# =============================================================================
# ROBINS-I Domains (for non-randomized studies)
# =============================================================================


class ROBINSIDomain(str, Enum):
    """ROBINS-I domains for non-randomized studies of interventions.

    Reference: Sterne JAC, et al. BMJ 2016;355:i4919
    """

    D1_CONFOUNDING = "D1"  # Bias due to confounding
    D2_SELECTION = "D2"  # Bias in selection of participants
    D3_CLASSIFICATION = "D3"  # Bias in classification of interventions
    D4_DEVIATIONS = "D4"  # Bias due to deviations from intended interventions
    D5_MISSING_DATA = "D5"  # Bias due to missing data
    D6_MEASUREMENT = "D6"  # Bias in measurement of outcomes
    D7_REPORTING = "D7"  # Bias in selection of the reported result
    OVERALL = "overall"


ROBINSI_DOMAIN_DESCRIPTIONS = {
    ROBINSIDomain.D1_CONFOUNDING: "Bias due to confounding",
    ROBINSIDomain.D2_SELECTION: "Bias in selection of participants into the study",
    ROBINSIDomain.D3_CLASSIFICATION: "Bias in classification of interventions",
    ROBINSIDomain.D4_DEVIATIONS: "Bias due to deviations from intended interventions",
    ROBINSIDomain.D5_MISSING_DATA: "Bias due to missing data",
    ROBINSIDomain.D6_MEASUREMENT: "Bias in measurement of outcomes",
    ROBINSIDomain.D7_REPORTING: "Bias in selection of the reported result",
    ROBINSIDomain.OVERALL: "Overall risk of bias",
}

ROBINSI_DOMAIN_SHORT_NAMES = {
    ROBINSIDomain.D1_CONFOUNDING: "Confounding",
    ROBINSIDomain.D2_SELECTION: "Selection",
    ROBINSIDomain.D3_CLASSIFICATION: "Classification",
    ROBINSIDomain.D4_DEVIATIONS: "Deviations",
    ROBINSIDomain.D5_MISSING_DATA: "Missing data",
    ROBINSIDomain.D6_MEASUREMENT: "Measurement",
    ROBINSIDomain.D7_REPORTING: "Reporting",
    ROBINSIDomain.OVERALL: "Overall",
}


# =============================================================================
# QUADAS-2 Domains (for diagnostic studies)
# =============================================================================


class QUADAS2Domain(str, Enum):
    """QUADAS-2 domains for diagnostic accuracy studies.

    Reference: Whiting PF, et al. Ann Intern Med 2011;155:529-536
    """

    D1_PATIENT_SELECTION = "D1"  # Patient selection
    D2_INDEX_TEST = "D2"  # Index test
    D3_REFERENCE_STANDARD = "D3"  # Reference standard
    D4_FLOW_TIMING = "D4"  # Flow and timing
    OVERALL = "overall"


QUADAS2_DOMAIN_DESCRIPTIONS = {
    QUADAS2Domain.D1_PATIENT_SELECTION: "Risk of bias in patient selection",
    QUADAS2Domain.D2_INDEX_TEST: "Risk of bias in index test",
    QUADAS2Domain.D3_REFERENCE_STANDARD: "Risk of bias in reference standard",
    QUADAS2Domain.D4_FLOW_TIMING: "Risk of bias in flow and timing",
    QUADAS2Domain.OVERALL: "Overall risk of bias",
}

QUADAS2_DOMAIN_SHORT_NAMES = {
    QUADAS2Domain.D1_PATIENT_SELECTION: "Patient selection",
    QUADAS2Domain.D2_INDEX_TEST: "Index test",
    QUADAS2Domain.D3_REFERENCE_STANDARD: "Reference standard",
    QUADAS2Domain.D4_FLOW_TIMING: "Flow and timing",
    QUADAS2Domain.OVERALL: "Overall",
}


# =============================================================================
# Domain Assessment
# =============================================================================


@dataclass
class DomainAssessment:
    """Assessment of a single risk of bias domain."""

    domain: str  # Domain identifier (D1, D2, etc.)
    domain_name: str  # Human-readable domain name
    judgment: RiskLevel  # Risk level judgment
    support: str = ""  # Supporting information/reasoning
    signaling_questions: dict[str, str | bool | int | float] = field(default_factory=dict)
    confidence: float = 1.0  # Confidence in assessment (0-1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "domain_name": self.domain_name,
            "judgment": self.judgment.value,
            "support": self.support,
            "signaling_questions": self.signaling_questions,
            "confidence": self.confidence,
        }


# =============================================================================
# Study Risk of Bias Assessment
# =============================================================================


@dataclass
class StudyRiskOfBias:
    """Complete risk of bias assessment for a single study."""

    study_id: str
    study_name: str
    tool: RoBTool
    domains: list[DomainAssessment]
    overall_judgment: RiskLevel
    overall_support: str = ""
    assessed_at: datetime = field(default_factory=_utc_now)
    assessed_by: str = "RiskOfBiasAssessor"

    @property
    def domain_judgments(self) -> dict[str, RiskLevel]:
        """Get dictionary of domain -> judgment."""
        return {d.domain: d.judgment for d in self.domains}

    @property
    def high_risk_domains(self) -> list[str]:
        """Get list of domains with high risk of bias."""
        return [d.domain_name for d in self.domains if d.judgment == RiskLevel.HIGH]

    @property
    def low_risk_count(self) -> int:
        """Count of low risk domains."""
        return sum(1 for d in self.domains if d.judgment == RiskLevel.LOW)

    @property
    def high_risk_count(self) -> int:
        """Count of high risk domains."""
        return sum(1 for d in self.domains if d.judgment == RiskLevel.HIGH)

    @property
    def some_concerns_count(self) -> int:
        """Count of some concerns domains."""
        return sum(1 for d in self.domains if d.judgment == RiskLevel.SOME_CONCERNS)

    def get_domain(self, domain_id: str) -> DomainAssessment | None:
        """Get assessment for a specific domain."""
        return next((d for d in self.domains if d.domain == domain_id), None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "study_id": self.study_id,
            "study_name": self.study_name,
            "tool": self.tool.value,
            "domains": [d.to_dict() for d in self.domains],
            "overall_judgment": self.overall_judgment.value,
            "overall_support": self.overall_support,
            "assessed_at": self.assessed_at.isoformat(),
            "assessed_by": self.assessed_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StudyRiskOfBias:
        """Create from dictionary."""
        domains = [
            DomainAssessment(
                domain=d["domain"],
                domain_name=d["domain_name"],
                judgment=RiskLevel(d["judgment"]),
                support=d.get("support", ""),
                signaling_questions=d.get("signaling_questions", {}),
                confidence=d.get("confidence", 1.0),
            )
            for d in data.get("domains", [])
        ]

        return cls(
            study_id=data["study_id"],
            study_name=data["study_name"],
            tool=RoBTool(data["tool"]),
            domains=domains,
            overall_judgment=RiskLevel(data["overall_judgment"]),
            overall_support=data.get("overall_support", ""),
            assessed_by=data.get("assessed_by", "RiskOfBiasAssessor"),
        )


# =============================================================================
# Risk of Bias Summary (across all studies)
# =============================================================================


@dataclass
class RiskOfBiasSummary:
    """Summary of risk of bias assessments across all included studies."""

    tool: RoBTool
    studies: list[StudyRiskOfBias]
    outcome_name: str = ""

    @property
    def n_studies(self) -> int:
        """Total number of studies assessed."""
        return len(self.studies)

    @property
    def overall_distribution(self) -> dict[RiskLevel, int]:
        """Distribution of overall judgments."""
        dist: dict[RiskLevel, int] = {level: 0 for level in RiskLevel}
        for study in self.studies:
            dist[study.overall_judgment] += 1
        return dist

    @property
    def domain_distributions(self) -> dict[str, dict[RiskLevel, int]]:
        """Distribution of judgments by domain."""
        if not self.studies:
            return {}

        # Get all domains from first study
        domains = [d.domain for d in self.studies[0].domains]
        distributions: dict[str, dict[RiskLevel, int]] = {}

        for domain in domains:
            distributions[domain] = {level: 0 for level in RiskLevel}
            for study in self.studies:
                assessment = study.get_domain(domain)
                if assessment:
                    distributions[domain][assessment.judgment] += 1

        return distributions

    @property
    def percent_low_risk(self) -> float:
        """Percentage of studies with low overall risk of bias."""
        if not self.studies:
            return 0.0
        low_risk_count = sum(1 for s in self.studies if s.overall_judgment == RiskLevel.LOW)
        return (low_risk_count / len(self.studies)) * 100

    @property
    def percent_high_risk(self) -> float:
        """Percentage of studies with high overall risk of bias."""
        if not self.studies:
            return 0.0
        high_risk_count = sum(1 for s in self.studies if s.overall_judgment == RiskLevel.HIGH)
        return (high_risk_count / len(self.studies)) * 100

    def get_domain_names(self) -> list[str]:
        """Get list of domain names in order."""
        if not self.studies:
            return []

        if self.tool == RoBTool.ROB_2:
            return [
                ROB2_DOMAIN_SHORT_NAMES.get(RoB2Domain(d.domain), d.domain_name)
                for d in self.studies[0].domains
            ]
        elif self.tool == RoBTool.ROBINS_I:
            return [
                ROBINSI_DOMAIN_SHORT_NAMES.get(ROBINSIDomain(d.domain), d.domain_name)
                for d in self.studies[0].domains
            ]
        elif self.tool == RoBTool.QUADAS_2:
            return [
                QUADAS2_DOMAIN_SHORT_NAMES.get(QUADAS2Domain(d.domain), d.domain_name)
                for d in self.studies[0].domains
            ]
        else:
            return [d.domain_name for d in self.studies[0].domains]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool.value,
            "outcome_name": self.outcome_name,
            "n_studies": self.n_studies,
            "percent_low_risk": round(self.percent_low_risk, 1),
            "percent_high_risk": round(self.percent_high_risk, 1),
            "overall_distribution": {k.value: v for k, v in self.overall_distribution.items()},
            "domain_distributions": {
                domain: {k.value: v for k, v in dist.items()}
                for domain, dist in self.domain_distributions.items()
            },
            "studies": [s.to_dict() for s in self.studies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskOfBiasSummary:
        """Create from dictionary."""
        studies = [StudyRiskOfBias.from_dict(s) for s in data.get("studies", [])]
        return cls(
            tool=RoBTool(data["tool"]),
            studies=studies,
            outcome_name=data.get("outcome_name", ""),
        )
