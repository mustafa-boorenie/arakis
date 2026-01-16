from __future__ import annotations

"""Models for paper screening decisions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ScreeningStatus(str, Enum):
    """Screening decision status."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"  # Requires human review


@dataclass
class ScreeningDecision:
    """Result of screening a paper against criteria."""

    paper_id: str
    status: ScreeningStatus
    reason: str
    confidence: float = 0.0  # 0-1 confidence score

    # Criteria matching
    matched_inclusion: list[str] = field(default_factory=list)
    matched_exclusion: list[str] = field(default_factory=list)

    # Metadata
    screener: str = "gpt-4o"  # Model or human identifier
    screened_at: datetime = field(default_factory=_utc_now)

    # For dual-review mode
    is_conflict: bool = False
    second_opinion: ScreeningDecision | None = None

    # For human-in-the-loop review
    human_reviewed: bool = False
    ai_decision: ScreeningStatus | None = None  # Original AI decision before human review
    ai_reason: str | None = None  # Original AI reason
    human_decision: ScreeningStatus | None = None  # Human override decision
    human_reason: str | None = None  # Human override reason
    overridden: bool = False  # True if human changed AI decision


@dataclass
class ScreeningCriteria:
    """Inclusion and exclusion criteria for screening."""

    inclusion: list[str]
    exclusion: list[str]

    # PICO components (optional, for structured screening)
    population: str | None = None
    intervention: str | None = None
    comparison: str | None = None
    outcome: str | None = None

    # Study design filters
    study_types: list[str] = field(default_factory=list)  # e.g., ["RCT", "cohort"]
    min_year: int | None = None
    max_year: int | None = None
    languages: list[str] = field(default_factory=lambda: ["English"])

    def to_prompt(self) -> str:
        """Convert criteria to a structured prompt for LLM screening."""
        parts = []

        if self.population:
            parts.append(f"Population: {self.population}")
        if self.intervention:
            parts.append(f"Intervention: {self.intervention}")
        if self.comparison:
            parts.append(f"Comparison: {self.comparison}")
        if self.outcome:
            parts.append(f"Outcome: {self.outcome}")

        if self.inclusion:
            parts.append("\nInclusion criteria:\n" + "\n".join(f"- {c}" for c in self.inclusion))

        if self.exclusion:
            parts.append("\nExclusion criteria:\n" + "\n".join(f"- {c}" for c in self.exclusion))

        if self.study_types:
            parts.append(f"\nAccepted study types: {', '.join(self.study_types)}")

        if self.min_year or self.max_year:
            year_range = f"{self.min_year or 'any'} - {self.max_year or 'present'}"
            parts.append(f"Publication years: {year_range}")

        return "\n".join(parts)
