"""End-to-end tests for the unified workflow system.

Tests the complete workflow from API endpoint through to completion,
verifying the 12-stage pipeline works correctly.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.workflow.orchestrator import WorkflowOrchestrator
from arakis.workflow.stages.base import StageResult


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one = MagicMock()
    result_mock.scalar_one_or_none = MagicMock()

    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    return db


@pytest.fixture
def mock_workflow():
    """Create a mock Workflow model."""
    workflow = MagicMock()
    workflow.id = "e2e-test-workflow"
    workflow.research_question = "Effect of aspirin on mortality in sepsis"
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
def workflow_input_data():
    """Create initial workflow input data."""
    return {
        "research_question": "Effect of aspirin on mortality in sepsis",
        "inclusion_criteria": ["Human RCTs", "Sepsis patients", "Mortality outcome"],
        "exclusion_criteria": ["Animal studies", "Reviews"],
        "databases": ["pubmed", "openalex"],
        "max_results_per_query": 50,
    }


# ==============================================================================
# E2E Tests
# ==============================================================================


class TestWorkflowE2E:
    """End-to-end tests for complete workflow execution."""

    @pytest.mark.asyncio
    async def test_complete_workflow_all_stages_succeed(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test a complete workflow where all 12 stages succeed."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Track which stages were executed
        executed_stages = []

        # Create mock results for each stage
        stage_outputs = {
            "search": {
                "papers_found": 100,
                "papers": [{"id": f"paper_{i}", "title": f"Paper {i}"} for i in range(100)],
            },
            "screen": {
                "total_screened": 100,
                "included": 15,
                "excluded": 85,
                "decisions": [],
                "included_paper_ids": [f"paper_{i}" for i in range(15)],
            },
            "pdf_fetch": {
                "total_fetched": 15,
                "successful": 12,
                "failed": 3,
            },
            "extract": {
                "extractions": [
                    {"paper_id": f"paper_{i}", "data": {}} for i in range(12)
                ],
            },
            "rob": {
                "n_studies": 12,
                "tool_used": "RoB 2",
                "percent_low_risk": 60.0,
            },
            "analysis": {
                "meta_analysis_feasible": True,
                "pooled_effect": -0.5,
                "forest_plot_url": "https://r2.example.com/forest.png",
            },
            "prisma": {
                "prisma_url": "https://r2.example.com/prisma.png",
            },
            "tables": {
                "study_characteristics_table": {},
                "rob_table": {},
                "grade_table": {},
            },
            "introduction": {
                "content": "Introduction text",
                "word_count": 500,
            },
            "methods": {
                "content": "Methods text",
                "word_count": 800,
            },
            "results": {
                "content": "Results text",
                "word_count": 600,
            },
            "discussion": {
                "content": "Discussion text",
                "word_count": 700,
            },
        }

        async def mock_run_with_retry(input_data):
            # Determine current stage from the context
            stage = orchestrator.STAGE_ORDER[len(executed_stages)]
            executed_stages.append(stage)
            return StageResult(
                success=True,
                output_data=stage_outputs.get(stage, {}),
                cost=0.1,
            )

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_assemble_manuscript", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_save_checkpoint", new_callable=AsyncMock
                ):
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
                                    "e2e-test-workflow",
                                    workflow_input_data,
                                )

        # Verify all 12 stages were executed
        assert len(executed_stages) == 12
        assert executed_stages == orchestrator.STAGE_ORDER

        # Verify workflow completed successfully
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_stops_on_failure(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test that workflow stops when a stage fails."""
        orchestrator = WorkflowOrchestrator(mock_db)

        executed_stages = []
        fail_at_stage = "extract"  # Stage 4

        async def mock_run_with_retry(input_data):
            stage = orchestrator.STAGE_ORDER[len(executed_stages)]
            executed_stages.append(stage)

            if stage == fail_at_stage:
                return StageResult(
                    success=False,
                    error="Extraction failed",
                    needs_user_action=True,
                    action_required="Please review extraction errors",
                )

            return StageResult(success=True, output_data={}, cost=0.1)

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_save_checkpoint", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_update_workflow_cost", new_callable=AsyncMock
                ):
                    with patch.object(
                        orchestrator, "_set_needs_user_action", new_callable=AsyncMock
                    ):
                        with patch.object(
                            orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                        ) as mock_load:
                            mock_load.return_value = {}

                            result = await orchestrator.execute_workflow(
                                "e2e-test-workflow",
                                workflow_input_data,
                            )

        # Should have executed up to and including the failed stage
        assert fail_at_stage in executed_stages
        assert len(executed_stages) == 4  # search, screen, pdf_fetch, extract

        # Workflow should be in needs_review state
        assert result["status"] == "needs_review"
        assert result["failed_stage"] == fail_at_stage

    @pytest.mark.asyncio
    async def test_workflow_resume_after_failure(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test resuming a workflow after a failure has been resolved."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Simulate resuming from extract stage
        resume_from = "extract"
        executed_stages = []

        async def mock_run_with_retry(input_data):
            stage_index = orchestrator.STAGE_ORDER.index(resume_from) + len(executed_stages)
            stage = orchestrator.STAGE_ORDER[stage_index]
            executed_stages.append(stage)
            return StageResult(success=True, output_data={}, cost=0.1)

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_assemble_manuscript", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_save_checkpoint", new_callable=AsyncMock
                ):
                    with patch.object(
                        orchestrator, "_update_workflow_cost", new_callable=AsyncMock
                    ):
                        with patch.object(
                            orchestrator, "_update_workflow_status", new_callable=AsyncMock
                        ):
                            with patch.object(
                                orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                            ) as mock_load:
                                # Simulate data from previous stages
                                mock_load.return_value = {
                                    "papers": [{"id": "paper_1"}],
                                    "included_paper_ids": ["paper_1"],
                                }

                                result = await orchestrator.execute_workflow(
                                    "e2e-test-workflow",
                                    workflow_input_data,
                                    start_from=resume_from,
                                )

        # Should only execute stages from resume point onwards
        assert executed_stages[0] == resume_from
        assert len(executed_stages) == 9  # extract through discussion

        # Workflow should complete
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_skip_stages(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test skipping specific stages during workflow execution."""
        orchestrator = WorkflowOrchestrator(mock_db)

        executed_stages = []
        skip_stages = ["analysis", "prisma"]

        async def mock_run_with_retry(input_data):
            # Find next non-skipped stage
            for stage in orchestrator.STAGE_ORDER:
                if stage not in executed_stages and stage not in skip_stages:
                    executed_stages.append(stage)
                    return StageResult(success=True, output_data={}, cost=0.1)
            return StageResult(success=True, output_data={}, cost=0.1)

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_assemble_manuscript", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_save_checkpoint", new_callable=AsyncMock
                ):
                    with patch.object(
                        orchestrator, "_mark_stage_status", new_callable=AsyncMock
                    ):
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
                                        "e2e-test-workflow",
                                        workflow_input_data,
                                        skip_stages=skip_stages,
                                    )

        # Skipped stages should not be in executed list
        for stage in skip_stages:
            assert stage not in executed_stages

        # Workflow should complete
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_data_flows_between_stages(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test that data correctly flows from one stage to the next."""
        orchestrator = WorkflowOrchestrator(mock_db)

        # Track input data received by each stage
        stage_inputs = {}

        async def mock_run_with_retry(input_data):
            stage_index = len(stage_inputs)
            stage = orchestrator.STAGE_ORDER[stage_index]
            stage_inputs[stage] = dict(input_data)

            # Return stage-specific output that should flow to next stage
            if stage == "search":
                return StageResult(
                    success=True,
                    output_data={
                        "papers": [{"id": "paper_1", "title": "Test Paper"}],
                        "papers_found": 1,
                    },
                    cost=0.1,
                )
            elif stage == "screen":
                return StageResult(
                    success=True,
                    output_data={
                        "included_paper_ids": ["paper_1"],
                        "total_screened": 1,
                    },
                    cost=0.1,
                )
            else:
                return StageResult(success=True, output_data={}, cost=0.1)

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_assemble_manuscript", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_save_checkpoint", new_callable=AsyncMock
                ):
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
                                    "e2e-test-workflow",
                                    workflow_input_data,
                                )

        # Verify data flows correctly
        # Screen stage should receive papers from search
        assert "papers" in stage_inputs.get("screen", {}) or "search" in stage_inputs.get("screen", {})

        # PDF fetch should receive included paper IDs from screen
        pdf_fetch_input = stage_inputs.get("pdf_fetch", {})
        assert "included_paper_ids" in pdf_fetch_input or "screen" in pdf_fetch_input

    @pytest.mark.asyncio
    async def test_workflow_tracks_total_cost(
        self, mock_db, mock_workflow, workflow_input_data
    ):
        """Test that workflow correctly accumulates cost across stages."""
        orchestrator = WorkflowOrchestrator(mock_db)

        stage_costs = {
            "search": 0.10,
            "screen": 0.50,
            "pdf_fetch": 0.00,
            "extract": 1.20,
            "rob": 0.00,
            "analysis": 0.20,
            "prisma": 0.00,
            "tables": 0.00,
            "introduction": 1.00,
            "methods": 0.50,
            "results": 0.50,
            "discussion": 1.00,
        }

        executed_count = 0
        total_cost_updates = []

        async def mock_run_with_retry(input_data):
            nonlocal executed_count
            stage = orchestrator.STAGE_ORDER[executed_count]
            executed_count += 1
            return StageResult(
                success=True,
                output_data={},
                cost=stage_costs[stage],
            )

        async def mock_update_cost(workflow_id, cost):
            total_cost_updates.append(cost)

        with patch.object(
            orchestrator, "_get_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_with_retry = mock_run_with_retry
            mock_get_executor.return_value = mock_executor

            with patch.object(
                orchestrator, "_assemble_manuscript", new_callable=AsyncMock
            ):
                with patch.object(
                    orchestrator, "_save_checkpoint", new_callable=AsyncMock
                ):
                    with patch.object(
                        orchestrator, "_update_workflow_cost", side_effect=mock_update_cost
                    ):
                        with patch.object(
                            orchestrator, "_update_workflow_status", new_callable=AsyncMock
                        ):
                            with patch.object(
                                orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
                            ) as mock_load:
                                mock_load.return_value = {}

                                result = await orchestrator.execute_workflow(
                                    "e2e-test-workflow",
                                    workflow_input_data,
                                )

        # Verify cost was updated for each stage
        assert len(total_cost_updates) == 12

        # Verify total cost matches expected
        expected_total = sum(stage_costs.values())
        actual_total = sum(total_cost_updates)
        assert actual_total == pytest.approx(expected_total, abs=0.01)


class TestWorkflowStageOrder:
    """Tests verifying the correct order of stage execution."""

    def test_stage_order_is_correct(self, mock_db):
        """Verify the stage order matches PRD requirements."""
        orchestrator = WorkflowOrchestrator(mock_db)

        expected_order = [
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

        assert orchestrator.STAGE_ORDER == expected_order

    def test_all_stages_have_executors(self, mock_db):
        """Verify every stage has an associated executor."""
        orchestrator = WorkflowOrchestrator(mock_db)

        for stage in orchestrator.STAGE_ORDER:
            assert stage in orchestrator.STAGE_EXECUTORS
            executor_class = orchestrator.STAGE_EXECUTORS[stage]
            assert executor_class is not None
            # Verify the class has the correct STAGE_NAME
            executor = executor_class("test", mock_db)
            assert executor.STAGE_NAME == stage


class TestWorkflowRerunCapability:
    """Tests for stage re-run functionality."""

    @pytest.mark.asyncio
    async def test_rerun_single_stage(self, mock_db, mock_workflow):
        """Test re-running a single failed stage."""
        orchestrator = WorkflowOrchestrator(mock_db)

        rerun_result = StageResult(
            success=True,
            output_data={"rerun": True, "fixed": True},
            cost=0.15,
        )

        with patch.object(
            orchestrator, "_get_checkpoint", new_callable=AsyncMock
        ) as mock_get_cp:
            # Pretend previous stages completed
            mock_cp = MagicMock()
            mock_cp.status = "completed"
            mock_get_cp.return_value = mock_cp

            with patch.object(
                orchestrator, "_load_checkpoint_data", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = {"papers": []}

                with patch.object(
                    orchestrator, "_get_executor"
                ) as mock_get_exec:
                    mock_executor = MagicMock()
                    mock_executor.run_with_retry = AsyncMock(return_value=rerun_result)
                    mock_get_exec.return_value = mock_executor

                    with patch.object(
                        orchestrator, "_save_checkpoint", new_callable=AsyncMock
                    ):
                        result = await orchestrator.rerun_stage(
                            "e2e-test-workflow",
                            "screen",
                        )

        assert result.success is True
        assert result.output_data["rerun"] is True

    @pytest.mark.asyncio
    async def test_rerun_validates_dependencies(self, mock_db):
        """Test that rerun validates required stages are completed."""
        orchestrator = WorkflowOrchestrator(mock_db)

        async def get_checkpoint(wf_id, stage):
            if stage == "search":
                cp = MagicMock()
                cp.status = "completed"
                return cp
            elif stage == "screen":
                cp = MagicMock()
                cp.status = "failed"  # Not completed
                return cp
            return None

        with patch.object(
            orchestrator, "_get_checkpoint", side_effect=get_checkpoint
        ):
            # Trying to rerun pdf_fetch should fail because screen isn't completed
            with pytest.raises(ValueError, match="required stage"):
                await orchestrator.rerun_stage("e2e-test-workflow", "pdf_fetch")


class TestWorkflowNoScreeningLimit:
    """Tests verifying the 50-paper screening limit has been removed."""

    @pytest.mark.asyncio
    async def test_screens_all_papers_no_limit(self, mock_db, mock_workflow):
        """Verify that screening processes ALL papers without the old 50-paper limit."""
        from arakis.workflow.stages.screen import ScreenStageExecutor

        executor = ScreenStageExecutor("test-123", mock_db)

        # Create more than 50 papers to verify no limit
        papers = [
            {
                "id": f"paper_{i}",
                "title": f"Paper {i}",
                "abstract": "Test abstract",
                "year": 2023,
                "source": "pubmed",
            }
            for i in range(150)  # Well over the old 50-paper limit
        ]

        # Configure mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        # Mock screener
        mock_decisions = [
            MagicMock(
                paper_id=f"paper_{i}",
                status=MagicMock(value="INCLUDE" if i < 75 else "EXCLUDE"),
                reason="Test",
                confidence=0.9,
                matched_inclusion=["Criteria"],
                matched_exclusion=[],
                is_conflict=False,
            )
            for i in range(150)
        ]

        mock_summary = {"included": 75, "excluded": 75, "maybe": 0, "conflicts": 0}

        with patch.object(
            executor.screener, "screen_batch", new_callable=AsyncMock
        ) as mock_screen:
            mock_screen.return_value = mock_decisions

            with patch.object(
                executor.screener, "summarize_screening"
            ) as mock_summarize:
                mock_summarize.return_value = mock_summary

                result = await executor.execute({
                    "papers": papers,
                    "inclusion_criteria": ["Human RCTs"],
                    "exclusion_criteria": ["Animal studies"],
                })

        # CRITICAL: Verify ALL 150 papers were screened
        assert result.success is True
        assert result.output_data["total_screened"] == 150
        assert len(result.output_data["decisions"]) == 150
