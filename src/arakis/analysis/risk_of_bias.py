"""Risk of Bias assessment module.

Provides automated risk of bias assessment using standardized tools:
- RoB 2 for RCTs
- ROBINS-I for cohort/case-control studies
- QUADAS-2 for diagnostic studies

The assessor analyzes extracted study data to determine risk of bias
based on methodological quality indicators.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Type alias for signaling questions dict
SignalingDict = dict[str, str | bool | int | float]

from arakis.models.extraction import ExtractedData, ExtractionResult
from arakis.models.risk_of_bias import (
    QUADAS2_DOMAIN_SHORT_NAMES,
    ROB2_DOMAIN_SHORT_NAMES,
    ROBINSI_DOMAIN_SHORT_NAMES,
    DomainAssessment,
    QUADAS2Domain,
    RiskLevel,
    RiskOfBiasSummary,
    RoB2Domain,
    ROBINSIDomain,
    RoBTool,
    StudyRiskOfBias,
)
from arakis.models.visualization import Table


@dataclass
class RiskOfBiasConfig:
    """Configuration for risk of bias assessment."""

    # Thresholds for automated assessment
    dropout_threshold_low: float = 10.0  # <=10% dropout = low risk
    dropout_threshold_high: float = 20.0  # >20% dropout = high risk
    loss_to_followup_threshold_low: float = 10.0
    loss_to_followup_threshold_high: float = 20.0

    # Minimum confounders for adequate adjustment
    min_confounders_for_low_risk: int = 3

    # Whether to be conservative (default to higher risk when uncertain)
    conservative: bool = True


class RiskOfBiasAssessor:
    """Automated risk of bias assessor.

    Analyzes extracted study data to assess risk of bias using
    standardized assessment tools (RoB 2, ROBINS-I, QUADAS-2).
    """

    def __init__(self, config: RiskOfBiasConfig | None = None):
        """Initialize assessor.

        Args:
            config: Assessment configuration. Uses defaults if None.
        """
        self.config = config or RiskOfBiasConfig()

    def assess_study(
        self,
        extracted: ExtractedData,
        study_name: str | None = None,
        tool: RoBTool | None = None,
    ) -> StudyRiskOfBias:
        """Assess risk of bias for a single study.

        Args:
            extracted: Extracted data for the study
            study_name: Human-readable study name
            tool: Assessment tool to use (auto-detected if None)

        Returns:
            StudyRiskOfBias assessment
        """
        # Auto-detect tool based on schema
        if tool is None:
            tool = self._detect_tool(extracted.schema_name)

        # Use paper_id as study name if not provided
        if study_name is None:
            study_name = extracted.paper_id

        # Assess based on tool
        if tool == RoBTool.ROB_2:
            return self._assess_rob2(extracted, study_name)
        elif tool == RoBTool.ROBINS_I:
            return self._assess_robins_i(extracted, study_name)
        elif tool == RoBTool.QUADAS_2:
            return self._assess_quadas2(extracted, study_name)
        else:
            raise ValueError(f"Unknown assessment tool: {tool}")

    def assess_studies(
        self,
        extraction_result: ExtractionResult,
        tool: RoBTool | None = None,
        outcome_name: str = "",
    ) -> RiskOfBiasSummary:
        """Assess risk of bias for all studies in extraction result.

        Args:
            extraction_result: Extraction results with all studies
            tool: Assessment tool (auto-detected if None)
            outcome_name: Name of the outcome being assessed

        Returns:
            RiskOfBiasSummary with all assessments
        """
        # Auto-detect tool from schema
        if tool is None:
            tool = self._detect_tool(extraction_result.schema.name)

        # Assess each study
        assessments = []
        for extracted in extraction_result.extractions:
            # Generate study name from extracted data
            study_name = self._generate_study_name(extracted)
            assessment = self.assess_study(extracted, study_name, tool)
            assessments.append(assessment)

        return RiskOfBiasSummary(
            tool=tool,
            studies=assessments,
            outcome_name=outcome_name,
        )

    def _detect_tool(self, schema_name: str) -> RoBTool:
        """Detect appropriate tool based on study schema."""
        schema_lower = schema_name.lower()

        if schema_lower in ["rct", "randomized controlled trial"]:
            return RoBTool.ROB_2
        elif schema_lower in ["diagnostic", "diagnostic accuracy"]:
            return RoBTool.QUADAS_2
        else:
            # Cohort, case-control, and other observational studies
            return RoBTool.ROBINS_I

    def _generate_study_name(self, extracted: ExtractedData) -> str:
        """Generate human-readable study name from extracted data."""
        # Try to extract author/year info if available
        data = extracted.data

        # Common patterns for first author
        first_author = data.get("first_author", "")
        year = data.get("publication_year", data.get("year", ""))

        if first_author and year:
            return f"{first_author} ({year})"
        elif first_author:
            return first_author

        # Fallback to paper_id
        return extracted.paper_id

    # =========================================================================
    # RoB 2 Assessment (for RCTs)
    # =========================================================================

    def _assess_rob2(self, extracted: ExtractedData, study_name: str) -> StudyRiskOfBias:
        """Assess RoB 2 for RCT."""
        data = extracted.data
        domains = []

        # D1: Randomization
        d1 = self._assess_rob2_d1_randomization(data)
        domains.append(d1)

        # D2: Deviations from intended interventions
        d2 = self._assess_rob2_d2_deviations(data)
        domains.append(d2)

        # D3: Missing outcome data
        d3 = self._assess_rob2_d3_missing_data(data)
        domains.append(d3)

        # D4: Measurement of outcome
        d4 = self._assess_rob2_d4_measurement(data)
        domains.append(d4)

        # D5: Selection of reported result
        d5 = self._assess_rob2_d5_selection(data)
        domains.append(d5)

        # Calculate overall judgment using RoB 2 algorithm
        overall_judgment, overall_support = self._calculate_rob2_overall(domains)

        return StudyRiskOfBias(
            study_id=extracted.paper_id,
            study_name=study_name,
            tool=RoBTool.ROB_2,
            domains=domains,
            overall_judgment=overall_judgment,
            overall_support=overall_support,
        )

    def _assess_rob2_d1_randomization(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess D1: Bias arising from randomization process."""
        support_points = []
        signaling: SignalingDict = {}

        # Check randomization method
        randomization = data.get("randomization_method", "").lower()
        allocation = data.get("allocation_concealment", "").lower()

        # Signaling question 1.1: Was the allocation sequence random?
        if any(term in randomization for term in ["computer", "random number", "central"]):
            signaling["1.1_random_sequence"] = True
            support_points.append(f"Randomization: {randomization}")
        elif randomization:
            signaling["1.1_random_sequence"] = "probably_yes"
            support_points.append(f"Randomization method reported: {randomization}")
        else:
            signaling["1.1_random_sequence"] = "no_information"
            support_points.append("Randomization method not reported")

        # Signaling question 1.2: Was allocation concealed?
        if allocation == "adequate":
            signaling["1.2_allocation_concealment"] = True
            support_points.append("Allocation concealment: adequate")
        elif allocation == "inadequate":
            signaling["1.2_allocation_concealment"] = False
            support_points.append("Allocation concealment: inadequate")
        else:
            signaling["1.2_allocation_concealment"] = "no_information"
            support_points.append("Allocation concealment unclear")

        # Determine judgment
        if (
            signaling.get("1.1_random_sequence") is True
            and signaling.get("1.2_allocation_concealment") is True
        ):
            judgment = RiskLevel.LOW
        elif signaling.get("1.2_allocation_concealment") is False:
            judgment = RiskLevel.HIGH
        elif signaling.get("1.1_random_sequence") == "no_information":
            judgment = RiskLevel.SOME_CONCERNS if self.config.conservative else RiskLevel.UNCLEAR
        else:
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=RoB2Domain.D1_RANDOMIZATION.value,
            domain_name=ROB2_DOMAIN_SHORT_NAMES[RoB2Domain.D1_RANDOMIZATION],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_rob2_d2_deviations(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess D2: Bias due to deviations from intended interventions."""
        support_points = []
        signaling: SignalingDict = {}

        blinding = data.get("blinding", [])
        if isinstance(blinding, str):
            blinding = [blinding]

        # Signaling question 2.1: Were participants aware of intervention?
        if "participants" in blinding:
            signaling["2.1_participants_blinded"] = True
            support_points.append("Participants blinded")
        elif "none" in blinding:
            signaling["2.1_participants_blinded"] = False
            support_points.append("Participants not blinded")
        else:
            signaling["2.1_participants_blinded"] = "no_information"

        # Signaling question 2.2: Were care providers aware?
        if "care_providers" in blinding:
            signaling["2.2_care_providers_blinded"] = True
            support_points.append("Care providers blinded")
        elif "none" in blinding:
            signaling["2.2_care_providers_blinded"] = False
            support_points.append("Care providers not blinded")
        else:
            signaling["2.2_care_providers_blinded"] = "no_information"

        # Determine judgment
        if (
            signaling.get("2.1_participants_blinded") is True
            and signaling.get("2.2_care_providers_blinded") is True
        ):
            judgment = RiskLevel.LOW
        elif (
            signaling.get("2.1_participants_blinded") is False
            and signaling.get("2.2_care_providers_blinded") is False
        ):
            judgment = RiskLevel.HIGH
        else:
            judgment = RiskLevel.SOME_CONCERNS

        if not support_points:
            support_points.append("Blinding information not reported")

        return DomainAssessment(
            domain=RoB2Domain.D2_DEVIATIONS.value,
            domain_name=ROB2_DOMAIN_SHORT_NAMES[RoB2Domain.D2_DEVIATIONS],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_rob2_d3_missing_data(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess D3: Bias due to missing outcome data."""
        support_points = []
        signaling: SignalingDict = {}

        dropout_rate = data.get("dropout_rate")
        if dropout_rate is not None:
            try:
                dropout = float(dropout_rate)
                signaling["3.1_dropout_rate"] = dropout
                support_points.append(f"Dropout rate: {dropout:.1f}%")

                if dropout <= self.config.dropout_threshold_low:
                    judgment = RiskLevel.LOW
                elif dropout > self.config.dropout_threshold_high:
                    judgment = RiskLevel.HIGH
                else:
                    judgment = RiskLevel.SOME_CONCERNS
            except (ValueError, TypeError):
                judgment = RiskLevel.UNCLEAR
                support_points.append("Dropout rate not clearly reported")
        else:
            judgment = (
                RiskLevel.UNCLEAR if not self.config.conservative else RiskLevel.SOME_CONCERNS
            )
            support_points.append("Missing data not reported")

        return DomainAssessment(
            domain=RoB2Domain.D3_MISSING_DATA.value,
            domain_name=ROB2_DOMAIN_SHORT_NAMES[RoB2Domain.D3_MISSING_DATA],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_rob2_d4_measurement(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess D4: Bias in measurement of the outcome."""
        support_points = []
        signaling: SignalingDict = {}

        blinding = data.get("blinding", [])
        if isinstance(blinding, str):
            blinding = [blinding]

        # Check if outcome assessors were blinded
        if "outcome_assessors" in blinding:
            signaling["4.1_assessors_blinded"] = True
            support_points.append("Outcome assessors blinded")
            judgment = RiskLevel.LOW
        elif "none" in blinding:
            signaling["4.1_assessors_blinded"] = False
            support_points.append("Outcome assessors not blinded")
            judgment = RiskLevel.HIGH
        else:
            signaling["4.1_assessors_blinded"] = "no_information"
            support_points.append("Outcome assessor blinding not reported")
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=RoB2Domain.D4_MEASUREMENT.value,
            domain_name=ROB2_DOMAIN_SHORT_NAMES[RoB2Domain.D4_MEASUREMENT],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_rob2_d5_selection(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess D5: Bias in selection of the reported result."""
        support_points = []
        signaling: SignalingDict = {}

        # Check for pre-registration or protocol
        # This is often not extractable from papers alone
        # Default to some concerns unless clear evidence

        primary_outcome = data.get("primary_outcome", "")

        if primary_outcome:
            signaling["5.1_primary_outcome_defined"] = True
            support_points.append(f"Primary outcome defined: {primary_outcome[:50]}...")
            judgment = RiskLevel.SOME_CONCERNS  # Can't verify without protocol
        else:
            signaling["5.1_primary_outcome_defined"] = "no_information"
            support_points.append("Primary outcome not clearly defined")
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=RoB2Domain.D5_SELECTION.value,
            domain_name=ROB2_DOMAIN_SHORT_NAMES[RoB2Domain.D5_SELECTION],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _calculate_rob2_overall(self, domains: list[DomainAssessment]) -> tuple[RiskLevel, str]:
        """Calculate overall RoB 2 judgment.

        Algorithm per RoB 2 guidance:
        - Low: All domains low risk
        - Some concerns: Some concerns in at least one domain, no high risk
        - High: High risk in at least one domain
        """
        judgments = [d.judgment for d in domains]

        if RiskLevel.HIGH in judgments:
            high_domains = [d.domain_name for d in domains if d.judgment == RiskLevel.HIGH]
            return (
                RiskLevel.HIGH,
                f"High risk due to: {', '.join(high_domains)}",
            )
        elif RiskLevel.SOME_CONCERNS in judgments or RiskLevel.UNCLEAR in judgments:
            concern_domains = [
                d.domain_name
                for d in domains
                if d.judgment in [RiskLevel.SOME_CONCERNS, RiskLevel.UNCLEAR]
            ]
            return (
                RiskLevel.SOME_CONCERNS,
                f"Some concerns in: {', '.join(concern_domains)}",
            )
        else:
            return (RiskLevel.LOW, "Low risk across all domains")

    # =========================================================================
    # ROBINS-I Assessment (for observational studies)
    # =========================================================================

    def _assess_robins_i(self, extracted: ExtractedData, study_name: str) -> StudyRiskOfBias:
        """Assess ROBINS-I for non-randomized study."""
        data = extracted.data
        domains = []

        # D1: Confounding
        d1 = self._assess_robins_d1_confounding(data)
        domains.append(d1)

        # D2: Selection of participants
        d2 = self._assess_robins_d2_selection(data)
        domains.append(d2)

        # D3: Classification of interventions
        d3 = self._assess_robins_d3_classification(data)
        domains.append(d3)

        # D4: Deviations from intended interventions
        d4 = self._assess_robins_d4_deviations(data)
        domains.append(d4)

        # D5: Missing data
        d5 = self._assess_robins_d5_missing_data(data)
        domains.append(d5)

        # D6: Measurement of outcomes
        d6 = self._assess_robins_d6_measurement(data)
        domains.append(d6)

        # D7: Selection of reported result
        d7 = self._assess_robins_d7_reporting(data)
        domains.append(d7)

        # Calculate overall judgment
        overall_judgment, overall_support = self._calculate_robins_overall(domains)

        return StudyRiskOfBias(
            study_id=extracted.paper_id,
            study_name=study_name,
            tool=RoBTool.ROBINS_I,
            domains=domains,
            overall_judgment=overall_judgment,
            overall_support=overall_support,
        )

    def _assess_robins_d1_confounding(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D1: Bias due to confounding."""
        support_points = []
        signaling: SignalingDict = {}

        confounders = data.get("adjusted_for_confounders", data.get("confounders_adjusted", []))
        if isinstance(confounders, str):
            confounders = [confounders]

        n_confounders = len(confounders) if confounders else 0
        signaling["1.1_confounders_adjusted"] = n_confounders

        if n_confounders >= self.config.min_confounders_for_low_risk:
            judgment = RiskLevel.LOW
            support_points.append(
                f"Adjusted for {n_confounders} confounders: {', '.join(confounders[:5])}"
            )
        elif n_confounders > 0:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append(f"Limited confounder adjustment ({n_confounders} variables)")
        else:
            judgment = RiskLevel.HIGH
            support_points.append("No confounder adjustment reported")

        return DomainAssessment(
            domain=ROBINSIDomain.D1_CONFOUNDING.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D1_CONFOUNDING],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_robins_d2_selection(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D2: Bias in selection of participants."""
        support_points = []

        # Check if selection criteria are clear
        pop_desc = data.get("population_description", "")
        case_def = data.get("case_definition", "")

        if pop_desc or case_def:
            judgment = RiskLevel.SOME_CONCERNS  # Default without detailed info
            support_points.append("Selection criteria reported")
        else:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append("Selection criteria not clearly reported")

        return DomainAssessment(
            domain=ROBINSIDomain.D2_SELECTION.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D2_SELECTION],
            judgment=judgment,
            support="; ".join(support_points) if support_points else "Unable to assess",
        )

    def _assess_robins_d3_classification(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D3: Bias in classification of interventions."""
        support_points = []

        exposure = data.get("exposure", "")
        exposure_assessment = data.get("exposure_assessment", "")

        if exposure_assessment:
            support_points.append(f"Exposure assessment: {exposure_assessment[:100]}")
            judgment = RiskLevel.SOME_CONCERNS
        elif exposure:
            support_points.append(f"Exposure defined: {exposure[:100]}")
            judgment = RiskLevel.SOME_CONCERNS
        else:
            support_points.append("Exposure classification not clearly reported")
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=ROBINSIDomain.D3_CLASSIFICATION.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D3_CLASSIFICATION],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _assess_robins_d4_deviations(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D4: Bias due to deviations from intended interventions."""
        # For observational studies, this is often low risk by design
        return DomainAssessment(
            domain=ROBINSIDomain.D4_DEVIATIONS.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D4_DEVIATIONS],
            judgment=RiskLevel.LOW,
            support="Observational study - deviations less relevant",
        )

    def _assess_robins_d5_missing_data(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D5: Bias due to missing data."""
        support_points = []
        signaling: SignalingDict = {}

        loss_to_followup = data.get("loss_to_followup", data.get("dropout_rate"))

        if loss_to_followup is not None:
            try:
                loss = float(loss_to_followup)
                signaling["5.1_loss_to_followup"] = loss
                support_points.append(f"Loss to follow-up: {loss:.1f}%")

                if loss <= self.config.loss_to_followup_threshold_low:
                    judgment = RiskLevel.LOW
                elif loss > self.config.loss_to_followup_threshold_high:
                    judgment = RiskLevel.HIGH
                else:
                    judgment = RiskLevel.SOME_CONCERNS
            except (ValueError, TypeError):
                judgment = RiskLevel.SOME_CONCERNS
                support_points.append("Loss to follow-up not clearly reported")
        else:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append("Missing data not reported")

        return DomainAssessment(
            domain=ROBINSIDomain.D5_MISSING_DATA.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D5_MISSING_DATA],
            judgment=judgment,
            support="; ".join(support_points),
            signaling_questions=signaling,
        )

    def _assess_robins_d6_measurement(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D6: Bias in measurement of outcomes."""
        support_points = []

        primary_outcome = data.get("primary_outcome", "")

        if primary_outcome:
            support_points.append(f"Outcome: {primary_outcome[:100]}")
            judgment = RiskLevel.SOME_CONCERNS  # Cannot verify measurement validity
        else:
            support_points.append("Outcome measurement not clearly described")
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=ROBINSIDomain.D6_MEASUREMENT.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D6_MEASUREMENT],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _assess_robins_d7_reporting(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess ROBINS-I D7: Bias in selection of reported result."""
        # Similar to RoB 2 D5 - usually cannot verify without protocol
        return DomainAssessment(
            domain=ROBINSIDomain.D7_REPORTING.value,
            domain_name=ROBINSI_DOMAIN_SHORT_NAMES[ROBINSIDomain.D7_REPORTING],
            judgment=RiskLevel.SOME_CONCERNS,
            support="Cannot verify selective reporting without protocol",
        )

    def _calculate_robins_overall(self, domains: list[DomainAssessment]) -> tuple[RiskLevel, str]:
        """Calculate overall ROBINS-I judgment.

        ROBINS-I overall algorithm:
        - Low: Low risk in all domains
        - Moderate: Low/moderate in all domains
        - Serious: Serious in at least one domain
        - Critical: Critical in at least one domain
        """
        judgments = [d.judgment for d in domains]

        if RiskLevel.HIGH in judgments:
            high_domains = [d.domain_name for d in domains if d.judgment == RiskLevel.HIGH]
            return (
                RiskLevel.HIGH,
                f"Serious/critical risk due to: {', '.join(high_domains)}",
            )
        elif RiskLevel.SOME_CONCERNS in judgments or RiskLevel.UNCLEAR in judgments:
            concern_domains = [
                d.domain_name
                for d in domains
                if d.judgment in [RiskLevel.SOME_CONCERNS, RiskLevel.UNCLEAR]
            ]
            return (
                RiskLevel.SOME_CONCERNS,
                f"Moderate risk in: {', '.join(concern_domains)}",
            )
        else:
            return (RiskLevel.LOW, "Low risk across all domains")

    # =========================================================================
    # QUADAS-2 Assessment (for diagnostic studies)
    # =========================================================================

    def _assess_quadas2(self, extracted: ExtractedData, study_name: str) -> StudyRiskOfBias:
        """Assess QUADAS-2 for diagnostic accuracy study."""
        data = extracted.data
        domains = []

        # D1: Patient selection
        d1 = self._assess_quadas_d1_patient_selection(data)
        domains.append(d1)

        # D2: Index test
        d2 = self._assess_quadas_d2_index_test(data)
        domains.append(d2)

        # D3: Reference standard
        d3 = self._assess_quadas_d3_reference_standard(data)
        domains.append(d3)

        # D4: Flow and timing
        d4 = self._assess_quadas_d4_flow_timing(data)
        domains.append(d4)

        # Calculate overall judgment
        overall_judgment, overall_support = self._calculate_quadas_overall(domains)

        return StudyRiskOfBias(
            study_id=extracted.paper_id,
            study_name=study_name,
            tool=RoBTool.QUADAS_2,
            domains=domains,
            overall_judgment=overall_judgment,
            overall_support=overall_support,
        )

    def _assess_quadas_d1_patient_selection(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess QUADAS-2 D1: Patient selection."""
        support_points = []

        study_design = data.get("study_design", "")
        population = data.get("population_description", "")

        if study_design == "case_control":
            judgment = RiskLevel.HIGH
            support_points.append("Case-control design may overestimate accuracy")
        elif population:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append(f"Population: {population[:100]}")
        else:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append("Patient selection not clearly described")

        return DomainAssessment(
            domain=QUADAS2Domain.D1_PATIENT_SELECTION.value,
            domain_name=QUADAS2_DOMAIN_SHORT_NAMES[QUADAS2Domain.D1_PATIENT_SELECTION],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _assess_quadas_d2_index_test(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess QUADAS-2 D2: Index test."""
        support_points = []

        index_test = data.get("index_test", "")
        threshold = data.get("index_test_threshold", "")

        if threshold:
            support_points.append(f"Threshold pre-specified: {threshold}")
            judgment = RiskLevel.LOW
        elif index_test:
            support_points.append(f"Index test: {index_test[:100]}")
            judgment = RiskLevel.SOME_CONCERNS
        else:
            support_points.append("Index test not clearly described")
            judgment = RiskLevel.SOME_CONCERNS

        return DomainAssessment(
            domain=QUADAS2Domain.D2_INDEX_TEST.value,
            domain_name=QUADAS2_DOMAIN_SHORT_NAMES[QUADAS2Domain.D2_INDEX_TEST],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _assess_quadas_d3_reference_standard(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess QUADAS-2 D3: Reference standard."""
        support_points = []

        reference = data.get("reference_standard", "")

        if reference:
            support_points.append(f"Reference standard: {reference[:100]}")
            judgment = RiskLevel.SOME_CONCERNS  # Cannot verify if appropriate
        else:
            support_points.append("Reference standard not described")
            judgment = RiskLevel.HIGH

        return DomainAssessment(
            domain=QUADAS2Domain.D3_REFERENCE_STANDARD.value,
            domain_name=QUADAS2_DOMAIN_SHORT_NAMES[QUADAS2Domain.D3_REFERENCE_STANDARD],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _assess_quadas_d4_flow_timing(self, data: dict[str, Any]) -> DomainAssessment:
        """Assess QUADAS-2 D4: Flow and timing."""
        support_points = []

        sample_size = data.get("sample_size", 0)
        tp = data.get("true_positives", 0)
        fp = data.get("false_positives", 0)
        tn = data.get("true_negatives", 0)
        fn = data.get("false_negatives", 0)

        analyzed = (tp or 0) + (fp or 0) + (tn or 0) + (fn or 0)

        if sample_size and analyzed:
            if analyzed == sample_size:
                judgment = RiskLevel.LOW
                support_points.append("All patients included in analysis")
            else:
                judgment = RiskLevel.SOME_CONCERNS
                support_points.append(f"Analyzed {analyzed} of {sample_size} patients")
        else:
            judgment = RiskLevel.SOME_CONCERNS
            support_points.append("Flow through study not clearly reported")

        return DomainAssessment(
            domain=QUADAS2Domain.D4_FLOW_TIMING.value,
            domain_name=QUADAS2_DOMAIN_SHORT_NAMES[QUADAS2Domain.D4_FLOW_TIMING],
            judgment=judgment,
            support="; ".join(support_points),
        )

    def _calculate_quadas_overall(self, domains: list[DomainAssessment]) -> tuple[RiskLevel, str]:
        """Calculate overall QUADAS-2 judgment."""
        judgments = [d.judgment for d in domains]

        if RiskLevel.HIGH in judgments:
            high_domains = [d.domain_name for d in domains if d.judgment == RiskLevel.HIGH]
            return (
                RiskLevel.HIGH,
                f"High risk due to: {', '.join(high_domains)}",
            )
        elif RiskLevel.SOME_CONCERNS in judgments or RiskLevel.UNCLEAR in judgments:
            concern_domains = [
                d.domain_name
                for d in domains
                if d.judgment in [RiskLevel.SOME_CONCERNS, RiskLevel.UNCLEAR]
            ]
            return (
                RiskLevel.SOME_CONCERNS,
                f"Some concerns in: {', '.join(concern_domains)}",
            )
        else:
            return (RiskLevel.LOW, "Low risk across all domains")


# =============================================================================
# Risk of Bias Table Generator
# =============================================================================


class RiskOfBiasTableGenerator:
    """Generates risk of bias summary tables and visualizations."""

    def generate_table(
        self,
        summary: RiskOfBiasSummary,
        table_id: str = "rob_table",
        use_symbols: bool = True,
    ) -> Table:
        """Generate risk of bias summary table.

        Args:
            summary: Risk of bias summary from assessor
            table_id: Table identifier
            use_symbols: Use traffic light symbols (+, ?, -) instead of text

        Returns:
            Table object for manuscript
        """
        if not summary.studies:
            return Table(
                id=table_id,
                title="Risk of Bias Assessment",
                caption="No studies assessed.",
                headers=["Study"],
                rows=[],
            )

        # Get domain names
        domain_names = summary.get_domain_names()

        # Build headers
        headers = ["Study"] + domain_names + ["Overall"]

        # Build rows
        rows = []
        for study in summary.studies:
            row = [study.study_name]

            # Add domain judgments
            for domain in study.domains:
                if use_symbols:
                    row.append(domain.judgment.symbol)
                else:
                    row.append(domain.judgment.value.replace("_", " ").title())

            # Add overall judgment
            if use_symbols:
                row.append(study.overall_judgment.symbol)
            else:
                row.append(study.overall_judgment.value.replace("_", " ").title())

            rows.append(row)

        # Generate footnotes
        tool_name = self._get_tool_name(summary.tool)
        footnotes = [
            f"Risk of bias assessed using {tool_name}.",
        ]

        if use_symbols:
            footnotes.append("+ = Low risk; ? = Some concerns/Unclear; - = High risk")

        # Add summary statistics
        footnotes.append(
            f"Overall: {summary.percent_low_risk:.0f}% low risk, "
            f"{summary.percent_high_risk:.0f}% high risk"
        )

        return Table(
            id=table_id,
            title=f"Risk of Bias Assessment ({tool_name})",
            caption=self._generate_caption(summary),
            headers=headers,
            rows=rows,
            footnotes=footnotes,
        )

    def generate_traffic_light_table(
        self,
        summary: RiskOfBiasSummary,
        table_id: str = "rob_traffic_light",
    ) -> Table:
        """Generate traffic light style table (for HTML/color output).

        Args:
            summary: Risk of bias summary
            table_id: Table identifier

        Returns:
            Table with color-coded cells
        """
        # This is similar to generate_table but with HTML color styling
        return self.generate_table(summary, table_id, use_symbols=True)

    def _get_tool_name(self, tool: RoBTool) -> str:
        """Get human-readable tool name."""
        names = {
            RoBTool.ROB_2: "Cochrane RoB 2",
            RoBTool.ROBINS_I: "ROBINS-I",
            RoBTool.QUADAS_2: "QUADAS-2",
        }
        return names.get(tool, str(tool))

    def _generate_caption(self, summary: RiskOfBiasSummary) -> str:
        """Generate table caption."""
        tool_name = self._get_tool_name(summary.tool)

        if summary.tool == RoBTool.ROB_2:
            domains_text = (
                "Domains: D1 = randomization process; D2 = deviations from intended "
                "interventions; D3 = missing outcome data; D4 = measurement of outcome; "
                "D5 = selection of reported result."
            )
        elif summary.tool == RoBTool.ROBINS_I:
            domains_text = (
                "Domains: D1 = confounding; D2 = selection; D3 = classification; "
                "D4 = deviations; D5 = missing data; D6 = measurement; D7 = reporting."
            )
        elif summary.tool == RoBTool.QUADAS_2:
            domains_text = (
                "Domains: D1 = patient selection; D2 = index test; "
                "D3 = reference standard; D4 = flow and timing."
            )
        else:
            domains_text = ""

        return (
            f"Risk of bias summary for {summary.n_studies} included studies "
            f"using the {tool_name} tool. {domains_text}"
        )
