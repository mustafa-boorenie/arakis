"""Data models for workflow state management and resume functionality."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class WorkflowStage(str, Enum):
    """Workflow stage identifiers."""

    INITIALIZED = "initialized"
    SEARCH = "search"
    SCREENING = "screening"
    PDF_FETCH = "pdf_fetch"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    PRISMA = "prisma"
    INTRODUCTION = "introduction"
    RESULTS = "results"
    MANUSCRIPT = "manuscript"
    COMPLETED = "completed"


class StageStatus(str, Enum):
    """Status of a workflow stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StageCheckpoint:
    """Checkpoint data for a single stage."""

    stage: WorkflowStage
    status: StageStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_file: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_file": self.output_file,
            "data": self.data,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageCheckpoint:
        """Create from dictionary."""
        return cls(
            stage=WorkflowStage(data["stage"]),
            status=StageStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            output_file=data.get("output_file"),
            data=data.get("data", {}),
            error=data.get("error"),
        )


@dataclass
class WorkflowState:
    """Complete workflow state for resume functionality.

    This captures the entire state of a workflow at any point,
    allowing exact resumption from where it was interrupted.
    """

    # Workflow identification
    workflow_id: str
    output_dir: str

    # Configuration (immutable once started)
    research_question: str
    inclusion_criteria: list[str]
    exclusion_criteria: list[str]
    databases: list[str]
    max_results: int
    fast_mode: bool = False
    extract_text: bool = True
    use_full_text: bool = True
    skip_analysis: bool = False
    skip_writing: bool = False
    schema: str = "auto"

    # Stage tracking
    current_stage: WorkflowStage = WorkflowStage.INITIALIZED
    stages: dict[str, StageCheckpoint] = field(default_factory=dict)

    # Timing
    started_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    completed_at: datetime | None = None

    # Cost tracking
    total_cost: float = 0.0

    # State version for compatibility
    version: str = "1.0"

    def __post_init__(self):
        """Initialize stages if empty."""
        if not self.stages:
            self._initialize_stages()

    def _initialize_stages(self):
        """Initialize all stages with pending status."""
        all_stages = [
            WorkflowStage.SEARCH,
            WorkflowStage.SCREENING,
            WorkflowStage.PDF_FETCH,
            WorkflowStage.EXTRACTION,
            WorkflowStage.ANALYSIS,
            WorkflowStage.PRISMA,
            WorkflowStage.INTRODUCTION,
            WorkflowStage.RESULTS,
            WorkflowStage.MANUSCRIPT,
        ]
        for stage in all_stages:
            self.stages[stage.value] = StageCheckpoint(
                stage=stage,
                status=StageStatus.PENDING,
            )

    def start_stage(self, stage: WorkflowStage) -> None:
        """Mark a stage as in progress."""
        self.current_stage = stage
        self.stages[stage.value].status = StageStatus.IN_PROGRESS
        self.stages[stage.value].started_at = _utc_now()
        self.updated_at = _utc_now()

    def complete_stage(
        self,
        stage: WorkflowStage,
        output_file: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Mark a stage as completed."""
        checkpoint = self.stages[stage.value]
        checkpoint.status = StageStatus.COMPLETED
        checkpoint.completed_at = _utc_now()
        if output_file:
            checkpoint.output_file = output_file
        if data:
            checkpoint.data = data
        self.updated_at = _utc_now()

    def skip_stage(self, stage: WorkflowStage, reason: str = "") -> None:
        """Mark a stage as skipped."""
        self.stages[stage.value].status = StageStatus.SKIPPED
        if reason:
            self.stages[stage.value].data["skip_reason"] = reason
        self.updated_at = _utc_now()

    def fail_stage(self, stage: WorkflowStage, error: str) -> None:
        """Mark a stage as failed."""
        self.stages[stage.value].status = StageStatus.FAILED
        self.stages[stage.value].error = error
        self.updated_at = _utc_now()

    def is_stage_completed(self, stage: WorkflowStage) -> bool:
        """Check if a stage is completed."""
        return self.stages[stage.value].status == StageStatus.COMPLETED

    def is_stage_skipped(self, stage: WorkflowStage) -> bool:
        """Check if a stage was skipped."""
        return self.stages[stage.value].status == StageStatus.SKIPPED

    def get_stage_data(self, stage: WorkflowStage) -> dict[str, Any]:
        """Get data from a completed stage."""
        return self.stages[stage.value].data

    def get_stage_output_file(self, stage: WorkflowStage) -> str | None:
        """Get output file from a completed stage."""
        return self.stages[stage.value].output_file

    def get_resume_stage(self) -> WorkflowStage | None:
        """Get the stage to resume from.

        Returns the first stage that is not completed or skipped,
        or None if all stages are done.
        """
        stage_order = [
            WorkflowStage.SEARCH,
            WorkflowStage.SCREENING,
            WorkflowStage.PDF_FETCH,
            WorkflowStage.EXTRACTION,
            WorkflowStage.ANALYSIS,
            WorkflowStage.PRISMA,
            WorkflowStage.INTRODUCTION,
            WorkflowStage.RESULTS,
            WorkflowStage.MANUSCRIPT,
        ]
        for stage in stage_order:
            status = self.stages[stage.value].status
            if status not in (StageStatus.COMPLETED, StageStatus.SKIPPED):
                return stage
        return None

    def mark_completed(self) -> None:
        """Mark the entire workflow as completed."""
        self.current_stage = WorkflowStage.COMPLETED
        self.completed_at = _utc_now()
        self.updated_at = _utc_now()

    @property
    def is_completed(self) -> bool:
        """Check if workflow is fully completed."""
        return self.current_stage == WorkflowStage.COMPLETED

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        total_stages = len(self.stages)
        completed = sum(
            1
            for s in self.stages.values()
            if s.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
        )
        return (completed / total_stages) * 100 if total_stages > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "workflow_id": self.workflow_id,
            "output_dir": self.output_dir,
            "config": {
                "research_question": self.research_question,
                "inclusion_criteria": self.inclusion_criteria,
                "exclusion_criteria": self.exclusion_criteria,
                "databases": self.databases,
                "max_results": self.max_results,
                "fast_mode": self.fast_mode,
                "extract_text": self.extract_text,
                "use_full_text": self.use_full_text,
                "skip_analysis": self.skip_analysis,
                "skip_writing": self.skip_writing,
                "schema": self.schema,
            },
            "current_stage": self.current_stage.value,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "timing": {
                "started_at": self.started_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            },
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowState:
        """Create WorkflowState from dictionary."""
        config = data.get("config", {})
        timing = data.get("timing", {})

        state = cls(
            workflow_id=data["workflow_id"],
            output_dir=data["output_dir"],
            research_question=config["research_question"],
            inclusion_criteria=config["inclusion_criteria"],
            exclusion_criteria=config["exclusion_criteria"],
            databases=config["databases"],
            max_results=config["max_results"],
            fast_mode=config.get("fast_mode", False),
            extract_text=config.get("extract_text", True),
            use_full_text=config.get("use_full_text", True),
            skip_analysis=config.get("skip_analysis", False),
            skip_writing=config.get("skip_writing", False),
            schema=config.get("schema", "auto"),
            current_stage=WorkflowStage(data["current_stage"]),
            started_at=datetime.fromisoformat(timing["started_at"])
            if timing.get("started_at")
            else _utc_now(),
            updated_at=datetime.fromisoformat(timing["updated_at"])
            if timing.get("updated_at")
            else _utc_now(),
            completed_at=datetime.fromisoformat(timing["completed_at"])
            if timing.get("completed_at")
            else None,
            total_cost=data.get("total_cost", 0.0),
            version=data.get("version", "1.0"),
        )

        # Load stages
        stages_data = data.get("stages", {})
        for stage_name, stage_data in stages_data.items():
            state.stages[stage_name] = StageCheckpoint.from_dict(stage_data)

        return state
