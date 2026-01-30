"""Number formatting, precision, and traceability utilities.

Provides centralized configuration for numerical precision and audit trails
to ensure all statistical outputs are accurate and traceable.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NumberCategory(str, Enum):
    """Categories of numbers with different precision requirements."""

    P_VALUE = "p_value"  # Statistical p-values
    EFFECT_SIZE = "effect_size"  # Effect estimates (MD, SMD, OR, RR)
    CONFIDENCE_INTERVAL = "confidence_interval"  # CI bounds
    HETEROGENEITY = "heterogeneity"  # I², tau², Q
    PERCENTAGE = "percentage"  # Percentages (e.g., I², weight)
    COUNT = "count"  # Integer counts
    SAMPLE_SIZE = "sample_size"  # Sample sizes
    TEST_STATISTIC = "test_statistic"  # z, t, chi-square values
    WEIGHT = "weight"  # Study weights in meta-analysis


@dataclass
class PrecisionConfig:
    """Configuration for number formatting precision.

    Centralizes all precision settings to ensure consistent and traceable
    numerical output across the codebase.

    References:
        - Cochrane Handbook 10.12.1 recommends 2 decimal places for SMD
        - APA 7th edition recommends p-values to 3 decimals (< 0.001)
        - CONSORT guidelines for reporting RCTs
    """

    # P-values: 4 decimals, minimum threshold 0.0001
    p_value_decimals: int = 4
    p_value_min_threshold: float = 0.0001

    # Effect sizes: 2-3 decimals depending on scale
    effect_size_decimals: int = 2
    log_effect_decimals: int = 3  # For log(OR), log(RR)

    # Confidence intervals: match effect size precision
    ci_decimals: int = 2
    ci_level_default: float = 0.95

    # Heterogeneity statistics
    i_squared_decimals: int = 1  # Percentage (0.0-100.0)
    tau_squared_decimals: int = 4  # Small variance values
    q_statistic_decimals: int = 2

    # Test statistics
    z_statistic_decimals: int = 2
    chi_squared_decimals: int = 2

    # Weights: 1 decimal for percentages
    weight_decimals: int = 1

    # Statistical constants with references
    # Reference: Rosner, B. (2015). Fundamentals of Biostatistics, 8th ed.
    Z_CRITICAL_95: float = 1.96  # For 95% CI (exact: 1.959964)
    Z_CRITICAL_90: float = 1.645  # For 90% CI
    Z_CRITICAL_99: float = 2.576  # For 99% CI

    # Heterogeneity interpretation thresholds
    # Reference: Higgins JPT, Thompson SG. BMJ 2002;327:557-560
    I_SQUARED_LOW: float = 25.0
    I_SQUARED_MODERATE: float = 50.0
    I_SQUARED_HIGH: float = 75.0

    # Effect size interpretation (Cohen's d)
    # Reference: Cohen, J. (1988). Statistical Power Analysis
    COHENS_D_SMALL: float = 0.2
    COHENS_D_MEDIUM: float = 0.5
    COHENS_D_LARGE: float = 0.8

    # Continuity correction for zero cells in 2x2 tables
    # Reference: Sweeting MJ, et al. Stat Med 2004;23:1351-1375
    CONTINUITY_CORRECTION: float = 0.5

    def format_p_value(self, value: float) -> str:
        """Format a p-value with appropriate precision.

        Args:
            value: The p-value to format

        Returns:
            Formatted string (e.g., "0.0234" or "< 0.0001")
        """
        if value < self.p_value_min_threshold:
            return f"< {self.p_value_min_threshold}"
        return f"{value:.{self.p_value_decimals}f}"

    def format_effect(self, value: float, is_log_scale: bool = False) -> str:
        """Format an effect size with appropriate precision.

        Args:
            value: The effect size value
            is_log_scale: Whether this is a log-transformed effect

        Returns:
            Formatted string
        """
        decimals = self.log_effect_decimals if is_log_scale else self.effect_size_decimals
        return f"{value:.{decimals}f}"

    def format_ci(self, lower: float, upper: float) -> str:
        """Format a confidence interval.

        Args:
            lower: Lower bound
            upper: Upper bound

        Returns:
            Formatted string (e.g., "[1.23, 4.56]")
        """
        return f"[{lower:.{self.ci_decimals}f}, {upper:.{self.ci_decimals}f}]"

    def format_i_squared(self, value: float) -> str:
        """Format I² statistic.

        Args:
            value: I² value (0-100)

        Returns:
            Formatted string with percent sign
        """
        return f"{value:.{self.i_squared_decimals}f}%"

    def format_weight(self, value: float) -> str:
        """Format study weight as percentage.

        Args:
            value: Weight value (0-1 scale)

        Returns:
            Formatted string with percent sign
        """
        return f"{value * 100:.{self.weight_decimals}f}%"

    def interpret_i_squared(self, value: float) -> str:
        """Interpret I² value according to Cochrane guidelines.

        Args:
            value: I² value (0-100)

        Returns:
            Interpretation string

        Reference:
            Higgins JPT, Thompson SG, Deeks JJ, Altman DG. BMJ 2003;327:557-560
        """
        if value < self.I_SQUARED_LOW:
            return "low heterogeneity"
        elif value < self.I_SQUARED_MODERATE:
            return "moderate heterogeneity"
        elif value < self.I_SQUARED_HIGH:
            return "substantial heterogeneity"
        else:
            return "considerable heterogeneity"

    def interpret_cohens_d(self, value: float) -> str:
        """Interpret Cohen's d effect size.

        Args:
            value: Absolute Cohen's d value

        Returns:
            Interpretation string

        Reference:
            Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences
        """
        abs_d = abs(value)
        if abs_d < self.COHENS_D_SMALL:
            return "negligible"
        elif abs_d < self.COHENS_D_MEDIUM:
            return "small"
        elif abs_d < self.COHENS_D_LARGE:
            return "medium"
        else:
            return "large"


# Global default precision configuration
DEFAULT_PRECISION = PrecisionConfig()


@dataclass
class CalculationStep:
    """A single step in a calculation with traceability information."""

    step_name: str
    description: str
    formula: str  # LaTeX-style formula
    inputs: dict[str, Any]
    output: Any
    output_name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_name": self.step_name,
            "description": self.description,
            "formula": self.formula,
            "inputs": self.inputs,
            "output": self.output,
            "output_name": self.output_name,
            "timestamp": self.timestamp,
        }


@dataclass
class AuditTrail:
    """Audit trail for statistical calculations.

    Provides full traceability of how each number was calculated,
    including formulas, inputs, and intermediate steps.
    """

    calculation_id: str
    calculation_type: str  # e.g., "meta_analysis", "heterogeneity", "effect_size"
    method_name: str  # e.g., "DerSimonian-Laird", "inverse_variance"
    method_reference: str = ""  # Academic reference for the method
    software_version: str = "arakis"
    confidence_level: float = 0.95
    steps: list[CalculationStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_step(
        self,
        step_name: str,
        description: str,
        formula: str,
        inputs: dict[str, Any],
        output: Any,
        output_name: str,
    ) -> None:
        """Add a calculation step to the audit trail.

        Args:
            step_name: Short name for the step
            description: Human-readable description
            formula: Mathematical formula (LaTeX-style)
            inputs: Input values used
            output: Result of the calculation
            output_name: Name of the output variable
        """
        self.steps.append(
            CalculationStep(
                step_name=step_name,
                description=description,
                formula=formula,
                inputs=inputs,
                output=output,
                output_name=output_name,
            )
        )

    def add_warning(self, warning: str) -> None:
        """Add a warning to the audit trail.

        Args:
            warning: Warning message
        """
        self.warnings.append(warning)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "calculation_id": self.calculation_id,
            "calculation_type": self.calculation_type,
            "method_name": self.method_name,
            "method_reference": self.method_reference,
            "software_version": self.software_version,
            "confidence_level": self.confidence_level,
            "steps": [step.to_dict() for step in self.steps],
            "warnings": self.warnings,
            "created_at": self.created_at,
        }

    def get_final_outputs(self) -> dict[str, Any]:
        """Get all final output values from the calculation.

        Returns:
            Dictionary of output_name -> output_value
        """
        return {step.output_name: step.output for step in self.steps}

    def __str__(self) -> str:
        """Generate human-readable summary of the audit trail."""
        lines = [
            f"Audit Trail: {self.calculation_type}",
            f"Method: {self.method_name}",
            f"Reference: {self.method_reference}" if self.method_reference else "",
            f"Confidence Level: {self.confidence_level * 100:.0f}%",
            "",
            "Steps:",
        ]

        for i, step in enumerate(self.steps, 1):
            lines.append(f"  {i}. {step.step_name}: {step.description}")
            lines.append(f"     Formula: {step.formula}")
            lines.append(f"     Result: {step.output_name} = {step.output}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(line for line in lines if line or line == "")


@dataclass
class TracedValue:
    """A value with its source and calculation traced.

    Use this for any number that needs to be traceable in outputs.
    """

    value: Any
    source: str  # Where this value came from (e.g., "user_input", "calculated")
    formula: str = ""  # How it was calculated (if applicable)
    inputs: dict[str, Any] = field(default_factory=dict)
    precision: int = 4  # Decimal places for display
    unit: str = ""  # e.g., "kg", "%", "days"

    def format(self, precision: int | None = None) -> str:
        """Format the value with appropriate precision.

        Args:
            precision: Override default precision

        Returns:
            Formatted string
        """
        p = precision if precision is not None else self.precision
        if isinstance(self.value, float):
            formatted = f"{self.value:.{p}f}"
        else:
            formatted = str(self.value)

        if self.unit:
            formatted += f" {self.unit}"

        return formatted

    def __repr__(self) -> str:
        return f"TracedValue({self.format()}, source='{self.source}')"


def validate_prisma_flow(
    records_identified: int,
    duplicates_removed: int,
    records_screened: int,
    records_excluded: int,
    reports_sought: int,
    reports_not_retrieved: int,
    reports_assessed: int,
    reports_excluded: int,
    studies_included: int,
) -> list[str]:
    """Validate PRISMA flow numbers for internal consistency.

    Checks that the numbers at each stage are mathematically consistent.

    Args:
        records_identified: Total records from all sources
        duplicates_removed: Records removed as duplicates
        records_screened: Records screened at title/abstract stage
        records_excluded: Records excluded at title/abstract stage
        reports_sought: Full-text reports sought for retrieval
        reports_not_retrieved: Reports that could not be retrieved
        reports_assessed: Reports assessed for eligibility
        reports_excluded: Reports excluded at full-text stage
        studies_included: Final studies included

    Returns:
        List of validation errors (empty if all checks pass)
    """
    errors = []

    # Check 1: Records after deduplication should equal records screened
    records_after_dedup = records_identified - duplicates_removed
    if records_after_dedup != records_screened and records_screened > 0:
        # Allow for automated removals
        if records_after_dedup < records_screened:
            errors.append(
                f"Records screened ({records_screened}) exceeds records after "
                f"deduplication ({records_after_dedup})"
            )

    # Check 2: Records excluded should not exceed records screened
    if records_excluded > records_screened:
        errors.append(
            f"Records excluded ({records_excluded}) exceeds records screened ({records_screened})"
        )

    # Check 3: Reports sought should equal screened minus excluded
    expected_reports_sought = records_screened - records_excluded
    if reports_sought > 0 and reports_sought > expected_reports_sought:
        errors.append(
            f"Reports sought ({reports_sought}) exceeds records passing "
            f"screening ({expected_reports_sought})"
        )

    # Check 4: Reports assessed should equal sought minus not retrieved
    expected_assessed = reports_sought - reports_not_retrieved
    if reports_assessed > 0 and reports_assessed > expected_assessed:
        errors.append(
            f"Reports assessed ({reports_assessed}) exceeds retrieved reports ({expected_assessed})"
        )

    # Check 5: Reports excluded should not exceed reports assessed
    if reports_excluded > reports_assessed and reports_assessed > 0:
        errors.append(
            f"Reports excluded ({reports_excluded}) exceeds reports assessed ({reports_assessed})"
        )

    # Check 6: Studies included should equal assessed minus excluded
    expected_included = reports_assessed - reports_excluded
    if studies_included > 0 and expected_included >= 0:
        if studies_included > expected_included:
            errors.append(
                f"Studies included ({studies_included}) exceeds reports "
                f"passing full-text review ({expected_included})"
            )

    # Check 7: No negative values
    all_values = [
        ("records_identified", records_identified),
        ("duplicates_removed", duplicates_removed),
        ("records_screened", records_screened),
        ("records_excluded", records_excluded),
        ("reports_sought", reports_sought),
        ("reports_not_retrieved", reports_not_retrieved),
        ("reports_assessed", reports_assessed),
        ("reports_excluded", reports_excluded),
        ("studies_included", studies_included),
    ]
    for name, value in all_values:
        if value < 0:
            errors.append(f"{name} cannot be negative (got {value})")

    return errors


def validate_sample_sizes(
    studies: list[dict[str, Any]],
    total_sample_size: int,
) -> list[str]:
    """Validate that total sample size matches sum of individual studies.

    Args:
        studies: List of study data dictionaries with sample size info
        total_sample_size: Reported total sample size

    Returns:
        List of validation errors (empty if all checks pass)
    """
    errors = []

    # Calculate sum from individual studies
    calculated_total = 0
    for study in studies:
        # Try intervention_n + control_n first
        if study.get("intervention_n") and study.get("control_n"):
            calculated_total += study["intervention_n"] + study["control_n"]
        elif study.get("sample_size"):
            calculated_total += study["sample_size"]

    if calculated_total > 0 and total_sample_size > 0:
        if calculated_total != total_sample_size:
            errors.append(
                f"Total sample size ({total_sample_size}) does not match sum "
                f"of individual studies ({calculated_total})"
            )

    return errors


def validate_weights_sum(weights: list[float], tolerance: float = 0.01) -> list[str]:
    """Validate that study weights sum to 1.0 (100%).

    Args:
        weights: List of study weights (should sum to 1.0)
        tolerance: Acceptable deviation from 1.0

    Returns:
        List of validation errors (empty if all checks pass)
    """
    errors = []

    if weights:
        total = sum(weights)
        if abs(total - 1.0) > tolerance:
            errors.append(
                f"Study weights sum to {total:.4f} instead of 1.0 (tolerance: {tolerance})"
            )

    return errors
