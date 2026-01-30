"""Base stage executor for the unified workflow system.

Provides common functionality for all stage executors:
- Retry logic with exponential backoff
- Checkpoint saving/loading
- Error handling with user prompts
- R2 figure upload helper
- Cost mode configuration support
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import ModeConfig, get_default_mode_config
from arakis.database.models import (
    Workflow,
    WorkflowFigure,
    WorkflowStageCheckpoint,
    WorkflowTable,
)
from arakis.storage.client import get_storage_client
from arakis.workflow.progress import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result from executing a stage."""

    success: bool
    output_data: dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    error: Optional[str] = None
    needs_user_action: bool = False
    action_required: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "output_data": self.output_data,
            "cost": self.cost,
            "error": self.error,
            "needs_user_action": self.needs_user_action,
            "action_required": self.action_required,
        }


class BaseStageExecutor(ABC):
    """Base class for all stage executors.

    Provides:
    - Retry logic with exponential backoff (3 retries)
    - Checkpoint saving to database
    - Error handling with user action prompts
    - R2 figure upload helper
    - Cost mode configuration support
    """

    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 2.0  # seconds

    # Subclasses must define these
    STAGE_NAME: str = ""  # e.g., "search", "screen", "pdf_fetch"

    def __init__(
        self,
        workflow_id: str,
        db: AsyncSession,
        mode_config: Optional[ModeConfig] = None,
    ):
        """Initialize the stage executor.

        Args:
            workflow_id: The workflow ID to execute for
            db: Async database session
            mode_config: Cost mode configuration. If None, uses default (BALANCED).
        """
        self.workflow_id = workflow_id
        self.db = db
        self.mode_config = mode_config or get_default_mode_config()
        self._storage_client = None
        self._progress_tracker: Optional[ProgressTracker] = None

    @property
    def storage_client(self):
        """Lazy-load storage client."""
        if self._storage_client is None:
            self._storage_client = get_storage_client()
        return self._storage_client

    async def init_progress_tracker(self) -> ProgressTracker:
        """Initialize and return a progress tracker for this stage.

        Returns:
            ProgressTracker instance for emitting progress events
        """
        self._progress_tracker = ProgressTracker(
            workflow_id=self.workflow_id,
            stage=self.STAGE_NAME,
            db=self.db,
        )
        return self._progress_tracker

    async def finalize_progress(self) -> None:
        """Finalize progress tracking, ensuring all data is written."""
        if self._progress_tracker:
            await self._progress_tracker.finalize()

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute the stage logic.

        Args:
            input_data: Input data from previous stages

        Returns:
            StageResult with success status and output data
        """
        pass

    @abstractmethod
    def get_required_stages(self) -> list[str]:
        """Return list of stages that must be completed before this one.

        Returns:
            List of stage names (e.g., ["search", "screen"])
        """
        pass

    async def run_with_retry(self, input_data: dict[str, Any]) -> StageResult:
        """Execute stage with retry logic and exponential backoff.

        Args:
            input_data: Input data from previous stages

        Returns:
            StageResult after retries exhausted or success
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(
                    f"[{self.STAGE_NAME}] Attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"for workflow {self.workflow_id}"
                )

                result = await self.execute(input_data)

                if result.success:
                    return result

                # Check if error is retryable
                if not self._is_retryable_error(result.error):
                    logger.warning(f"[{self.STAGE_NAME}] Non-retryable error: {result.error}")
                    return result

                last_error = result.error

            except Exception as e:
                last_error = str(e)
                logger.exception(f"[{self.STAGE_NAME}] Exception on attempt {attempt + 1}: {e}")

                if not self._is_retryable_error(str(e)):
                    return StageResult(
                        success=False,
                        error=str(e),
                        needs_user_action=True,
                        action_required=f"Stage '{self.STAGE_NAME}' failed with error: {e}",
                    )

            # Exponential backoff before retry
            if attempt < self.MAX_RETRIES - 1:
                delay = self.INITIAL_RETRY_DELAY * (2**attempt)
                logger.info(f"[{self.STAGE_NAME}] Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # All retries exhausted
        return StageResult(
            success=False,
            error=last_error,
            needs_user_action=True,
            action_required=(
                f"Stage '{self.STAGE_NAME}' failed after {self.MAX_RETRIES} attempts. "
                f"Last error: {last_error}"
            ),
        )

    def _is_retryable_error(self, error: Optional[str]) -> bool:
        """Check if error is transient and worth retrying.

        Args:
            error: Error message string

        Returns:
            True if error is retryable
        """
        if not error:
            return False

        error_lower = error.lower()
        retryable_patterns = [
            "rate limit",
            "rate_limit",
            "ratelimit",
            "429",
            "timeout",
            "timed out",
            "connection",
            "503",
            "502",
            "500",
            "service unavailable",
            "temporarily unavailable",
            "retry",
            "overloaded",
        ]
        return any(pattern in error_lower for pattern in retryable_patterns)

    async def get_workflow(self) -> Workflow:
        """Get the workflow from database.

        Returns:
            Workflow model instance
        """
        result = await self.db.execute(select(Workflow).where(Workflow.id == self.workflow_id))
        return result.scalar_one()

    async def update_workflow_stage(self, stage: str) -> None:
        """Update the workflow's current stage.

        Args:
            stage: New stage name
        """
        workflow = await self.get_workflow()
        workflow.current_stage = stage
        await self.db.commit()

    async def save_checkpoint(
        self,
        status: str,
        output_data: Optional[dict] = None,
        error_message: Optional[str] = None,
        cost: float = 0.0,
    ) -> WorkflowStageCheckpoint:
        """Save or update stage checkpoint.

        Args:
            status: Stage status (pending, in_progress, completed, failed, skipped)
            output_data: Stage output data to save
            error_message: Error message if failed
            cost: Cost incurred for this stage

        Returns:
            The checkpoint model instance
        """
        # Check if checkpoint exists
        result = await self.db.execute(
            select(WorkflowStageCheckpoint).where(
                WorkflowStageCheckpoint.workflow_id == self.workflow_id,
                WorkflowStageCheckpoint.stage == self.STAGE_NAME,
            )
        )
        checkpoint = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if checkpoint is None:
            # Create new checkpoint
            checkpoint = WorkflowStageCheckpoint(
                workflow_id=self.workflow_id,
                stage=self.STAGE_NAME,
                status=status,
                started_at=now if status == "in_progress" else None,
                completed_at=now if status in ("completed", "failed", "skipped") else None,
                output_data=output_data,
                error_message=error_message,
                cost=cost,
            )
            self.db.add(checkpoint)
        else:
            # Update existing checkpoint
            checkpoint.status = status
            if status == "in_progress" and checkpoint.started_at is None:
                checkpoint.started_at = now
            if status in ("completed", "failed", "skipped"):
                checkpoint.completed_at = now
            if status == "failed":
                checkpoint.retry_count += 1
            if output_data is not None:
                checkpoint.output_data = output_data
            if error_message is not None:
                checkpoint.error_message = error_message
            checkpoint.cost += cost

        await self.db.commit()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def get_checkpoint(self, stage: str) -> Optional[WorkflowStageCheckpoint]:
        """Get checkpoint for a stage.

        Args:
            stage: Stage name to get checkpoint for

        Returns:
            Checkpoint if exists, None otherwise
        """
        result = await self.db.execute(
            select(WorkflowStageCheckpoint).where(
                WorkflowStageCheckpoint.workflow_id == self.workflow_id,
                WorkflowStageCheckpoint.stage == stage,
            )
        )
        return result.scalar_one_or_none()

    async def upload_figure_to_r2(
        self,
        local_path: str,
        figure_type: str,
        title: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> str:
        """Upload figure to R2 and save record to database.

        Args:
            local_path: Path to local file
            figure_type: Type of figure (forest_plot, funnel_plot, prisma, etc.)
            title: Optional figure title
            caption: Optional figure caption

        Returns:
            Public URL of uploaded figure
        """
        # Read file content
        with open(local_path, "rb") as f:
            content = f.read()

        # Generate R2 key
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        r2_key = f"workflows/{self.workflow_id}/figures/{figure_type}_{timestamp}.png"

        # Upload to R2
        result = self.storage_client.upload_bytes(
            data=content,
            key=r2_key,
            content_type="image/png",
            metadata={
                "workflow_id": self.workflow_id,
                "figure_type": figure_type,
            },
        )

        if not result.success:
            raise RuntimeError(f"Failed to upload figure to R2: {result.error}")

        # Save figure record to database
        figure = WorkflowFigure(
            workflow_id=self.workflow_id,
            figure_type=figure_type,
            title=title,
            caption=caption,
            r2_key=r2_key,
            r2_url=result.url,
            file_size_bytes=len(content),
        )
        self.db.add(figure)
        await self.db.commit()

        logger.info(f"[{self.STAGE_NAME}] Uploaded {figure_type} to R2: {result.url}")
        return result.url

    async def save_table(
        self,
        table_type: str,
        headers: list[str],
        rows: list[list[Any]],
        title: Optional[str] = None,
        caption: Optional[str] = None,
        footnotes: Optional[list[str]] = None,
    ) -> WorkflowTable:
        """Save generated table to database.

        Args:
            table_type: Type of table (study_characteristics, risk_of_bias, grade_sof)
            headers: Column headers
            rows: Row data
            title: Optional table title
            caption: Optional table caption
            footnotes: Optional list of footnotes

        Returns:
            The table model instance
        """
        table = WorkflowTable(
            workflow_id=self.workflow_id,
            table_type=table_type,
            title=title,
            caption=caption,
            headers=headers,
            rows=rows,
            footnotes=footnotes or [],
        )
        self.db.add(table)
        await self.db.commit()
        await self.db.refresh(table)

        logger.info(
            f"[{self.STAGE_NAME}] Saved {table_type} table with "
            f"{len(headers)} columns and {len(rows)} rows"
        )
        return table
