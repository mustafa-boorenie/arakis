"""Audit trail models for tracking paper processing history.

This module provides a comprehensive audit trail for each paper, recording
all events that occur during the systematic review pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class AuditEventType(str, Enum):
    """Types of events that can be recorded in the audit trail."""

    # Paper lifecycle events
    PAPER_CREATED = "paper_created"
    PAPER_RETRIEVED = "paper_retrieved"
    PAPER_UPDATED = "paper_updated"

    # Search and deduplication
    SEARCH_RESULT = "search_result"
    DUPLICATE_DETECTED = "duplicate_detected"
    MARKED_AS_DUPLICATE = "marked_as_duplicate"
    METADATA_MERGED = "metadata_merged"

    # Screening events
    SCREENING_STARTED = "screening_started"
    SCREENING_PASS_1 = "screening_pass_1"
    SCREENING_PASS_2 = "screening_pass_2"
    SCREENING_CONFLICT = "screening_conflict"
    SCREENING_RESOLVED = "screening_resolved"
    SCREENING_COMPLETED = "screening_completed"
    SCREENING_HUMAN_REVIEW = "screening_human_review"
    SCREENING_HUMAN_OVERRIDE = "screening_human_override"

    # Full text retrieval
    FULL_TEXT_FETCH_STARTED = "full_text_fetch_started"
    FULL_TEXT_FETCH_SUCCESS = "full_text_fetch_success"
    FULL_TEXT_FETCH_FAILED = "full_text_fetch_failed"
    FULL_TEXT_EXTRACTED = "full_text_extracted"

    # Data extraction events
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_PASS = "extraction_pass"
    EXTRACTION_CONFLICT = "extraction_conflict"
    EXTRACTION_RESOLVED = "extraction_resolved"
    EXTRACTION_COMPLETED = "extraction_completed"
    EXTRACTION_HUMAN_REVIEW = "extraction_human_review"
    EXTRACTION_HUMAN_OVERRIDE = "extraction_human_override"

    # Analysis events
    INCLUDED_IN_ANALYSIS = "included_in_analysis"
    EXCLUDED_FROM_ANALYSIS = "excluded_from_analysis"

    # General events
    FIELD_UPDATED = "field_updated"
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass
class AuditEvent:
    """A single event in the paper's audit trail.

    Captures what happened, when, by whom, and any relevant details.
    """

    event_type: AuditEventType
    timestamp: datetime = field(default_factory=_utc_now)

    # What agent/user/system triggered this event
    actor: str = "system"  # e.g., "ScreeningAgent", "user:john@example.com", "PubMedClient"

    # Human-readable description of what happened
    description: str = ""

    # Structured details about the event
    details: dict[str, Any] = field(default_factory=dict)

    # For events that change fields, track before/after values
    field_changes: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Format: {"field_name": {"before": old_value, "after": new_value}}

    # Context information
    stage: str | None = None  # "search", "screening", "extraction", "analysis"
    model_used: str | None = None  # LLM model if applicable, e.g., "gpt-4o"
    temperature: float | None = None  # LLM temperature if applicable

    # Performance and cost tracking
    duration_ms: int | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "description": self.description,
        }

        if self.details:
            result["details"] = self.details
        if self.field_changes:
            result["field_changes"] = self.field_changes
        if self.stage:
            result["stage"] = self.stage
        if self.model_used:
            result["model_used"] = self.model_used
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.tokens_used is not None:
            result["tokens_used"] = self.tokens_used
        if self.cost_usd is not None:
            result["cost_usd"] = self.cost_usd

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Create an AuditEvent from a dictionary."""
        return cls(
            event_type=AuditEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data.get("actor", "system"),
            description=data.get("description", ""),
            details=data.get("details", {}),
            field_changes=data.get("field_changes", {}),
            stage=data.get("stage"),
            model_used=data.get("model_used"),
            temperature=data.get("temperature"),
            duration_ms=data.get("duration_ms"),
            tokens_used=data.get("tokens_used"),
            cost_usd=data.get("cost_usd"),
        )


@dataclass
class AuditTrail:
    """Complete audit trail for a paper.

    Maintains a chronological list of all events that occurred during
    the paper's processing through the systematic review pipeline.
    """

    paper_id: str
    events: list[AuditEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)

    def add_event(
        self,
        event_type: AuditEventType,
        description: str = "",
        actor: str = "system",
        details: dict[str, Any] | None = None,
        field_changes: dict[str, dict[str, Any]] | None = None,
        stage: str | None = None,
        model_used: str | None = None,
        temperature: float | None = None,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        cost_usd: float | None = None,
    ) -> AuditEvent:
        """Add a new event to the audit trail.

        Args:
            event_type: Type of event
            description: Human-readable description
            actor: Who/what triggered the event
            details: Additional structured details
            field_changes: Dict of field changes with before/after values
            stage: Pipeline stage (search, screening, extraction, analysis)
            model_used: LLM model used if applicable
            temperature: LLM temperature if applicable
            duration_ms: Time taken for the operation
            tokens_used: Tokens used for LLM calls
            cost_usd: Cost of the operation

        Returns:
            The created AuditEvent
        """
        event = AuditEvent(
            event_type=event_type,
            description=description,
            actor=actor,
            details=details or {},
            field_changes=field_changes or {},
            stage=stage,
            model_used=model_used,
            temperature=temperature,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )
        self.events.append(event)
        return event

    def add_field_change(
        self,
        field_name: str,
        before: Any,
        after: Any,
        actor: str = "system",
        description: str = "",
    ) -> AuditEvent:
        """Convenience method to record a field change.

        Args:
            field_name: Name of the field that changed
            before: Value before the change
            after: Value after the change
            actor: Who/what made the change
            description: Optional description of why the change was made

        Returns:
            The created AuditEvent
        """
        return self.add_event(
            event_type=AuditEventType.FIELD_UPDATED,
            description=description or f"Field '{field_name}' updated",
            actor=actor,
            field_changes={field_name: {"before": before, "after": after}},
        )

    def add_error(
        self,
        error_message: str,
        error_type: str = "",
        actor: str = "system",
        stage: str | None = None,
    ) -> AuditEvent:
        """Convenience method to record an error.

        Args:
            error_message: The error message
            error_type: Type/class of the error
            actor: Who/what encountered the error
            stage: Pipeline stage where error occurred

        Returns:
            The created AuditEvent
        """
        return self.add_event(
            event_type=AuditEventType.ERROR,
            description=error_message,
            actor=actor,
            details={"error_type": error_type} if error_type else {},
            stage=stage,
        )

    def add_warning(
        self,
        warning_message: str,
        actor: str = "system",
        stage: str | None = None,
    ) -> AuditEvent:
        """Convenience method to record a warning.

        Args:
            warning_message: The warning message
            actor: Who/what generated the warning
            stage: Pipeline stage where warning occurred

        Returns:
            The created AuditEvent
        """
        return self.add_event(
            event_type=AuditEventType.WARNING,
            description=warning_message,
            actor=actor,
            stage=stage,
        )

    def add_note(
        self,
        note: str,
        actor: str = "system",
        stage: str | None = None,
    ) -> AuditEvent:
        """Convenience method to add a note.

        Args:
            note: The note content
            actor: Who/what added the note
            stage: Pipeline stage

        Returns:
            The created AuditEvent
        """
        return self.add_event(
            event_type=AuditEventType.NOTE,
            description=note,
            actor=actor,
            stage=stage,
        )

    def get_events_by_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_stage(self, stage: str) -> list[AuditEvent]:
        """Get all events from a specific pipeline stage."""
        return [e for e in self.events if e.stage == stage]

    def get_events_by_actor(self, actor: str) -> list[AuditEvent]:
        """Get all events triggered by a specific actor."""
        return [e for e in self.events if e.actor == actor]

    def get_errors(self) -> list[AuditEvent]:
        """Get all error events."""
        return self.get_events_by_type(AuditEventType.ERROR)

    def get_warnings(self) -> list[AuditEvent]:
        """Get all warning events."""
        return self.get_events_by_type(AuditEventType.WARNING)

    def get_field_history(self, field_name: str) -> list[AuditEvent]:
        """Get all events that changed a specific field."""
        return [e for e in self.events if field_name in e.field_changes]

    @property
    def last_event(self) -> AuditEvent | None:
        """Get the most recent event."""
        return self.events[-1] if self.events else None

    @property
    def total_cost(self) -> float:
        """Sum of all costs recorded in events."""
        return sum(e.cost_usd or 0.0 for e in self.events)

    @property
    def total_tokens(self) -> int:
        """Sum of all tokens used in events."""
        return sum(e.tokens_used or 0 for e in self.events)

    @property
    def total_duration_ms(self) -> int:
        """Sum of all durations recorded in events."""
        return sum(e.duration_ms or 0 for e in self.events)

    @property
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return any(e.event_type == AuditEventType.ERROR for e in self.events)

    @property
    def has_conflicts(self) -> bool:
        """Check if any conflicts were recorded (screening or extraction)."""
        return any(
            e.event_type in (AuditEventType.SCREENING_CONFLICT, AuditEventType.EXTRACTION_CONFLICT)
            for e in self.events
        )

    @property
    def was_human_reviewed(self) -> bool:
        """Check if paper was reviewed by a human at any stage."""
        return any(
            e.event_type
            in (
                AuditEventType.SCREENING_HUMAN_REVIEW,
                AuditEventType.EXTRACTION_HUMAN_REVIEW,
            )
            for e in self.events
        )

    @property
    def was_human_overridden(self) -> bool:
        """Check if a human overrode an AI decision."""
        return any(
            e.event_type
            in (
                AuditEventType.SCREENING_HUMAN_OVERRIDE,
                AuditEventType.EXTRACTION_HUMAN_OVERRIDE,
            )
            for e in self.events
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert audit trail to dictionary for serialization."""
        return {
            "paper_id": self.paper_id,
            "created_at": self.created_at.isoformat(),
            "events": [e.to_dict() for e in self.events],
            "summary": {
                "total_events": len(self.events),
                "total_cost_usd": self.total_cost,
                "total_tokens": self.total_tokens,
                "total_duration_ms": self.total_duration_ms,
                "has_errors": self.has_errors,
                "has_conflicts": self.has_conflicts,
                "was_human_reviewed": self.was_human_reviewed,
                "was_human_overridden": self.was_human_overridden,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditTrail:
        """Create an AuditTrail from a dictionary."""
        trail = cls(
            paper_id=data["paper_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        trail.events = [AuditEvent.from_dict(e) for e in data.get("events", [])]
        return trail

    def __len__(self) -> int:
        """Return number of events in the trail."""
        return len(self.events)

    def __iter__(self):
        """Iterate over events."""
        return iter(self.events)


def create_audit_trail(paper_id: str, source: str = "unknown") -> AuditTrail:
    """Create a new audit trail with an initial creation event.

    Args:
        paper_id: ID of the paper
        source: Source database/system

    Returns:
        New AuditTrail with PAPER_CREATED event
    """
    trail = AuditTrail(paper_id=paper_id)
    trail.add_event(
        event_type=AuditEventType.PAPER_CREATED,
        description=f"Paper record created from {source}",
        actor=source,
        stage="search",
    )
    return trail
