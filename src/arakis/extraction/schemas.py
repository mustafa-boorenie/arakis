"""Pre-built extraction schemas for common study types.

This module provides ready-to-use schemas for extracting data from:
- Randomized Controlled Trials (RCTs)
- Cohort Studies
- Case-Control Studies
- Diagnostic Accuracy Studies
- Meta-Analyses
"""

from arakis.models.extraction import ExtractionField, ExtractionSchema, FieldType

# ============================================================================
# Randomized Controlled Trial (RCT) Schema
# ============================================================================

RCT_SCHEMA = ExtractionSchema(
    name="rct",
    description="Standard extraction schema for Randomized Controlled Trials (RCTs)",
    study_types=["Randomized Controlled Trial", "RCT", "Clinical Trial"],
    version="1.0",
    fields=[
        # Study identification
        ExtractionField(
            name="study_design",
            description="Type of study design (e.g., parallel RCT, crossover RCT, cluster RCT)",
            field_type=FieldType.CATEGORICAL,
            required=True,
            validation_rules={
                "allowed_values": ["parallel", "crossover", "cluster", "factorial", "other"]
            },
        ),
        # Population
        ExtractionField(
            name="sample_size_total",
            description="Total number of participants randomized",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="sample_size_intervention",
            description="Number of participants in intervention group",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="sample_size_control",
            description="Number of participants in control group",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="mean_age",
            description="Mean age of participants in years",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 120},
        ),
        ExtractionField(
            name="percent_female",
            description="Percentage of female participants",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        ExtractionField(
            name="population_description",
            description="Brief description of the study population and inclusion criteria",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 500},
        ),
        # Intervention
        ExtractionField(
            name="intervention_name",
            description="Name of the intervention being tested",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 200},
        ),
        ExtractionField(
            name="intervention_dose",
            description="Dose, frequency, and duration of intervention",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 200},
        ),
        ExtractionField(
            name="control_type",
            description="Type of control (placebo, active comparator, usual care, etc.)",
            field_type=FieldType.CATEGORICAL,
            required=True,
            validation_rules={
                "allowed_values": [
                    "placebo",
                    "active_comparator",
                    "usual_care",
                    "no_treatment",
                    "other",
                ]
            },
        ),
        ExtractionField(
            name="control_description",
            description="Description of what the control group received",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 200},
        ),
        # Study quality
        ExtractionField(
            name="randomization_method",
            description="Method used for randomization",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 200},
        ),
        ExtractionField(
            name="allocation_concealment",
            description="Was allocation concealment adequate?",
            field_type=FieldType.CATEGORICAL,
            required=False,
            validation_rules={"allowed_values": ["adequate", "inadequate", "unclear"]},
        ),
        ExtractionField(
            name="blinding",
            description="Who was blinded? (participants, care providers, outcome assessors)",
            field_type=FieldType.LIST,
            required=False,
            validation_rules={
                "allowed_values": ["participants", "care_providers", "outcome_assessors", "none"]
            },
        ),
        ExtractionField(
            name="dropout_rate",
            description="Overall dropout/loss to follow-up rate as percentage",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        # Outcomes
        ExtractionField(
            name="primary_outcome",
            description="Primary outcome measure",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="primary_outcome_intervention_n",
            description="Number of events (or mean value) for primary outcome in intervention group",
            field_type=FieldType.TEXT,  # Can be count or continuous
            required=False,
        ),
        ExtractionField(
            name="primary_outcome_control_n",
            description="Number of events (or mean value) for primary outcome in control group",
            field_type=FieldType.TEXT,
            required=False,
        ),
        ExtractionField(
            name="primary_outcome_result",
            description="Primary outcome result (effect size, p-value, confidence interval)",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="secondary_outcomes",
            description="List of secondary outcomes measured",
            field_type=FieldType.LIST,
            required=False,
        ),
        ExtractionField(
            name="adverse_events",
            description="Description of adverse events reported",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 500},
        ),
        # Follow-up
        ExtractionField(
            name="follow_up_duration",
            description="Duration of follow-up (e.g., '12 weeks', '6 months', '1 year')",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 100},
        ),
        # Funding
        ExtractionField(
            name="funding_source",
            description="Source of funding (industry, government, non-profit, unclear)",
            field_type=FieldType.CATEGORICAL,
            required=False,
            validation_rules={
                "allowed_values": [
                    "industry",
                    "government",
                    "non_profit",
                    "mixed",
                    "unclear",
                    "none",
                ]
            },
        ),
    ],
)


# ============================================================================
# Cohort Study Schema
# ============================================================================

COHORT_SCHEMA = ExtractionSchema(
    name="cohort",
    description="Standard extraction schema for Cohort Studies",
    study_types=["Cohort Study", "Prospective Cohort", "Retrospective Cohort"],
    version="1.0",
    fields=[
        # Study design
        ExtractionField(
            name="cohort_type",
            description="Type of cohort study",
            field_type=FieldType.CATEGORICAL,
            required=True,
            validation_rules={
                "allowed_values": ["prospective", "retrospective", "ambidirectional"]
            },
        ),
        # Population
        ExtractionField(
            name="sample_size_total",
            description="Total number of participants at baseline",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="sample_size_exposed",
            description="Number of participants in exposed group",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="sample_size_unexposed",
            description="Number of participants in unexposed/control group",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="mean_age",
            description="Mean age of participants in years",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 120},
        ),
        ExtractionField(
            name="percent_female",
            description="Percentage of female participants",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        ExtractionField(
            name="population_description",
            description="Description of the cohort population",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 500},
        ),
        # Exposure
        ExtractionField(
            name="exposure",
            description="Exposure or risk factor being studied",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="exposure_assessment",
            description="How exposure was measured or defined",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 300},
        ),
        # Follow-up
        ExtractionField(
            name="follow_up_duration",
            description="Mean or median follow-up duration",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 100},
        ),
        ExtractionField(
            name="loss_to_followup",
            description="Percentage lost to follow-up",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        # Outcomes
        ExtractionField(
            name="primary_outcome",
            description="Primary outcome measure",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="outcome_exposed",
            description="Number of events in exposed group",
            field_type=FieldType.NUMERIC,
            required=False,
        ),
        ExtractionField(
            name="outcome_unexposed",
            description="Number of events in unexposed group",
            field_type=FieldType.NUMERIC,
            required=False,
        ),
        ExtractionField(
            name="effect_measure",
            description="Effect measure reported (hazard ratio, relative risk, etc.) with CI",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="adjusted_for_confounders",
            description="List of confounders adjusted for in analysis",
            field_type=FieldType.LIST,
            required=False,
        ),
    ],
)


# ============================================================================
# Case-Control Study Schema
# ============================================================================

CASE_CONTROL_SCHEMA = ExtractionSchema(
    name="case_control",
    description="Standard extraction schema for Case-Control Studies",
    study_types=["Case-Control Study"],
    version="1.0",
    fields=[
        # Population
        ExtractionField(
            name="number_of_cases",
            description="Total number of cases",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="number_of_controls",
            description="Total number of controls",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="case_definition",
            description="How cases were defined and identified",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="control_selection",
            description="How controls were selected and matched",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="matching_criteria",
            description="Variables used for matching (age, sex, etc.)",
            field_type=FieldType.LIST,
            required=False,
        ),
        # Exposure
        ExtractionField(
            name="exposure",
            description="Exposure or risk factor being studied",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="exposure_assessment",
            description="How exposure was measured (recall, records, etc.)",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="exposed_cases",
            description="Number of exposed cases",
            field_type=FieldType.NUMERIC,
            required=False,
        ),
        ExtractionField(
            name="exposed_controls",
            description="Number of exposed controls",
            field_type=FieldType.NUMERIC,
            required=False,
        ),
        # Results
        ExtractionField(
            name="odds_ratio",
            description="Odds ratio with confidence interval",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 200},
        ),
        ExtractionField(
            name="adjusted_or",
            description="Adjusted odds ratio (if multivariate analysis performed)",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 200},
        ),
        ExtractionField(
            name="confounders_adjusted",
            description="List of confounders adjusted for",
            field_type=FieldType.LIST,
            required=False,
        ),
    ],
)


# ============================================================================
# Diagnostic Accuracy Study Schema
# ============================================================================

DIAGNOSTIC_SCHEMA = ExtractionSchema(
    name="diagnostic",
    description="Standard extraction schema for Diagnostic Accuracy Studies",
    study_types=["Diagnostic Study", "Test Accuracy Study"],
    version="1.0",
    fields=[
        # Study design
        ExtractionField(
            name="study_design",
            description="Study design (cross-sectional, cohort, case-control)",
            field_type=FieldType.CATEGORICAL,
            required=True,
            validation_rules={
                "allowed_values": ["cross_sectional", "cohort", "case_control", "other"]
            },
        ),
        # Population
        ExtractionField(
            name="sample_size",
            description="Total number of participants",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1},
        ),
        ExtractionField(
            name="population_description",
            description="Description of study population",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 500},
        ),
        ExtractionField(
            name="disease_prevalence",
            description="Prevalence of target condition in study population (%)",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        # Index test
        ExtractionField(
            name="index_test",
            description="Index test being evaluated",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        ExtractionField(
            name="index_test_threshold",
            description="Threshold or cutoff used for positive result",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 200},
        ),
        # Reference standard
        ExtractionField(
            name="reference_standard",
            description="Reference standard (gold standard) test",
            field_type=FieldType.TEXT,
            required=True,
            validation_rules={"max_length": 300},
        ),
        # Results (2x2 table)
        ExtractionField(
            name="true_positives",
            description="Number of true positives",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0},
        ),
        ExtractionField(
            name="false_positives",
            description="Number of false positives",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0},
        ),
        ExtractionField(
            name="true_negatives",
            description="Number of true negatives",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0},
        ),
        ExtractionField(
            name="false_negatives",
            description="Number of false negatives",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0},
        ),
        # Calculated metrics
        ExtractionField(
            name="sensitivity",
            description="Sensitivity (%) with confidence interval",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 100},
        ),
        ExtractionField(
            name="specificity",
            description="Specificity (%) with confidence interval",
            field_type=FieldType.TEXT,
            required=False,
            validation_rules={"max_length": 100},
        ),
        ExtractionField(
            name="ppv",
            description="Positive predictive value (%)",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
        ExtractionField(
            name="npv",
            description="Negative predictive value (%)",
            field_type=FieldType.NUMERIC,
            required=False,
            validation_rules={"min": 0, "max": 100},
        ),
    ],
)


# ============================================================================
# Schema Registry
# ============================================================================

AVAILABLE_SCHEMAS = {
    "rct": RCT_SCHEMA,
    "cohort": COHORT_SCHEMA,
    "case_control": CASE_CONTROL_SCHEMA,
    "diagnostic": DIAGNOSTIC_SCHEMA,
}


def get_schema(name: str) -> ExtractionSchema:
    """
    Get a pre-built schema by name.

    Args:
        name: Schema name (rct, cohort, case_control, diagnostic)

    Returns:
        ExtractionSchema

    Raises:
        ValueError: If schema name is not recognized
    """
    if name not in AVAILABLE_SCHEMAS:
        available = ", ".join(AVAILABLE_SCHEMAS.keys())
        raise ValueError(f"Unknown schema '{name}'. Available schemas: {available}")

    return AVAILABLE_SCHEMAS[name]


def list_schemas() -> dict[str, str]:
    """
    List all available pre-built schemas.

    Returns:
        Dict mapping schema name to description
    """
    return {name: schema.description for name, schema in AVAILABLE_SCHEMAS.items()}
