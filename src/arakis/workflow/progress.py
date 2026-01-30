"""Progress tracking infrastructure for real-time workflow feedback.

Provides granular progress updates during workflow execution with:
- Batched database writes (every 2 seconds)
- Rolling buffer of recent events (last 20)
- Summary statistics for UI display
- Estimated time remaining calculations
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.database.models import WorkflowStageCheckpoint

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """A single progress event for a workflow stage."""

    stage: str
    event_type: str  # item_started, item_completed, summary_update, thought, phase_changed
    current: int
    total: int
    item_data: Optional[dict[str, Any]] = None  # Current item being processed
    result_data: Optional[dict[str, Any]] = None  # Result of processing
    thought_process: Optional[str] = None  # AI reasoning/thought process
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "stage": self.stage,
            "event_type": self.event_type,
            "current": self.current,
            "total": self.total,
            "item_data": self.item_data,
            "result_data": self.result_data,
            "thought_process": self.thought_process,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SearchProgressData:
    """Progress data structure for search stage."""

    phase: str = "generating_queries"  # generating_queries | searching | deduplicating
    current_database: Optional[str] = None
    databases_completed: list[str] = field(default_factory=list)
    thought_process: Optional[str] = None
    queries: dict[str, str] = field(default_factory=dict)
    results_per_database: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phase": self.phase,
            "current_database": self.current_database,
            "databases_completed": self.databases_completed,
            "thought_process": self.thought_process,
            "queries": self.queries,
            "results_per_database": self.results_per_database,
        }


@dataclass
class ScreeningProgressData:
    """Progress data structure for screening stage."""

    current_paper: Optional[dict[str, Any]] = None  # {id, title, index}
    summary: dict[str, int] = field(
        default_factory=lambda: {"total": 0, "included": 0, "excluded": 0, "maybe": 0, "conflicts": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_paper": self.current_paper,
            "summary": self.summary,
        }


@dataclass
class FetchProgressData:
    """Progress data structure for PDF fetch stage."""

    current_paper: Optional[dict[str, Any]] = None  # {id, title, index}
    current_source: Optional[str] = None
    sources_tried: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(
        default_factory=lambda: {"total": 0, "fetched": 0, "failed": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_paper": self.current_paper,
            "current_source": self.current_source,
            "sources_tried": self.sources_tried,
            "summary": self.summary,
        }


@dataclass
class WritingProgressData:
    """Progress data structure for writing stages."""

    current_subsection: Optional[str] = None
    subsections_completed: list[str] = field(default_factory=list)
    subsections_pending: list[str] = field(default_factory=list)
    thought_process: Optional[str] = None
    word_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_subsection": self.current_subsection,
            "subsections_completed": self.subsections_completed,
            "subsections_pending": self.subsections_pending,
            "thought_process": self.thought_process,
            "word_count": self.word_count,
        }


class ProgressTracker:
    """Batches progress updates to database every 2 seconds.

    Maintains a rolling buffer of the last 20 events and summary statistics.
    Updates are batched to avoid overwhelming the database with writes.
    """

    def __init__(
        self,
        workflow_id: str,
        stage: str,
        db: AsyncSession,
        batch_interval: float = 2.0,
        max_events: int = 20,
    ):
        """Initialize the progress tracker.

        Args:
            workflow_id: The workflow ID
            stage: The stage name (search, screen, etc.)
            db: Async database session
            batch_interval: Seconds between database writes (default 2.0)
            max_events: Maximum events to keep in rolling buffer (default 20)
        """
        self.workflow_id = workflow_id
        self.stage = stage
        self.db = db
        self.batch_interval = batch_interval
        self.max_events = max_events

        # Rolling buffer of recent events
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=max_events)

        # Stage-specific progress data
        self._stage_data: dict[str, Any] = {}

        # Summary statistics
        self._summary: dict[str, Any] = {}

        # Timing for batching
        self._last_flush: datetime = datetime.now(timezone.utc)
        self._start_time: Optional[datetime] = None
        self._items_processed: int = 0
        self._total_items: int = 0

        # Processing time tracking for estimates
        self._processing_times: deque[float] = deque(maxlen=50)

    async def emit(self, event: ProgressEvent) -> None:
        """Emit a progress event.

        Args:
            event: The progress event to emit
        """
        # Track start time on first event
        if self._start_time is None:
            self._start_time = datetime.now(timezone.utc)

        # Add to rolling buffer
        self._recent_events.append(event.to_dict())

        # Update summary from result data
        if event.result_data:
            self._update_summary(event)

        # Track item processing for time estimates
        if event.event_type == "item_completed":
            self._items_processed = event.current
            self._total_items = event.total
            if len(self._recent_events) >= 2:
                # Calculate processing time for this item
                prev_event = self._recent_events[-2]
                prev_time = datetime.fromisoformat(prev_event["timestamp"])
                elapsed = (event.timestamp - prev_time).total_seconds()
                self._processing_times.append(elapsed)

        # Determine if we should flush to database
        elapsed_since_flush = (datetime.now(timezone.utc) - self._last_flush).total_seconds()
        should_flush = (
            elapsed_since_flush >= self.batch_interval
            or event.event_type == "stage_completed"
            or event.event_type == "phase_changed"
            or (event.current == event.total and event.total > 0)
        )

        if should_flush:
            await self._flush()

    async def emit_thought(self, thought: str) -> None:
        """Emit a thought/reasoning event.

        Args:
            thought: The AI thought/reasoning text
        """
        event = ProgressEvent(
            stage=self.stage,
            event_type="thought",
            current=self._items_processed,
            total=self._total_items,
            thought_process=thought,
        )
        await self.emit(event)

    async def emit_phase_change(self, phase: str, details: Optional[dict[str, Any]] = None) -> None:
        """Emit a phase change event (e.g., generating_queries -> searching).

        Args:
            phase: The new phase name
            details: Optional details about the phase
        """
        self._stage_data["phase"] = phase
        if details:
            self._stage_data.update(details)

        event = ProgressEvent(
            stage=self.stage,
            event_type="phase_changed",
            current=self._items_processed,
            total=self._total_items,
            item_data={"phase": phase, **(details or {})},
        )
        await self.emit(event)

    async def emit_item_started(
        self,
        current: int,
        total: int,
        item_data: dict[str, Any],
    ) -> None:
        """Emit an item started event.

        Args:
            current: Current item index (1-based)
            total: Total items to process
            item_data: Data about the current item
        """
        event = ProgressEvent(
            stage=self.stage,
            event_type="item_started",
            current=current,
            total=total,
            item_data=item_data,
        )
        await self.emit(event)

    async def emit_item_completed(
        self,
        current: int,
        total: int,
        item_data: dict[str, Any],
        result_data: dict[str, Any],
    ) -> None:
        """Emit an item completed event.

        Args:
            current: Current item index (1-based)
            total: Total items to process
            item_data: Data about the completed item
            result_data: Result of processing the item
        """
        event = ProgressEvent(
            stage=self.stage,
            event_type="item_completed",
            current=current,
            total=total,
            item_data=item_data,
            result_data=result_data,
        )
        await self.emit(event)

    def set_stage_data(self, data: dict[str, Any]) -> None:
        """Set stage-specific progress data.

        Args:
            data: Stage-specific data dictionary
        """
        self._stage_data.update(data)

    def update_summary(self, key: str, value: Any) -> None:
        """Update a summary statistic.

        Args:
            key: Summary key
            value: Summary value
        """
        self._summary[key] = value

    def increment_summary(self, key: str, amount: int = 1) -> None:
        """Increment a summary counter.

        Args:
            key: Summary key
            amount: Amount to increment (default 1)
        """
        self._summary[key] = self._summary.get(key, 0) + amount

    def _update_summary(self, event: ProgressEvent) -> None:
        """Update summary from event result data.

        Args:
            event: The event containing result data
        """
        if not event.result_data:
            return

        # For screening decisions
        if "decision" in event.result_data:
            decision = event.result_data["decision"]
            self._summary["total"] = self._summary.get("total", 0) + 1
            if decision == "INCLUDE":
                self._summary["included"] = self._summary.get("included", 0) + 1
            elif decision == "EXCLUDE":
                self._summary["excluded"] = self._summary.get("excluded", 0) + 1
            elif decision == "MAYBE":
                self._summary["maybe"] = self._summary.get("maybe", 0) + 1
            if event.result_data.get("is_conflict"):
                self._summary["conflicts"] = self._summary.get("conflicts", 0) + 1

        # For fetch results
        if "success" in event.result_data and "source" in event.result_data:
            if event.result_data["success"]:
                self._summary["fetched"] = self._summary.get("fetched", 0) + 1
            else:
                self._summary["failed"] = self._summary.get("failed", 0) + 1

    def _estimate_remaining_seconds(self) -> Optional[int]:
        """Estimate remaining time based on processing speed.

        Returns:
            Estimated seconds remaining, or None if not enough data
        """
        if not self._processing_times or self._total_items == 0:
            return None

        avg_time = sum(self._processing_times) / len(self._processing_times)
        remaining_items = self._total_items - self._items_processed
        return int(avg_time * remaining_items)

    async def _flush(self) -> None:
        """Write progress data to the database checkpoint."""
        try:
            # Get or create checkpoint
            result = await self.db.execute(
                select(WorkflowStageCheckpoint).where(
                    WorkflowStageCheckpoint.workflow_id == self.workflow_id,
                    WorkflowStageCheckpoint.stage == self.stage,
                )
            )
            checkpoint = result.scalar_one_or_none()

            if checkpoint is None:
                logger.warning(
                    f"[progress] No checkpoint found for workflow={self.workflow_id}, stage={self.stage}"
                )
                return

            # Build progress data
            progress_data = {
                **self._stage_data,
                "summary": self._summary,
                "recent_decisions": list(self._recent_events),
                "estimated_remaining_seconds": self._estimate_remaining_seconds(),
                "items_processed": self._items_processed,
                "total_items": self._total_items,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Update checkpoint
            checkpoint.progress_data = progress_data
            await self.db.commit()

            self._last_flush = datetime.now(timezone.utc)
            logger.debug(
                f"[progress] Flushed progress for {self.stage}: "
                f"{self._items_processed}/{self._total_items}"
            )

        except Exception as e:
            logger.warning(f"[progress] Failed to flush progress: {e}")

    async def finalize(self) -> None:
        """Finalize progress tracking and ensure all data is written."""
        await self._flush()


def create_screening_callback(
    tracker: ProgressTracker,
) -> Callable:
    """Create a screening progress callback that emits events to the tracker.

    Args:
        tracker: The progress tracker instance

    Returns:
        Callback function compatible with ScreeningAgent.screen_batch
    """

    async def callback(current: int, total: int, paper, decision) -> None:
        """Progress callback for screening."""
        # Emit item completed event with full decision details
        await tracker.emit_item_completed(
            current=current,
            total=total,
            item_data={
                "id": paper.id,
                "title": paper.title[:100] if paper.title else "",
                "index": current,
            },
            result_data={
                "paper_id": decision.paper_id,
                "title": paper.title[:100] if paper.title else "",
                "decision": decision.status.value,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "matched_inclusion": decision.matched_inclusion or [],
                "matched_exclusion": decision.matched_exclusion or [],
                "is_conflict": decision.is_conflict,
            },
        )

    return callback


def create_fetch_callback(
    tracker: ProgressTracker,
) -> Callable:
    """Create a fetch progress callback that emits events to the tracker.

    Args:
        tracker: The progress tracker instance

    Returns:
        Callback function compatible with PaperFetcher
    """

    async def callback(
        current: int,
        total: int,
        paper_id: str,
        paper_title: str,
        success: bool,
        source: Optional[str],
        sources_tried: list[str],
    ) -> None:
        """Progress callback for PDF fetching."""
        await tracker.emit_item_completed(
            current=current,
            total=total,
            item_data={
                "id": paper_id,
                "title": paper_title[:100] if paper_title else "",
                "index": current,
            },
            result_data={
                "paper_id": paper_id,
                "success": success,
                "source": source,
                "sources_tried": sources_tried,
            },
        )

    return callback


def create_extraction_callback(
    tracker: ProgressTracker,
) -> Callable:
    """Create an extraction progress callback that emits events to the tracker.

    Args:
        tracker: The progress tracker instance

    Returns:
        Callback function compatible with DataExtractionAgent
    """

    async def callback(
        current: int,
        total: int,
        paper_id: str,
        paper_title: str,
        extraction_quality: float,
        needs_review: bool,
    ) -> None:
        """Progress callback for data extraction."""
        await tracker.emit_item_completed(
            current=current,
            total=total,
            item_data={
                "id": paper_id,
                "title": paper_title[:100] if paper_title else "",
                "index": current,
            },
            result_data={
                "paper_id": paper_id,
                "extraction_quality": extraction_quality,
                "needs_review": needs_review,
            },
        )

    return callback


def create_writing_callback(
    tracker: ProgressTracker,
    subsections: list[str],
) -> Callable:
    """Create a writing progress callback that emits events to the tracker.

    Args:
        tracker: The progress tracker instance
        subsections: List of subsection names in order

    Returns:
        Callback function for writing agents
    """
    completed = []

    async def callback(
        subsection: str,
        word_count: int,
        thought_process: Optional[str] = None,
    ) -> None:
        """Progress callback for writing stages."""
        completed.append(subsection)
        pending = [s for s in subsections if s not in completed]

        tracker.set_stage_data({
            "current_subsection": subsection,
            "subsections_completed": completed.copy(),
            "subsections_pending": pending,
            "word_count": word_count,
        })

        if thought_process:
            await tracker.emit_thought(thought_process)

        await tracker.emit_item_completed(
            current=len(completed),
            total=len(subsections),
            item_data={
                "subsection": subsection,
                "index": len(completed),
            },
            result_data={
                "subsection": subsection,
                "word_count": word_count,
            },
        )

    return callback
