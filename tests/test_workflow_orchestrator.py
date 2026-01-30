"""Tests for WorkflowOrchestrator.

Integration tests for the workflow orchestrator that coordinates
the 12-stage systematic review workflow.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.config import get_default_mode_config
from arakis.workflow.orchestrator import WorkflowOrchestrator
from arakis.workflow.stages.base import StageResult

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()

    # Create a workflow mock with cost_mode for queries
    workflow_mock = MagicMock()
    workflow_mock.cost_mode = "BALANCED"
    workflow_mock.id = "test-workflow-123"
    workflow_mock.status = "running"
    workflow_mock.current_stage = "search"

    # Create a result mock for execute
    result_mock = MagicMock()
    result_mock.scalar_one = MagicMock(return_value=workflow_mock)
    result_mock.scalar_one_or_none = MagicMock(return_value=workflow_mock)

    # db.execute returns an awaitable that resolves to result_mock
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    return db


@pytest.fixture
def mock_workflow():
    """Create a mock Workflow model."""
    workflow = MagicMock()
    workflow.id = "test-workflow-123"
    workflow.research_question = "Effect of aspirin on mortality in sepsis patients"
    workflow.inclusion_criteria = ["Human RCTs", "Sepsis patients", "Mortality outcome"]
    workflow.exclusion_criteria = ["Animal studies", "Reviews"]
    workflow.databases = ["pubmed", "openalex"]
    workflow.current_stage = "search"
    workflow.status = "running"
    workflow.papers_found = 0
    workflow.papers_screened = 0
    workflow.papers_included = 0
    workflow.total_cost = 0.0
    workflow.needs_user_action = False
    workflow.action_required = None
    workflow.meta_analysis_feasible = None
    workflow.cost_mode = "BALANCED"
    return workflow


@pytest.fixture
def mock_checkpoint():
    """Create a mock WorkflowStageCheckpoint model."""

    def create_checkpoint(stage, status="completed", output_data=None):
        checkpoint = MagicMock()
        checkpoint.workflow_id = "test-workflow-123"
        checkpoint.stage = stage
        checkpoint.status = status
        checkpoint.started_at = datetime.now(timezone.utc)
        checkpoint.completed_at = datetime.now(timezone.utc) if status == "completed" else None
        checkpoint.retry_count = 0
        checkpoint.output_data = output_data or {}
        checkpoint.error_message = None
        checkpoint.cost = 0.1
        return checkpoint

    return create_checkpoint


@pytest.fixture
def initial_workflow_data():
    """Create initial data for starting a workflow."""
    return {
        "research_question": "Effect of aspirin on mortality in sepsis patients",
        "inclusion_criteria": ["Human RCTs", "Sepsis patients"],
        "exclusion_criteria": ["Animal studies"],
        "databases": ["pubmed", "openalex"],
    }


# ==============================================================================
# WorkflowOrchestrator Basic Tests
# ==============================================================================


class TestWorkflowOrchestratorBasics:
    """Basic tests for WorkflowOrchestrator."""

    def test_stage_order(self, mock_db):
        """Test that STAGE_ORDER contains all 12 stages."""
        orchestrator = WorkflowOrchestrator(mock_db)

        assert len(orchestrator.STAGE_ORDER) == 12
        assert orchestrator.STAGE_ORDER == [
            "search",
            "screen",
            "pdf_fetch",
            "extract",
            "rob",
            "analysis",
            "prisma",
            "tables",
            "introduction",
            "methods",
            "results",
            "discussion",
        ]

    def test_stage_executors_mapping(self, mock_db):
        """Test that all stages have executors."""
        orchestrator = WorkflowOrchestrator(mock_db)

        for stage in orchestrator.STAGE_ORDER:
            assert stage in orchestrator.STAGE_EXECUTORS
            assert orchestrator.STAGE_EXECUTORS[stage] is not None

    def test_get_executor(self, mock_db):
        """Test getting executor for a stage."""
        orchestrator = WorkflowOrchestrator(mock_db)
        mode_config = get_default_mode_config()

        executor = orchestrator._get_executor("test-123", "search", mode_config)

        assert executor is not None
        assert executor.STAGE_NAME == "search"
        assert executor.workflow_id == "test-123"

    def test_get_executor_invalid_stage(self, mock_db):
        """Test getting executor for invalid stage raises error."""
        orchestrator = WorkflowOrchestrator(mock_db)
        mode_config = get_default_mode_config()

        with pytest.raises(ValueError, match="No executor found"):
            orchestrator._get_executor("test-123", "invalid_stage", mode_config)


# ==============================================================================
# Workflow Execution Tests
# ==============================================================================


class TestWorkflowExecution:
    """Tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_start_stage(self, mock_db, initial_workflow_data):
        """Test that invalid start stage raises error."""
        orchestrator = WorkflowOrchestrator(mock_db)

        with pytest.raises(ValueError, match="Invalid stage"):
            await orchestrator.execute_workflow(
                "test-123",
                initial_workflow_data,
                start_from="invalid_stage",
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_skip_stages(
        self, mock_db, mock_workflow, initial_workflow_data
    ):
        """Test skipping stages during execution."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Create a mock executor that always succeeds
        mock_result = StageResult(success=True, output_data={"test": "data"}, cost=0.1)

        with patch.object(orchestrator, "_get_executor") as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = AsyncMock(return_value=mock_result)
            mock_get_executor.return_value = mock_executor

            with patch.object(orchestrator, "_assemble_manuscript", new_callable=AsyncMock):
                with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                    with patch.object(orchestrator, "_mark_stage_status", new_callable=AsyncMock):
                        with patch.object(
                            orchestrator, "_update_workflow_cost", new_callable=AsyncMock
                        ):
                            with patch.object(
                                orchestrator, "_update_workflow_status", new_callable=AsyncMock
                            ):
                                with patch.object(
                                    orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                                ) as mock_load:
                                    mock_load.return_value = {}
                                    result = await orchestrator.execute_workflow(
                                        "test-123",
                                        initial_workflow_data,
                                        skip_stages=["pdf_fetch", "analysis"],
                                    )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_workflow_stage_failure_needs_review(
        self, mock_db, mock_workflow, initial_workflow_data
    ):
        """Test workflow pauses when stage needs user review."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # First stage succeeds, second fails with user action needed
        call_count = 0

        async def mock_run_with_retry(input_data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return StageResult(success=True, output_data={"papers": []}, cost=0.1)
            else:
                return StageResult(
                    success=False,
                    error="Rate limit exceeded",
                    needs_user_action=True,
                    action_required="Please wait and retry",
                )

        with patch.object(orchestrator, "_get_executor") as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                with patch.object(orchestrator, "_set_needs_user_action", new_callable=AsyncMock):
                    with patch.object(
                        orchestrator, "_update_workflow_cost", new_callable=AsyncMock
                    ):
                        with patch.object(
                            orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                        ) as mock_load:
                            mock_load.return_value = {}
                            result = await orchestrator.execute_workflow(
                                "test-123",
                                initial_workflow_data,
                            )

        assert result["status"] == "needs_review"
        assert result["failed_stage"] == "screen"  # Second stage
        assert result["action_required"] == "Please wait and retry"

    @pytest.mark.asyncio
    async def test_execute_workflow_hard_failure(
        self, mock_db, mock_workflow, initial_workflow_data
    ):
        """Test workflow fails when stage has hard failure."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Stage fails without needing user action
        mock_result = StageResult(
            success=False,
            error="Critical error",
            needs_user_action=False,
        )

        with patch.object(orchestrator, "_get_executor") as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = AsyncMock(return_value=mock_result)
            mock_get_executor.return_value = mock_executor

            with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                with patch.object(orchestrator, "_update_workflow_status", new_callable=AsyncMock):
                    with patch.object(
                        orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                    ) as mock_load:
                        mock_load.return_value = {}
                        result = await orchestrator.execute_workflow(
                            "test-123",
                            initial_workflow_data,
                        )

        assert result["status"] == "failed"
        assert result["error"] == "Critical error"

    @pytest.mark.asyncio
    async def test_execute_workflow_accumulates_data(
        self, mock_db, mock_workflow, initial_workflow_data
    ):
        """Test that output data accumulates between stages."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Track accumulated data
        accumulated_inputs = []

        async def mock_run_with_retry(input_data):
            accumulated_inputs.append(dict(input_data))
            stage_num = len(accumulated_inputs)
            return StageResult(
                success=True,
                output_data={f"stage_{stage_num}_output": f"data_{stage_num}"},
                cost=0.1,
            )

        with patch.object(orchestrator, "_get_executor") as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(orchestrator, "_assemble_manuscript", new_callable=AsyncMock):
                with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                    with patch.object(orchestrator, "_mark_stage_status", new_callable=AsyncMock):
                        with patch.object(
                            orchestrator, "_update_workflow_cost", new_callable=AsyncMock
                        ):
                            with patch.object(
                                orchestrator, "_update_workflow_status", new_callable=AsyncMock
                            ):
                                with patch.object(
                                    orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                                ) as mock_load:
                                    mock_load.return_value = {}
                                    # Only run first 3 stages to verify accumulation
                                    await orchestrator.execute_workflow(
                                        "test-123",
                                        initial_workflow_data,
                                        skip_stages=[
                                            "extract",
                                            "rob",
                                            "analysis",
                                            "prisma",
                                            "tables",
                                            "introduction",
                                            "methods",
                                            "results",
                                            "discussion",
                                        ],
                                    )

        # Verify data accumulates
        assert len(accumulated_inputs) >= 2
        # Second stage should see first stage's output
        if len(accumulated_inputs) >= 2:
            assert "stage_1_output" in accumulated_inputs[1] or "search" in accumulated_inputs[1]


# ==============================================================================
# Stage Re-run Tests
# ==============================================================================


class TestStageRerun:
    """Tests for stage re-run functionality."""

    @pytest.mark.asyncio
    async def test_rerun_stage_invalid_stage(self, mock_db):
        """Test re-running invalid stage raises error."""
        orchestrator = WorkflowOrchestrator(mock_db)

        with pytest.raises(ValueError, match="Invalid stage"):
            await orchestrator.rerun_stage("test-123", "invalid_stage")

    @pytest.mark.asyncio
    async def test_rerun_stage_missing_dependencies(self, mock_db, mock_checkpoint):
        """Test re-running stage with incomplete dependencies raises error."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Only search completed, trying to rerun extract (needs search, screen, pdf_fetch)
        def get_checkpoint(wf_id, stage):
            if stage == "search":
                return mock_checkpoint("search", status="completed")
            return None

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            with pytest.raises(ValueError, match="required stage"):
                await orchestrator.rerun_stage("test-123", "extract")

    @pytest.mark.asyncio
    async def test_rerun_stage_success(self, mock_db, mock_checkpoint):
        """Test successful stage re-run."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Search completed, re-run screen
        completed_checkpoint = mock_checkpoint(
            "search", status="completed", output_data={"papers": []}
        )

        async def get_checkpoint(wf_id, stage):
            if stage == "search":
                return completed_checkpoint
            return None

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            with patch.object(
                orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = {"papers": []}

                with patch.object(orchestrator, "_get_executor") as mock_get_executor:
                    mock_executor = MagicMock()
                    mock_executor.run_with_retry = AsyncMock(
                        return_value=StageResult(success=True, output_data={"screened": 10})
                    )
                    mock_get_executor.return_value = mock_executor

                    with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                        result = await orchestrator.rerun_stage("test-123", "screen")

        assert result.success is True
        assert result.output_data["screened"] == 10

    @pytest.mark.asyncio
    async def test_rerun_stage_with_override(self, mock_db, mock_checkpoint):
        """Test re-running stage with input override."""
        orchestrator = WorkflowOrchestrator(mock_db)

        completed_checkpoint = mock_checkpoint("search", status="completed")

        async def get_checkpoint(wf_id, stage):
            if stage == "search":
                return completed_checkpoint
            return None

        captured_input = None

        async def capture_input(input_data):
            nonlocal captured_input
            captured_input = input_data
            return StageResult(success=True, output_data={})

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            with patch.object(
                orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = {"original_key": "original_value"}

                with patch.object(orchestrator, "_get_executor") as mock_get_executor:
                    mock_executor = MagicMock()
                    mock_executor.run_with_retry = capture_input
                    mock_get_executor.return_value = mock_executor

                    with patch.object(orchestrator, "_save_checkpoint", new_callable=AsyncMock):
                        await orchestrator.rerun_stage(
                            "test-123",
                            "screen",
                            input_override={"override_key": "override_value"},
                        )

        assert captured_input is not None
        assert captured_input.get("override_key") == "override_value"


# ==============================================================================
# Resume Workflow Tests
# ==============================================================================


class TestResumeWorkflow:
    """Tests for resuming workflow functionality."""

    @pytest.mark.asyncio
    async def test_resume_workflow_already_completed(self, mock_db, mock_checkpoint):
        """Test resuming already completed workflow."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # All stages completed
        async def get_checkpoint(wf_id, stage):
            return mock_checkpoint(stage, status="completed")

        with patch.object(orchestrator, "_clear_user_action", new_callable=AsyncMock):
            with patch.object(
                orchestrator, "_find_resume_point", new_callable=AsyncMock
            ) as mock_find:
                mock_find.return_value = None  # All completed

                result = await orchestrator.resume_workflow("test-123")

        assert result["status"] == "already_completed"

    @pytest.mark.asyncio
    async def test_resume_workflow_from_failed_stage(self, mock_db, mock_workflow, mock_checkpoint):
        """Test resuming from a failed stage."""
        orchestrator = WorkflowOrchestrator(mock_db)

        mock_db.execute.return_value.scalar_one.return_value = mock_workflow
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with patch.object(orchestrator, "_clear_user_action", new_callable=AsyncMock):
            with patch.object(
                orchestrator, "_find_resume_point", new_callable=AsyncMock
            ) as mock_find:
                mock_find.return_value = "screen"  # Resume from screen

                with patch.object(
                    orchestrator, "_get_workflow", new_callable=AsyncMock
                ) as mock_get_wf:
                    mock_get_wf.return_value = mock_workflow

                    with patch.object(
                        orchestrator, "execute_workflow", new_callable=AsyncMock
                    ) as mock_execute:
                        mock_execute.return_value = {"status": "completed"}

                        await orchestrator.resume_workflow("test-123")

        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args
        assert call_kwargs[1]["start_from"] == "screen"


# ==============================================================================
# Stage Status Tests
# ==============================================================================


class TestGetStageStatus:
    """Tests for getting stage status."""

    @pytest.mark.asyncio
    async def test_get_stage_status_all_pending(self, mock_db):
        """Test getting status when all stages are pending."""
        orchestrator = WorkflowOrchestrator(mock_db)

        async def get_checkpoint(wf_id, stage):
            return None  # No checkpoints

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            stages = await orchestrator.get_stage_status("test-123")

        assert len(stages) == 12
        for stage in stages:
            assert stage["status"] == "pending"
            assert stage["retry_count"] == 0
            assert stage["cost"] == 0.0

    @pytest.mark.asyncio
    async def test_get_stage_status_mixed(self, mock_db, mock_checkpoint):
        """Test getting status with mixed stage states."""
        orchestrator = WorkflowOrchestrator(mock_db)

        async def get_checkpoint(wf_id, stage):
            if stage == "search":
                return mock_checkpoint("search", status="completed")
            elif stage == "screen":
                return mock_checkpoint("screen", status="in_progress")
            elif stage == "pdf_fetch":
                return mock_checkpoint("pdf_fetch", status="failed")
            return None

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            stages = await orchestrator.get_stage_status("test-123")

        # Find specific stages
        search_status = next(s for s in stages if s["stage"] == "search")
        screen_status = next(s for s in stages if s["stage"] == "screen")
        pdf_status = next(s for s in stages if s["stage"] == "pdf_fetch")
        extract_status = next(s for s in stages if s["stage"] == "extract")

        assert search_status["status"] == "completed"
        assert screen_status["status"] == "in_progress"
        assert pdf_status["status"] == "failed"
        assert extract_status["status"] == "pending"


# ==============================================================================
# Checkpoint Management Tests
# ==============================================================================


class TestCheckpointManagement:
    """Tests for checkpoint management."""

    @pytest.mark.asyncio
    async def test_save_checkpoint_new(self, mock_db):
        """Test saving a new checkpoint."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Configure the result mock's method to return None
        result_mock = await mock_db.execute()
        result_mock.scalar_one_or_none.return_value = None

        result = StageResult(
            success=True,
            output_data={"key": "value"},
            cost=0.15,
        )

        await orchestrator._save_checkpoint("test-123", "search", result)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_update_existing(self, mock_db, mock_checkpoint):
        """Test updating an existing checkpoint."""
        orchestrator = WorkflowOrchestrator(mock_db)

        existing = mock_checkpoint("search", status="in_progress")

        # Configure the result mock's method to return the existing checkpoint
        result_mock = await mock_db.execute()
        result_mock.scalar_one_or_none.return_value = existing

        result = StageResult(
            success=True,
            output_data={"new_key": "new_value"},
            cost=0.25,
        )

        await orchestrator._save_checkpoint("test-123", "search", result)

        assert existing.status == "completed"
        assert existing.output_data == {"new_key": "new_value"}
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_checkpoint_data(self, mock_db, mock_checkpoint):
        """Test loading accumulated checkpoint data."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Create checkpoints for first 3 stages
        checkpoints = {
            "search": mock_checkpoint(
                "search", status="completed", output_data={"papers": [1, 2, 3]}
            ),
            "screen": mock_checkpoint(
                "screen", status="completed", output_data={"included": [1, 2]}
            ),
            "pdf_fetch": mock_checkpoint(
                "pdf_fetch", status="completed", output_data={"fetched": 2}
            ),
        }

        async def get_checkpoint(wf_id, stage):
            return checkpoints.get(stage)

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            # Load data up to extract stage (index 3)
            data = await orchestrator._load_checkpoint_data("test-123", 3)

        assert "papers" in data or "search" in data
        assert "included" in data or "screen" in data

    @pytest.mark.asyncio
    async def test_find_resume_point_first_incomplete(self, mock_db, mock_checkpoint):
        """Test finding first incomplete stage."""
        orchestrator = WorkflowOrchestrator(mock_db)

        async def get_checkpoint(wf_id, stage):
            if stage in ["search", "screen"]:
                return mock_checkpoint(stage, status="completed")
            elif stage == "pdf_fetch":
                return mock_checkpoint(stage, status="failed")
            return None

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            resume_point = await orchestrator._find_resume_point("test-123")

        assert resume_point == "pdf_fetch"

    @pytest.mark.asyncio
    async def test_find_resume_point_all_completed(self, mock_db, mock_checkpoint):
        """Test finding resume point when all completed."""
        orchestrator = WorkflowOrchestrator(mock_db)

        async def get_checkpoint(wf_id, stage):
            return mock_checkpoint(stage, status="completed")

        with patch.object(orchestrator, "_get_checkpoint", side_effect=get_checkpoint):
            resume_point = await orchestrator._find_resume_point("test-123")

        assert resume_point is None


# ==============================================================================
# Workflow Status Update Tests
# ==============================================================================


class TestWorkflowStatusUpdates:
    """Tests for workflow status updates."""

    @pytest.mark.asyncio
    async def test_update_workflow_status(self, mock_db, mock_workflow):
        """Test updating workflow status."""
        orchestrator = WorkflowOrchestrator(mock_db)

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._update_workflow_status("test-123", "completed")

        assert mock_workflow.status == "completed"
        assert mock_workflow.completed_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_workflow_cost(self, mock_db, mock_workflow):
        """Test updating workflow cost."""
        orchestrator = WorkflowOrchestrator(mock_db)
        mock_workflow.total_cost = 0.5

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._update_workflow_cost("test-123", 0.25)

        assert mock_workflow.total_cost == 0.75
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_needs_user_action(self, mock_db, mock_workflow):
        """Test setting needs_user_action flag."""
        orchestrator = WorkflowOrchestrator(mock_db)

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._set_needs_user_action("test-123", "Please review extraction errors")

        assert mock_workflow.needs_user_action is True
        assert mock_workflow.action_required == "Please review extraction errors"
        assert mock_workflow.status == "needs_review"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_user_action(self, mock_db, mock_workflow):
        """Test clearing user action flag."""
        orchestrator = WorkflowOrchestrator(mock_db)
        mock_workflow.needs_user_action = True
        mock_workflow.action_required = "Previous action"

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._clear_user_action("test-123")

        assert mock_workflow.needs_user_action is False
        assert mock_workflow.action_required is None
        mock_db.commit.assert_called_once()


# ==============================================================================
# Manuscript Assembly Tests
# ==============================================================================


class TestManuscriptAssembly:
    """Tests for manuscript assembly."""

    @pytest.mark.asyncio
    async def test_assemble_manuscript(self, mock_db, mock_workflow):
        """Test assembling final manuscript."""
        orchestrator = WorkflowOrchestrator(mock_db)

        accumulated_data = {
            "introduction": {
                "markdown": "# Introduction\n\nThis review examines...",
            },
            "methods": {
                "markdown": "# Methods\n\nWe searched...",
            },
            "results": {
                "markdown": "# Results\n\nWe found...",
            },
            "discussion": {
                "markdown": "# Discussion\n\nOur findings suggest...",
            },
            "figures": {},
            "tables": {},
            "references": [],
        }

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._assemble_manuscript("test-123", accumulated_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assemble_manuscript_generates_default_abstract(self, mock_db, mock_workflow):
        """Test that default abstract is generated if missing."""
        orchestrator = WorkflowOrchestrator(mock_db)
        mock_workflow.papers_screened = 100
        mock_workflow.papers_included = 15

        accumulated_data = {
            "introduction": {"content": "Intro"},
            "methods": {"content": "Methods"},
            "results": {"content": "Results"},
            "discussion": {"content": "Discussion"},
        }

        with patch.object(orchestrator, "_get_workflow", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_workflow

            await orchestrator._assemble_manuscript("test-123", accumulated_data)

        # Verify manuscript was created
        mock_db.add.assert_called_once()
        added_manuscript = mock_db.add.call_args[0][0]

        # Check abstract was generated
        assert "Background" in added_manuscript.abstract
        assert "100" in added_manuscript.abstract or "screened" in added_manuscript.abstract.lower()
