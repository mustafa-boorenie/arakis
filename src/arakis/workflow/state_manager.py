"""State management for workflow persistence and resume functionality."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from arakis.models.workflow_state import (
    StageStatus,
    WorkflowStage,
    WorkflowState,
)

if TYPE_CHECKING:
    from arakis.models.paper import Paper
    from arakis.models.screening import ScreeningDecision


class WorkflowStateManager:
    """Manages workflow state persistence and recovery.

    This class handles:
    - Creating and loading workflow state
    - Saving checkpoints after each stage
    - Validating state integrity for resume
    - Loading cached data from previous stages
    """

    STATE_FILENAME = "workflow_state.json"
    BACKUP_DIR = ".state_backups"

    def __init__(self, output_dir: str | Path):
        """Initialize state manager.

        Args:
            output_dir: Directory where workflow outputs and state are stored
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / self.STATE_FILENAME
        self._state: WorkflowState | None = None

    @property
    def state(self) -> WorkflowState | None:
        """Current workflow state."""
        return self._state

    def create_new_state(
        self,
        research_question: str,
        inclusion_criteria: list[str],
        exclusion_criteria: list[str],
        databases: list[str],
        max_results: int,
        fast_mode: bool = False,
        extract_text: bool = True,
        use_full_text: bool = True,
        skip_analysis: bool = False,
        skip_writing: bool = False,
        schema: str = "auto",
    ) -> WorkflowState:
        """Create a new workflow state.

        Args:
            research_question: The research question
            inclusion_criteria: List of inclusion criteria
            exclusion_criteria: List of exclusion criteria
            databases: List of databases to search
            max_results: Maximum results per database
            fast_mode: Whether to use fast mode (single-pass)
            extract_text: Whether to extract text from PDFs
            use_full_text: Whether to use full text for extraction
            skip_analysis: Whether to skip analysis stage
            skip_writing: Whether to skip writing stage
            schema: Extraction schema name

        Returns:
            New WorkflowState instance
        """
        workflow_id = str(uuid.uuid4())[:8]
        self._state = WorkflowState(
            workflow_id=workflow_id,
            output_dir=str(self.output_dir),
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            databases=databases,
            max_results=max_results,
            fast_mode=fast_mode,
            extract_text=extract_text,
            use_full_text=use_full_text,
            skip_analysis=skip_analysis,
            skip_writing=skip_writing,
            schema=schema,
        )
        self.save()
        return self._state

    def load_state(self) -> WorkflowState | None:
        """Load existing workflow state from file.

        Returns:
            WorkflowState if found, None otherwise
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                data = json.load(f)
            self._state = WorkflowState.from_dict(data)
            return self._state
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Invalid state file
            raise ValueError(f"Invalid state file: {e}") from e

    def save(self) -> None:
        """Save current state to file."""
        if self._state is None:
            raise ValueError("No state to save")

        # Create backup before overwriting
        self._create_backup()

        # Save current state
        with open(self.state_file, "w") as f:
            json.dump(self._state.to_dict(), f, indent=2)

    def _create_backup(self) -> None:
        """Create backup of current state file."""
        if not self.state_file.exists():
            return

        backup_dir = self.output_dir / self.BACKUP_DIR
        backup_dir.mkdir(exist_ok=True)

        # Use timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"state_{timestamp}.json"

        # Copy current state to backup
        with open(self.state_file) as src, open(backup_file, "w") as dst:
            dst.write(src.read())

        # Keep only last 10 backups
        backups = sorted(backup_dir.glob("state_*.json"))
        for old_backup in backups[:-10]:
            old_backup.unlink()

    def has_existing_state(self) -> bool:
        """Check if there's an existing state file."""
        return self.state_file.exists()

    def can_resume(self) -> bool:
        """Check if workflow can be resumed.

        Returns:
            True if state exists and is not completed
        """
        if not self.has_existing_state():
            return False

        try:
            state = self.load_state()
            if state is None:
                return False
            return not state.is_completed
        except ValueError:
            return False

    def get_resume_info(self) -> dict[str, Any] | None:
        """Get information about resumable state.

        Returns:
            Dict with resume information or None
        """
        if not self.can_resume():
            return None

        state = self._state
        if state is None:
            return None

        resume_stage = state.get_resume_stage()
        completed_stages = [
            stage for stage, checkpoint in state.stages.items()
            if checkpoint.status == StageStatus.COMPLETED
        ]

        return {
            "workflow_id": state.workflow_id,
            "research_question": state.research_question[:100] + "..." if len(state.research_question) > 100 else state.research_question,
            "started_at": state.started_at.isoformat(),
            "progress": f"{state.progress_percentage:.0f}%",
            "resume_stage": resume_stage.value if resume_stage else None,
            "completed_stages": completed_stages,
            "total_cost": state.total_cost,
        }

    def start_stage(self, stage: WorkflowStage) -> None:
        """Mark a stage as started and save state."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.start_stage(stage)
        self.save()

    def complete_stage(
        self,
        stage: WorkflowStage,
        output_file: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Mark a stage as completed and save state."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.complete_stage(stage, output_file, data)
        self.save()

    def skip_stage(self, stage: WorkflowStage, reason: str = "") -> None:
        """Mark a stage as skipped and save state."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.skip_stage(stage, reason)
        self.save()

    def fail_stage(self, stage: WorkflowStage, error: str) -> None:
        """Mark a stage as failed and save state."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.fail_stage(stage, error)
        self.save()

    def add_cost(self, cost: float) -> None:
        """Add cost to total and save state."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.total_cost += cost
        self.save()

    def mark_completed(self) -> None:
        """Mark workflow as completed."""
        if self._state is None:
            raise ValueError("No workflow state initialized")
        self._state.mark_completed()
        self.save()

    # Data loading helpers for resume

    def load_search_results(self) -> list[dict[str, Any]] | None:
        """Load search results from previous run.

        Returns:
            List of paper dictionaries or None
        """
        if self._state is None:
            return None

        search_file = self._state.get_stage_output_file(WorkflowStage.SEARCH)
        if search_file is None:
            # Try default filename
            search_file = str(self.output_dir / "1_search_results.json")

        path = Path(search_file)
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)

    def load_screening_decisions(self) -> list[dict[str, Any]] | None:
        """Load screening decisions from previous run.

        Returns:
            List of decision dictionaries or None
        """
        if self._state is None:
            return None

        screening_file = self._state.get_stage_output_file(WorkflowStage.SCREENING)
        if screening_file is None:
            screening_file = str(self.output_dir / "2_screening_decisions.json")

        path = Path(screening_file)
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)

    def load_extraction_results(self) -> dict[str, Any] | None:
        """Load extraction results from previous run.

        Returns:
            Extraction result dictionary or None
        """
        if self._state is None:
            return None

        extraction_file = self._state.get_stage_output_file(WorkflowStage.EXTRACTION)
        if extraction_file is None:
            extraction_file = str(self.output_dir / "3_extraction_results.json")

        path = Path(extraction_file)
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)

    def load_analysis_results(self) -> dict[str, Any] | None:
        """Load analysis results from previous run.

        Returns:
            Analysis result dictionary or None
        """
        if self._state is None:
            return None

        analysis_file = self._state.get_stage_output_file(WorkflowStage.ANALYSIS)
        if analysis_file is None:
            analysis_file = str(self.output_dir / "4_analysis_results.json")

        path = Path(analysis_file)
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)

    def validate_resume_data(self, resume_stage: WorkflowStage) -> tuple[bool, list[str]]:
        """Validate that required data exists for resuming at a given stage.

        Args:
            resume_stage: The stage to resume from

        Returns:
            Tuple of (is_valid, list of missing files/data)
        """
        missing = []

        # Define dependencies for each stage
        dependencies = {
            WorkflowStage.SEARCH: [],
            WorkflowStage.SCREENING: [WorkflowStage.SEARCH],
            WorkflowStage.PDF_FETCH: [WorkflowStage.SEARCH, WorkflowStage.SCREENING],
            WorkflowStage.EXTRACTION: [WorkflowStage.SEARCH, WorkflowStage.SCREENING],
            WorkflowStage.ANALYSIS: [WorkflowStage.EXTRACTION],
            WorkflowStage.PRISMA: [WorkflowStage.SEARCH, WorkflowStage.SCREENING],
            WorkflowStage.INTRODUCTION: [],
            WorkflowStage.RESULTS: [WorkflowStage.SCREENING],
            WorkflowStage.MANUSCRIPT: [],
        }

        required_stages = dependencies.get(resume_stage, [])

        for required_stage in required_stages:
            if self._state is None:
                missing.append(f"No state loaded")
                break

            checkpoint = self._state.stages.get(required_stage.value)
            if checkpoint is None or checkpoint.status != StageStatus.COMPLETED:
                missing.append(f"Stage '{required_stage.value}' not completed")
                continue

            # Check output file exists
            output_file = checkpoint.output_file
            if output_file and not Path(output_file).exists():
                missing.append(f"Output file missing: {output_file}")

        return len(missing) == 0, missing
