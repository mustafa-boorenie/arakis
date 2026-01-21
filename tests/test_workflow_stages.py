"""Tests for workflow stage executors.

Tests the 12 workflow stages and their base class:
- BaseStageExecutor: retry logic, checkpointing, R2 upload
- SearchStageExecutor: multi-database search
- ScreenStageExecutor: paper screening (no 50-paper limit)
- PDFFetchStageExecutor: PDF download and text extraction
- ExtractStageExecutor: structured data extraction
- RiskOfBiasStageExecutor: RoB assessment
- AnalysisStageExecutor: meta-analysis
- PRISMAStageExecutor: flow diagram
- TablesStageExecutor: table generation
- IntroductionStageExecutor: intro writing
- MethodsStageExecutor: methods writing
- ResultsStageExecutor: results writing
- DiscussionStageExecutor: discussion writing
"""

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from arakis.workflow.stages.base import BaseStageExecutor, StageResult
from arakis.workflow.stages.search import SearchStageExecutor
from arakis.workflow.stages.screen import ScreenStageExecutor
from arakis.workflow.stages.pdf_fetch import PDFFetchStageExecutor
from arakis.workflow.stages.extract import ExtractStageExecutor
from arakis.workflow.stages.rob import RiskOfBiasStageExecutor
from arakis.workflow.stages.analysis import AnalysisStageExecutor
from arakis.workflow.stages.prisma import PRISMAStageExecutor
from arakis.workflow.stages.tables import TablesStageExecutor
from arakis.workflow.stages.introduction import IntroductionStageExecutor
from arakis.workflow.stages.methods import MethodsStageExecutor
from arakis.workflow.stages.results import ResultsStageExecutor
from arakis.workflow.stages.discussion import DiscussionStageExecutor


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()

    # Create a result mock for execute
    result_mock = MagicMock()
    result_mock.scalar_one = MagicMock()
    result_mock.scalar_one_or_none = MagicMock()

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
    return workflow


@pytest.fixture
def mock_checkpoint():
    """Create a mock WorkflowStageCheckpoint model."""
    checkpoint = MagicMock()
    checkpoint.workflow_id = "test-workflow-123"
    checkpoint.stage = "search"
    checkpoint.status = "pending"
    checkpoint.started_at = None
    checkpoint.completed_at = None
    checkpoint.retry_count = 0
    checkpoint.output_data = None
    checkpoint.error_message = None
    checkpoint.cost = 0.0
    return checkpoint


@pytest.fixture
def sample_search_result():
    """Create sample search results for testing."""
    return {
        "papers_found": 25,
        "duplicates_removed": 5,
        "records_identified": {"pubmed": 15, "openalex": 15},
        "papers": [
            {
                "id": f"paper_{i}",
                "title": f"Paper {i}: Effect of aspirin on sepsis",
                "doi": f"10.1234/paper{i}",
                "pmid": f"1234567{i}",
                "year": 2023,
                "source": "pubmed",
                "abstract": f"This study investigates aspirin effects. Methods: RCT with {100 + i * 10} patients."
            }
            for i in range(25)
        ],
    }


@pytest.fixture
def sample_screening_result():
    """Create sample screening results for testing."""
    return {
        "total_screened": 25,
        "included": 10,
        "excluded": 12,
        "maybe": 3,
        "conflicts": 2,
        "decisions": [
            {
                "paper_id": f"paper_{i}",
                "status": "INCLUDE" if i < 10 else "EXCLUDE",
                "reason": "Meets criteria" if i < 10 else "Not relevant",
                "confidence": 0.9,
                "matched_inclusion": ["Human RCTs"] if i < 10 else [],
                "matched_exclusion": [] if i < 10 else ["Reviews"],
                "is_conflict": False,
            }
            for i in range(25)
        ],
        "included_paper_ids": [f"paper_{i}" for i in range(10)],
    }


@pytest.fixture
def sample_extractions():
    """Create sample extraction data for testing."""
    return [
        {
            "paper_id": f"paper_{i}",
            "schema_name": "rct",
            "extraction_method": "triple_review",
            "data": {
                "study_design": "RCT",
                "sample_size_total": 100 + i * 20,
                "sample_size_intervention": 50 + i * 10,
                "sample_size_control": 50 + i * 10,
                "intervention_mean": 5.0 + i * 0.5,
                "intervention_sd": 2.0,
                "control_mean": 8.0 + i * 0.3,
                "control_sd": 2.5,
                "primary_outcome": "30-day mortality",
            },
            "confidence": {
                "study_design": 0.95,
                "sample_size_total": 0.90,
            },
            "extraction_quality": 0.88,
            "needs_human_review": False,
        }
        for i in range(5)
    ]


# ==============================================================================
# StageResult Tests
# ==============================================================================


class TestStageResult:
    """Tests for StageResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful stage result."""
        result = StageResult(
            success=True,
            output_data={"papers_found": 25},
            cost=0.15,
        )

        assert result.success is True
        assert result.output_data == {"papers_found": 25}
        assert result.cost == 0.15
        assert result.error is None
        assert result.needs_user_action is False
        assert result.action_required is None

    def test_failed_result(self):
        """Test creating a failed stage result."""
        result = StageResult(
            success=False,
            error="API rate limit exceeded",
            needs_user_action=True,
            action_required="Please wait and retry",
        )

        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.needs_user_action is True
        assert result.action_required == "Please wait and retry"

    def test_to_dict(self):
        """Test serializing StageResult to dictionary."""
        result = StageResult(
            success=True,
            output_data={"key": "value"},
            cost=0.25,
            error=None,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["output_data"] == {"key": "value"}
        assert d["cost"] == 0.25
        assert d["error"] is None
        assert d["needs_user_action"] is False
        assert d["action_required"] is None


# ==============================================================================
# BaseStageExecutor Tests
# ==============================================================================


class TestBaseStageExecutor:
    """Tests for BaseStageExecutor base class."""

    def test_is_retryable_error_rate_limit(self):
        """Test that rate limit errors are retryable."""
        # Create a concrete subclass for testing
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", MagicMock())

        # Test various rate limit patterns
        assert executor._is_retryable_error("Rate limit exceeded") is True
        assert executor._is_retryable_error("Error 429: Too many requests") is True
        assert executor._is_retryable_error("rate_limit_error") is True

    def test_is_retryable_error_timeout(self):
        """Test that timeout errors are retryable."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", MagicMock())

        assert executor._is_retryable_error("Connection timeout") is True
        assert executor._is_retryable_error("Request timed out") is True

    def test_is_retryable_error_server_errors(self):
        """Test that server errors are retryable."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", MagicMock())

        assert executor._is_retryable_error("Error 500: Internal server error") is True
        assert executor._is_retryable_error("Error 502: Bad gateway") is True
        assert executor._is_retryable_error("Error 503: Service unavailable") is True

    def test_is_retryable_error_non_retryable(self):
        """Test that client errors are not retryable."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", MagicMock())

        assert executor._is_retryable_error("Invalid API key") is False
        assert executor._is_retryable_error("Missing required field") is False
        assert executor._is_retryable_error(None) is False

    @pytest.mark.asyncio
    async def test_run_with_retry_success_first_attempt(self, mock_db):
        """Test run_with_retry succeeds on first attempt."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                return StageResult(success=True, output_data={"test": "data"})
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        result = await executor.run_with_retry({"input": "data"})

        assert result.success is True
        assert result.output_data == {"test": "data"}

    @pytest.mark.asyncio
    async def test_run_with_retry_success_after_retries(self, mock_db):
        """Test run_with_retry succeeds after transient failures."""
        attempt_count = 0

        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            INITIAL_RETRY_DELAY = 0.01  # Fast retry for tests

            async def execute(self, input_data):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    return StageResult(success=False, error="Rate limit exceeded")
                return StageResult(success=True, output_data={"attempts": attempt_count})

            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        result = await executor.run_with_retry({"input": "data"})

        assert result.success is True
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_run_with_retry_fails_after_max_retries(self, mock_db):
        """Test run_with_retry fails after max retries."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            MAX_RETRIES = 3
            INITIAL_RETRY_DELAY = 0.01

            async def execute(self, input_data):
                return StageResult(success=False, error="Connection timeout")

            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        result = await executor.run_with_retry({"input": "data"})

        assert result.success is False
        assert result.needs_user_action is True
        assert "3 attempts" in result.action_required
        assert "Connection timeout" in result.error

    @pytest.mark.asyncio
    async def test_run_with_retry_non_retryable_error(self, mock_db):
        """Test run_with_retry fails immediately for non-retryable errors."""
        attempt_count = 0

        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            INITIAL_RETRY_DELAY = 0.01

            async def execute(self, input_data):
                nonlocal attempt_count
                attempt_count += 1
                return StageResult(success=False, error="Invalid API key")

            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        result = await executor.run_with_retry({"input": "data"})

        assert result.success is False
        assert attempt_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_save_checkpoint_creates_new(self, mock_db, mock_checkpoint):
        """Test save_checkpoint creates a new checkpoint."""
        # Configure the result mock's method to return None
        result_mock = await mock_db.execute()
        result_mock.scalar_one_or_none.return_value = None

        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        checkpoint = await executor.save_checkpoint(
            status="in_progress",
            output_data={"key": "value"},
            cost=0.15,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_updates_existing(self, mock_db, mock_checkpoint):
        """Test save_checkpoint updates an existing checkpoint."""
        # Configure the result mock's method to return the checkpoint
        result_mock = await mock_db.execute()
        result_mock.scalar_one_or_none.return_value = mock_checkpoint

        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)
        await executor.save_checkpoint(
            status="completed",
            output_data={"key": "value"},
            cost=0.15,
        )

        assert mock_checkpoint.status == "completed"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_figure_to_r2(self, mock_db):
        """Test uploading a figure to R2."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)

        # Mock storage client
        mock_storage = MagicMock()
        mock_storage.upload_bytes.return_value = MagicMock(
            success=True,
            url="https://r2.example.com/workflows/test-123/figures/forest_plot.png",
        )
        executor._storage_client = mock_storage

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png content")
            temp_path = f.name

        try:
            url = await executor.upload_figure_to_r2(
                local_path=temp_path,
                figure_type="forest_plot",
                title="Forest Plot",
                caption="Meta-analysis forest plot",
            )

            assert "forest_plot" in url
            mock_storage.upload_bytes.assert_called_once()
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_save_table(self, mock_db):
        """Test saving a table to the database."""
        class TestExecutor(BaseStageExecutor):
            STAGE_NAME = "test"
            async def execute(self, input_data):
                pass
            def get_required_stages(self):
                return []

        executor = TestExecutor("test-123", mock_db)

        table = await executor.save_table(
            table_type="study_characteristics",
            headers=["Study", "N", "Outcome"],
            rows=[["Smith 2023", "100", "Positive"]],
            title="Table 1: Study Characteristics",
            caption="Characteristics of included studies",
            footnotes=["N = sample size"],
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ==============================================================================
# SearchStageExecutor Tests
# ==============================================================================


class TestSearchStageExecutor:
    """Tests for SearchStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = SearchStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "search"

    def test_required_stages(self):
        """Test that search has no required stages."""
        executor = SearchStageExecutor("test-123", MagicMock())
        assert executor.get_required_stages() == []

    @pytest.mark.asyncio
    async def test_execute_missing_research_question(self, mock_db):
        """Test execute fails without research question."""
        executor = SearchStageExecutor("test-123", mock_db)

        result = await executor.execute({"databases": ["pubmed"]})

        assert result.success is False
        assert "research_question" in result.error

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_db, mock_workflow):
        """Test successful search execution."""
        # Setup mock workflow retrieval - configure result mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        executor = SearchStageExecutor("test-123", mock_db)

        # Mock the SearchOrchestrator
        mock_search_result = MagicMock()
        mock_search_result.papers = [
            MagicMock(
                id="paper_1",
                title="Paper 1",
                doi="10.1234/paper1",
                pmid="12345671",
                year=2023,
                source=MagicMock(value="pubmed"),
                abstract="Test abstract",
            )
        ]
        mock_search_result.prisma_flow = MagicMock(
            duplicates_removed=5,
            records_identified={"pubmed": 10},
        )

        with patch.object(
            executor.orchestrator,
            "comprehensive_search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_search_result

            result = await executor.execute({
                "research_question": "Effect of aspirin on mortality",
                "databases": ["pubmed"],
            })

            assert result.success is True
            assert result.output_data["papers_found"] == 1
            assert result.output_data["duplicates_removed"] == 5
            assert len(result.output_data["papers"]) == 1
            assert result.cost > 0


# ==============================================================================
# ScreenStageExecutor Tests
# ==============================================================================


class TestScreenStageExecutor:
    """Tests for ScreenStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = ScreenStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "screen"

    def test_required_stages(self):
        """Test that screen requires search."""
        executor = ScreenStageExecutor("test-123", MagicMock())
        assert executor.get_required_stages() == ["search"]

    @pytest.mark.asyncio
    async def test_execute_no_papers(self, mock_db):
        """Test execute fails with no papers."""
        executor = ScreenStageExecutor("test-123", mock_db)

        result = await executor.execute({
            "papers": [],
            "inclusion_criteria": ["Human RCTs"],
        })

        assert result.success is False
        assert "No papers" in result.error

    @pytest.mark.asyncio
    async def test_execute_missing_criteria(self, mock_db):
        """Test execute fails without inclusion criteria."""
        executor = ScreenStageExecutor("test-123", mock_db)

        result = await executor.execute({
            "papers": [{"id": "paper_1", "title": "Test"}],
            "inclusion_criteria": [],
        })

        assert result.success is False
        assert "inclusion_criteria" in result.error

    @pytest.mark.asyncio
    async def test_execute_success_no_limit(self, mock_db, mock_workflow):
        """Test successful screening with NO 50-paper limit."""
        # Setup mock workflow retrieval - configure result mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        executor = ScreenStageExecutor("test-123", mock_db)

        # Create 100 papers to test NO LIMIT
        papers = [
            {
                "id": f"paper_{i}",
                "title": f"Paper {i}",
                "abstract": "Test abstract",
                "year": 2023,
                "source": "pubmed",
            }
            for i in range(100)  # More than old 50-paper limit
        ]

        # Mock the ScreeningAgent
        mock_decisions = [
            MagicMock(
                paper_id=f"paper_{i}",
                status=MagicMock(value="INCLUDE" if i < 50 else "EXCLUDE"),
                reason="Test",
                confidence=0.9,
                matched_inclusion=["Criteria"],
                matched_exclusion=[],
                is_conflict=False,
            )
            for i in range(100)
        ]

        mock_summary = {"included": 50, "excluded": 50, "maybe": 0, "conflicts": 0}

        with patch.object(
            executor.screener,
            "screen_batch",
            new_callable=AsyncMock,
        ) as mock_screen:
            mock_screen.return_value = mock_decisions

            with patch.object(
                executor.screener,
                "summarize_screening",
            ) as mock_summarize:
                mock_summarize.return_value = mock_summary

                result = await executor.execute({
                    "papers": papers,
                    "inclusion_criteria": ["Human RCTs"],
                    "exclusion_criteria": ["Animal studies"],
                })

                assert result.success is True
                # CRITICAL: Verify ALL 100 papers were screened (no 50-paper limit)
                assert result.output_data["total_screened"] == 100
                assert result.output_data["included"] == 50
                assert len(result.output_data["decisions"]) == 100


# ==============================================================================
# RiskOfBiasStageExecutor Tests
# ==============================================================================


class TestRiskOfBiasStageExecutor:
    """Tests for RiskOfBiasStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = RiskOfBiasStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "rob"

    def test_required_stages(self):
        """Test that RoB requires extraction."""
        executor = RiskOfBiasStageExecutor("test-123", MagicMock())
        assert executor.get_required_stages() == ["search", "screen", "pdf_fetch", "extract"]

    @pytest.mark.asyncio
    async def test_execute_no_extractions(self, mock_db):
        """Test execute with no extractions returns success."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        executor = RiskOfBiasStageExecutor("test-123", mock_db)

        result = await executor.execute({
            "extractions": [],
            "schema_used": "rct",
        })

        assert result.success is True
        assert result.output_data["n_studies"] == 0

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_db, mock_workflow, sample_extractions):
        """Test successful RoB assessment."""
        # Setup mock workflow retrieval - configure result mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        executor = RiskOfBiasStageExecutor("test-123", mock_db)

        # Mock RoB assessor
        mock_rob_summary = MagicMock()
        mock_rob_summary.n_studies = 5
        mock_rob_summary.tool = MagicMock(value="RoB 2")
        mock_rob_summary.percent_low_risk = 60.0
        mock_rob_summary.percent_high_risk = 20.0
        mock_rob_summary.percent_unclear = 20.0
        mock_rob_summary.assessments = [
            MagicMock(
                study_id=f"paper_{i}",
                overall_judgment=MagicMock(value="Low"),
                domains=[
                    MagicMock(domain_name="Randomization", judgment=MagicMock(value="Low"), support="Good")
                ],
            )
            for i in range(5)
        ]

        mock_table = MagicMock()
        mock_table.headers = ["Study", "D1", "D2", "Overall"]
        mock_table.rows = [["Study 1", "Low", "Low", "Low"]]
        mock_table.title = "Risk of Bias Assessment"
        mock_table.caption = "RoB 2 assessment"
        mock_table.footnotes = []

        # Mock the internal method that converts extractions to avoid complex object creation
        with patch.object(
            executor, "update_workflow_stage", new_callable=AsyncMock
        ):
            with patch.object(
                executor, "save_checkpoint", new_callable=AsyncMock
            ):
                with patch.object(
                    executor.assessor,
                    "assess_studies",
                ) as mock_assess:
                    mock_assess.return_value = mock_rob_summary

                    with patch.object(
                        executor.table_generator,
                        "generate_table",
                    ) as mock_gen_table:
                        mock_gen_table.return_value = mock_table

                        with patch.object(
                            executor, "save_table", new_callable=AsyncMock
                        ):
                            # Patch the ExtractionResult creation
                            with patch(
                                "arakis.workflow.stages.rob.ExtractionResult"
                            ) as mock_er_class:
                                mock_er = MagicMock()
                                mock_er.extractions = []
                                mock_er_class.return_value = mock_er

                                result = await executor.execute({
                                    "extractions": sample_extractions,
                                    "schema_used": "rct",
                                })

                                assert result.success is True
                                assert result.output_data["n_studies"] == 5
                                assert result.output_data["tool_used"] == "RoB 2"
                                assert result.output_data["percent_low_risk"] == 60.0


# ==============================================================================
# AnalysisStageExecutor Tests
# ==============================================================================


class TestAnalysisStageExecutor:
    """Tests for AnalysisStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = AnalysisStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "analysis"

    def test_required_stages(self):
        """Test that analysis requires RoB."""
        executor = AnalysisStageExecutor("test-123", MagicMock())
        assert "rob" in executor.get_required_stages()

    @pytest.mark.asyncio
    async def test_execute_no_extractions(self, mock_db):
        """Test execute with no extractions."""
        executor = AnalysisStageExecutor("test-123", mock_db)

        result = await executor.execute({
            "extractions": [],
        })

        assert result.success is True
        assert result.output_data["meta_analysis_feasible"] is False

    @pytest.mark.asyncio
    async def test_execute_insufficient_studies(self, mock_db, mock_workflow):
        """Test execute with insufficient studies for meta-analysis."""
        # Setup mock workflow retrieval - configure result mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        executor = AnalysisStageExecutor("test-123", mock_db)

        # Only 1 study
        extractions = [
            {
                "paper_id": "paper_1",
                "data": {
                    "sample_size_intervention": 50,
                    "sample_size_control": 50,
                    "intervention_mean": 5.0,
                    "intervention_sd": 2.0,
                    "control_mean": 8.0,
                    "control_sd": 2.5,
                },
            }
        ]

        result = await executor.execute({"extractions": extractions})

        assert result.success is True
        assert result.output_data["meta_analysis_feasible"] is False
        assert "Narrative synthesis" in result.output_data.get("recommendation", "")

    @pytest.mark.asyncio
    async def test_execute_meta_analysis_success(self, mock_db, mock_workflow, sample_extractions):
        """Test successful meta-analysis execution."""
        # Setup mock workflow retrieval - configure result mock
        result_mock = await mock_db.execute()
        result_mock.scalar_one.return_value = mock_workflow
        result_mock.scalar_one_or_none.return_value = None

        executor = AnalysisStageExecutor("test-123", mock_db)

        # Mock meta-analysis engine
        mock_meta_result = MagicMock()
        mock_meta_result.studies_included = 5
        mock_meta_result.total_sample_size = 500
        mock_meta_result.pooled_effect = -0.5
        mock_meta_result.confidence_interval = MagicMock(lower=-0.8, upper=-0.2)
        mock_meta_result.p_value = 0.001
        mock_meta_result.is_significant = True
        mock_meta_result.has_high_heterogeneity = False
        mock_meta_result.heterogeneity = MagicMock(
            i_squared=30.0,
            tau_squared=0.05,
            q_statistic=5.7,
            q_p_value=0.22,
        )
        mock_meta_result.individual_studies = [
            MagicMock(study_id=f"paper_{i}", effect=-0.5 + i * 0.1, weight=20.0)
            for i in range(5)
        ]

        # Mock visualization
        mock_storage = MagicMock()
        mock_storage.upload_bytes.return_value = MagicMock(
            success=True,
            url="https://r2.example.com/forest_plot.png",
        )
        executor._storage_client = mock_storage

        with patch.object(
            executor.meta_engine,
            "calculate_pooled_effect",
        ) as mock_calc:
            mock_calc.return_value = mock_meta_result

            with patch.object(
                executor.meta_engine,
                "leave_one_out_analysis",
            ) as mock_loo:
                mock_loo.return_value = []

                with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                    mock_tmpdir.return_value.__enter__.return_value = "/tmp/test"

                    with patch(
                        "arakis.workflow.stages.analysis.VisualizationGenerator"
                    ) as mock_viz_class:
                        mock_viz = MagicMock()
                        mock_viz.create_forest_plot.return_value = "/tmp/test/forest.png"
                        mock_viz.create_funnel_plot.return_value = "/tmp/test/funnel.png"
                        mock_viz_class.return_value = mock_viz

                        # Mock file read for upload
                        with patch("builtins.open", MagicMock()):
                            result = await executor.execute({
                                "extractions": sample_extractions,
                                "outcome_name": "Mortality",
                            })

        assert result.success is True
        assert result.output_data["meta_analysis_feasible"] is True
        assert result.output_data["pooled_effect"] == -0.5
        assert result.output_data["is_significant"] is True


# ==============================================================================
# IntroductionStageExecutor Tests
# ==============================================================================


class TestIntroductionStageExecutor:
    """Tests for IntroductionStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = IntroductionStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "introduction"

    def test_required_stages(self):
        """Test introduction required stages."""
        executor = IntroductionStageExecutor("test-123", MagicMock())
        required = executor.get_required_stages()
        # Introduction only requires search according to actual implementation
        assert "search" in required


# ==============================================================================
# TablesStageExecutor Tests
# ==============================================================================


class TestTablesStageExecutor:
    """Tests for TablesStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = TablesStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "tables"

    def test_required_stages(self):
        """Test tables required stages."""
        executor = TablesStageExecutor("test-123", MagicMock())
        required = executor.get_required_stages()
        assert "analysis" in required
        assert "rob" in required


# ==============================================================================
# PRISMAStageExecutor Tests
# ==============================================================================


class TestPRISMAStageExecutor:
    """Tests for PRISMAStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = PRISMAStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "prisma"

    def test_required_stages(self):
        """Test PRISMA required stages."""
        executor = PRISMAStageExecutor("test-123", MagicMock())
        required = executor.get_required_stages()
        assert "screen" in required


# ==============================================================================
# MethodsStageExecutor Tests
# ==============================================================================


class TestMethodsStageExecutor:
    """Tests for MethodsStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = MethodsStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "methods"


# ==============================================================================
# ResultsStageExecutor Tests
# ==============================================================================


class TestResultsStageExecutor:
    """Tests for ResultsStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = ResultsStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "results"


# ==============================================================================
# DiscussionStageExecutor Tests
# ==============================================================================


class TestDiscussionStageExecutor:
    """Tests for DiscussionStageExecutor."""

    def test_stage_name(self):
        """Test that stage name is correctly set."""
        executor = DiscussionStageExecutor("test-123", MagicMock())
        assert executor.STAGE_NAME == "discussion"

    def test_required_stages(self):
        """Test discussion required stages."""
        executor = DiscussionStageExecutor("test-123", MagicMock())
        required = executor.get_required_stages()
        assert "results" in required
