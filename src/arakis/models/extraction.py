"""Data models for data extraction from papers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)
from typing import Any


class FieldType(str, Enum):
    """Type of data to extract for a field."""

    NUMERIC = "numeric"  # Numbers (sample size, age, etc.)
    CATEGORICAL = "categorical"  # Categories (gender, intervention type, etc.)
    TEXT = "text"  # Free text (descriptions, conclusions, etc.)
    DATE = "date"  # Dates (publication date, study period, etc.)
    BOOLEAN = "boolean"  # Yes/No, True/False
    LIST = "list"  # List of items (outcomes, medications, etc.)


class ExtractionMethod(str, Enum):
    """Method used for extraction."""

    TRIPLE_REVIEW = "triple-review"  # 3 AI reviewers with majority voting
    SINGLE_PASS = "single-pass"  # 1 AI reviewer (fast mode)
    HUMAN = "human"  # Manual human extraction
    HYBRID = "hybrid"  # AI + human verification


@dataclass
class ExtractionField:
    """Definition of a single field to extract from papers.

    This defines what to extract, how to extract it, and validation rules.
    """

    name: str  # Field identifier (e.g., "sample_size", "primary_outcome")
    description: str  # Clear definition for LLM and human reviewers
    field_type: FieldType  # Type of data expected
    required: bool = False  # Must be present in every paper
    validation_rules: dict[str, Any] = field(default_factory=dict)  # Validation constraints

    # Validation rule examples:
    # - For NUMERIC: {"min": 0, "max": 10000}
    # - For CATEGORICAL: {"allowed_values": ["RCT", "cohort", "case-control"]}
    # - For TEXT: {"max_length": 500}
    # - For LIST: {"min_items": 1, "max_items": 10}

    def __post_init__(self):
        """Validate field definition."""
        if not self.name:
            raise ValueError("Field name cannot be empty")
        if not self.description:
            raise ValueError(f"Field {self.name} must have a description")

    def validate(self, value: Any) -> tuple[bool, str | None]:
        """Validate a value against this field's rules.

        Args:
            value: The value to validate

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        # Check if required field is missing
        if self.required and value is None:
            return False, f"Field '{self.name}' is required but no value provided"

        # Optional field can be None
        if not self.required and value is None:
            return True, None

        # Type-specific validation
        if self.field_type == FieldType.NUMERIC:
            return self._validate_numeric(value)
        elif self.field_type == FieldType.CATEGORICAL:
            return self._validate_categorical(value)
        elif self.field_type == FieldType.TEXT:
            return self._validate_text(value)
        elif self.field_type == FieldType.LIST:
            return self._validate_list(value)
        elif self.field_type == FieldType.BOOLEAN:
            return self._validate_boolean(value)
        elif self.field_type == FieldType.DATE:
            return self._validate_date(value)

        # No validation rules for this type
        return True, None

    def _validate_numeric(self, value: Any) -> tuple[bool, str | None]:
        """Validate numeric value."""
        if not isinstance(value, (int, float)):
            return False, f"Field '{self.name}' must be a number"

        rules = self.validation_rules
        if "min" in rules and value < rules["min"]:
            return False, f"Field '{self.name}' value {value} is below minimum {rules['min']}"
        if "max" in rules and value > rules["max"]:
            return False, f"Field '{self.name}' value {value} exceeds maximum {rules['max']}"

        return True, None

    def _validate_categorical(self, value: Any) -> tuple[bool, str | None]:
        """Validate categorical value."""
        if not isinstance(value, str):
            return False, f"Field '{self.name}' must be a string"

        rules = self.validation_rules
        if "allowed_values" in rules:
            allowed = rules["allowed_values"]
            if value not in allowed:
                return False, f"Field '{self.name}' must be one of {allowed}, got '{value}'"

        return True, None

    def _validate_text(self, value: Any) -> tuple[bool, str | None]:
        """Validate text value."""
        if not isinstance(value, str):
            return False, f"Field '{self.name}' must be text"

        rules = self.validation_rules
        if "max_length" in rules and len(value) > rules["max_length"]:
            return False, f"Field '{self.name}' exceeds maximum length {rules['max_length']}"
        if "min_length" in rules and len(value) < rules["min_length"]:
            return False, f"Field '{self.name}' below minimum length {rules['min_length']}"

        return True, None

    def _validate_list(self, value: Any) -> tuple[bool, str | None]:
        """Validate list value."""
        if not isinstance(value, list):
            return False, f"Field '{self.name}' must be a list"

        rules = self.validation_rules
        if "min_items" in rules and len(value) < rules["min_items"]:
            return False, f"Field '{self.name}' has fewer than {rules['min_items']} items"
        if "max_items" in rules and len(value) > rules["max_items"]:
            return False, f"Field '{self.name}' has more than {rules['max_items']} items"

        return True, None

    def _validate_boolean(self, value: Any) -> tuple[bool, str | None]:
        """Validate boolean value."""
        if not isinstance(value, bool):
            return False, f"Field '{self.name}' must be a boolean"
        return True, None

    def _validate_date(self, value: Any) -> tuple[bool, str | None]:
        """Validate date value."""
        # Accept string dates for now
        if not isinstance(value, (str, datetime)):
            return False, f"Field '{self.name}' must be a date"
        return True, None


@dataclass
class ExtractionSchema:
    """Complete schema defining all fields to extract.

    A schema is a template for extracting structured data from papers.
    Pre-built schemas exist for common study types (RCT, cohort, etc.).
    """

    name: str  # Schema identifier (e.g., "RCT Standard", "Cohort Study")
    description: str  # What this schema is for
    fields: list[ExtractionField]  # All fields to extract
    study_types: list[str] = field(default_factory=list)  # Applicable study designs
    version: str = "1.0"  # Schema version for compatibility

    @property
    def required_fields(self) -> list[ExtractionField]:
        """Get all required fields."""
        return [f for f in self.fields if f.required]

    @property
    def optional_fields(self) -> list[ExtractionField]:
        """Get all optional fields."""
        return [f for f in self.fields if not f.required]

    def get_field(self, name: str) -> ExtractionField | None:
        """Get field by name."""
        return next((f for f in self.fields if f.name == name), None)

    def validate(self) -> list[str]:
        """Validate schema definition. Returns list of errors."""
        errors = []

        if not self.name:
            errors.append("Schema name cannot be empty")

        if not self.fields:
            errors.append("Schema must have at least one field")

        # Check for duplicate field names
        field_names = [f.name for f in self.fields]
        duplicates = [name for name in field_names if field_names.count(name) > 1]
        if duplicates:
            errors.append(f"Duplicate field names: {set(duplicates)}")

        return errors


@dataclass
class ReviewerDecision:
    """A single reviewer's extraction decision for one field."""

    field_name: str
    value: Any  # Extracted value
    confidence: float  # 0-1, how confident is this extraction
    reasoning: str = ""  # Why this value was extracted
    reviewer_id: str = ""  # Which reviewer/pass (reviewer1, reviewer2, reviewer3)


@dataclass
class ExtractedData:
    """Data extracted from a single paper.

    Contains the extracted values, confidence scores, and audit trail
    for quality assurance and conflict resolution.
    """

    paper_id: str
    schema_name: str  # Which schema was used
    extraction_method: ExtractionMethod

    # Final extracted data (after conflict resolution)
    data: dict[str, Any] = field(default_factory=dict)  # field_name → value
    confidence: dict[str, float] = field(default_factory=dict)  # field_name → confidence (0-1)

    # Audit trail for quality assurance
    reviewer_decisions: list[ReviewerDecision] = field(
        default_factory=list
    )  # All reviewer decisions
    conflicts: list[str] = field(default_factory=list)  # Fields with reviewer disagreement
    low_confidence_fields: list[str] = field(
        default_factory=list
    )  # Fields below confidence threshold

    # Metadata
    extraction_quality: float = 1.0  # Overall quality score (0-1)
    extracted_at: datetime = field(default_factory=_utc_now)
    extracted_by: str = "DataExtractionAgent"  # Agent or human identifier
    extraction_time_ms: int = 0  # Time taken to extract

    # Flags for review
    needs_human_review: bool = False  # Should a human verify this?
    human_reviewed: bool = False  # Has a human reviewed this?
    human_override: dict[str, Any] = field(default_factory=dict)  # Human corrections

    # Thresholds for quality control
    LOW_CONFIDENCE_THRESHOLD: float = field(default=0.8, init=False, repr=False)
    LOW_QUALITY_THRESHOLD: float = field(default=0.7, init=False, repr=False)

    def __post_init__(self):
        """Automatically determine quality flags after initialization."""
        # Populate low_confidence_fields based on confidence scores
        self.low_confidence_fields = [
            field_name
            for field_name, confidence_score in self.confidence.items()
            if confidence_score < self.LOW_CONFIDENCE_THRESHOLD
        ]

        # Automatically flag for human review if quality issues detected
        if not self.needs_human_review:  # Don't override if already set
            self.needs_human_review = (
                len(self.conflicts) > 0  # Has conflicts
                or len(self.low_confidence_fields) > 0  # Has low confidence fields
                or self.extraction_quality < self.LOW_QUALITY_THRESHOLD  # Low overall quality
            )

    @property
    def completion_rate(self) -> float:
        """Percentage of required fields successfully extracted."""
        if not self.data:
            return 0.0
        # This would need schema reference to calculate properly
        return float(len(self.data))

    @property
    def average_confidence(self) -> float:
        """Average confidence across all fields."""
        if not self.confidence:
            return 0.0
        return sum(self.confidence.values()) / len(self.confidence)

    @property
    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self.conflicts) > 0

    @property
    def has_low_confidence(self) -> bool:
        """Check if there are low confidence fields."""
        return len(self.low_confidence_fields) > 0

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get value for a field, with default fallback."""
        return self.data.get(field_name, default)

    def get_field_confidence(self, field_name: str) -> float:
        """Get confidence for a field (0 if not found)."""
        return self.confidence.get(field_name, 0.0)

    def flag_for_review(self, reason: str = ""):
        """Flag this extraction for human review."""
        self.needs_human_review = True
        if reason and reason not in self.conflicts:
            self.conflicts.append(reason)


@dataclass
class ExtractionResult:
    """Complete extraction results across multiple papers.

    This is the output of a batch extraction operation.
    """

    schema: ExtractionSchema
    extractions: list[ExtractedData]
    extraction_method: ExtractionMethod

    # Summary statistics
    total_papers: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    papers_needing_review: int = 0

    # Quality metrics
    average_quality: float = 0.0
    average_confidence: float = 0.0
    conflict_rate: float = 0.0  # Percentage of papers with conflicts

    # Performance
    total_time_ms: int = 0
    average_time_per_paper_ms: float = 0.0

    # Cost tracking (OpenAI API tokens)
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    estimated_cost: float = 0.0  # USD

    def __post_init__(self):
        """Calculate summary statistics."""
        if self.extractions:
            self.total_papers = len(self.extractions)
            self.successful_extractions = sum(
                1 for e in self.extractions if not e.needs_human_review
            )
            self.failed_extractions = self.total_papers - self.successful_extractions
            self.papers_needing_review = sum(1 for e in self.extractions if e.needs_human_review)

            # Quality metrics
            self.average_quality = (
                sum(e.extraction_quality for e in self.extractions) / self.total_papers
            )
            self.average_confidence = (
                sum(e.average_confidence for e in self.extractions) / self.total_papers
            )
            self.conflict_rate = (
                sum(1 for e in self.extractions if e.has_conflicts) / self.total_papers
            )

            # Performance
            if self.total_time_ms > 0 and self.total_papers > 0:
                self.average_time_per_paper_ms = self.total_time_ms / self.total_papers

    @property
    def success_rate(self) -> float:
        """Percentage of successful extractions (0-1)."""
        if self.total_papers == 0:
            return 0.0
        return self.successful_extractions / self.total_papers

    def get_extraction(self, paper_id: str) -> ExtractedData | None:
        """Get extraction for a specific paper."""
        return next((e for e in self.extractions if e.paper_id == paper_id), None)

    def get_extractions_needing_review(self) -> list[ExtractedData]:
        """Get all extractions flagged for human review."""
        return [e for e in self.extractions if e.needs_human_review]

    def get_successful_extractions(self) -> list[ExtractedData]:
        """Get all successful extractions (no review needed)."""
        return [e for e in self.extractions if not e.needs_human_review]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schema": {
                "name": self.schema.name,
                "version": self.schema.version,
                "fields": [f.name for f in self.schema.fields],
            },
            "extraction_method": self.extraction_method.value,
            "summary": {
                "total_papers": self.total_papers,
                "successful": self.successful_extractions,
                "failed": self.failed_extractions,
                "needs_review": self.papers_needing_review,
                "average_quality": round(self.average_quality, 3),
                "average_confidence": round(self.average_confidence, 3),
                "conflict_rate": round(self.conflict_rate, 3),
            },
            "performance": {
                "total_time_ms": self.total_time_ms,
                "avg_time_per_paper_ms": round(self.average_time_per_paper_ms, 1),
                "total_tokens_input": self.total_tokens_input,
                "total_tokens_output": self.total_tokens_output,
                "estimated_cost_usd": round(self.estimated_cost, 2),
            },
            "extractions": [
                {
                    "paper_id": e.paper_id,
                    "data": e.data,
                    "confidence": e.confidence,
                    "quality": e.extraction_quality,
                    "needs_review": e.needs_human_review,
                    "conflicts": e.conflicts,
                }
                for e in self.extractions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionResult:
        """Create ExtractionResult from dictionary.

        Args:
            data: Dictionary from JSON file

        Returns:
            ExtractionResult instance
        """
        # Import here to avoid circular dependency
        from arakis.extraction.schemas import get_schema

        # Get schema
        schema_data = data.get("schema", {})
        schema_name = schema_data.get("name", "rct")

        try:
            schema = get_schema(schema_name)
        except ValueError:
            # Fallback: create a minimal schema from the data
            schema = ExtractionSchema(
                name=schema_name,
                description="Loaded from saved extraction",
                fields=[],
                version=schema_data.get("version", "1.0"),
            )

        # Parse extraction method
        method_str = data.get("extraction_method", "triple-review")
        extraction_method = ExtractionMethod(method_str)

        # Parse extractions
        extractions = []
        papers_data = data.get("papers", data.get("extractions", []))

        for paper_data in papers_data:
            extraction = ExtractedData(
                paper_id=paper_data.get("paper_id", ""),
                schema_name=schema_name,
                extraction_method=extraction_method,
                data=paper_data.get("data", {}),
                confidence=paper_data.get("confidence", {}),
                extraction_quality=paper_data.get("quality", 0.0),
                needs_human_review=paper_data.get("needs_review", False),
                conflicts=paper_data.get("conflicts", []),
                low_confidence_fields=paper_data.get("low_confidence_fields", []),
                extraction_time_ms=paper_data.get("extraction_time_ms", 0),
            )
            extractions.append(extraction)

        # Parse performance metrics
        performance = data.get("performance", {})

        # Create result
        result = cls(
            schema=schema,
            extractions=extractions,
            extraction_method=extraction_method,
            total_time_ms=performance.get("total_time_ms", 0),
            total_tokens_input=performance.get("total_tokens_input", 0),
            total_tokens_output=performance.get("total_tokens_output", 0),
            estimated_cost=performance.get("estimated_cost_usd", 0.0),
        )

        return result

    @property
    def papers(self) -> list[ExtractedData]:
        """Alias for extractions to match JSON format."""
        return self.extractions
