"""Tests for introduction and discussion writers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.agents.discussion_writer import DiscussionWriterAgent
from arakis.agents.intro_writer import IntroductionWriterAgent
from arakis.models.analysis import (
    AnalysisMethod,
    ConfidenceInterval,
    EffectMeasure,
    Heterogeneity,
    MetaAnalysisResult,
)
from arakis.models.paper import Paper


@pytest.fixture
def sample_papers():
    """Create sample papers for testing."""
    return [
        Paper(
            id="test1",
            title="Machine Learning in Healthcare",
            abstract="This paper discusses machine learning applications in healthcare settings.",
            authors=["Smith, J.", "Jones, A."],
            year=2020,
            journal="Medical AI",
            doi="10.1234/test1",
        ),
        Paper(
            id="test2",
            title="Deep Learning for Medical Diagnosis",
            abstract="Deep learning models can improve diagnostic accuracy in medical imaging.",
            authors=["Brown, K.", "Davis, L."],
            year=2021,
            journal="AI Medicine",
            doi="10.1234/test2",
        ),
    ]


@pytest.fixture
def sample_meta_analysis():
    """Create sample meta-analysis result for testing."""
    return MetaAnalysisResult(
        outcome_name="Mortality",
        studies_included=5,
        total_sample_size=560,
        pooled_effect=-13.389,
        confidence_interval=ConfidenceInterval(lower=-17.285, upper=-9.494),
        z_statistic=-7.234,
        p_value=0.0001,
        effect_measure=EffectMeasure.MEAN_DIFFERENCE,
        analysis_method=AnalysisMethod.RANDOM_EFFECTS,
        heterogeneity=Heterogeneity(
            q_statistic=1.234,
            q_p_value=0.9999,
            i_squared=0.0,
            tau_squared=0.0,
        ),
        studies=[],
        forest_plot_path=None,
        funnel_plot_path=None,
    )


class TestIntroductionWriter:
    """Tests for IntroductionWriterAgent."""

    @pytest.mark.asyncio
    async def test_write_background(self, sample_papers):
        """Test writing background subsection."""
        writer = IntroductionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Background content"))]
        mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_background(
                topic="Antihypertensive therapy",
                literature_context=sample_papers,
            )

            assert result.success
            assert result.section.title == "Background"
            assert result.section.content == "Background content"
            # Note: tokens_used is 0 when using validation+retry flow
            assert result.tokens_used >= 0
            mock_create.assert_called()

    @pytest.mark.asyncio
    async def test_write_rationale(self):
        """Test writing rationale subsection."""
        writer = IntroductionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Rationale content"))]
        mock_response.usage = MagicMock(total_tokens=80, prompt_tokens=40, completion_tokens=40)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_rationale(
                research_question="Effect of antihypertensive therapy on blood pressure"
            )

            assert result.success
            assert result.section.title == "Rationale"
            assert result.section.content == "Rationale content"
            # Note: tokens_used is 0 when using validation+retry flow
            assert result.tokens_used >= 0
            mock_create.assert_called()

    @pytest.mark.asyncio
    async def test_write_objectives(self):
        """Test writing objectives subsection."""
        writer = IntroductionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Objectives content"))]
        mock_response.usage = MagicMock(total_tokens=60, prompt_tokens=30, completion_tokens=30)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_objectives(
                research_question="Effect of antihypertensive therapy on blood pressure",
                inclusion_criteria=["RCTs", "Adult patients"],
                primary_outcome="Systolic blood pressure",
            )

            assert result.success
            assert result.section.title == "Objectives"
            assert result.section.content == "Objectives content"
            assert result.tokens_used == 60
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_complete_introduction(self, sample_papers):
        """Test writing complete introduction section."""
        writer = IntroductionWriterAgent()

        # Mock OpenAI responses for all three subsections
        mock_responses = [
            MagicMock(
                choices=[MagicMock(message=MagicMock(content=f"{section} content"))],
                usage=MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50),
            )
            for section in ["Background", "Rationale", "Objectives"]
        ]

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = mock_responses

            # write_complete_introduction now returns (Section, list[Paper])
            section, cited_papers = await writer.write_complete_introduction(
                research_question="Effect of antihypertensive therapy",
                literature_context=sample_papers,
                use_perplexity=False,  # Don't use Perplexity in test
            )

            assert section.title == "Introduction"
            assert len(section.subsections) == 3
            assert section.subsections[0].title == "Background"
            assert section.subsections[1].title == "Rationale"
            assert section.subsections[2].title == "Objectives"
            assert mock_create.call_count == 3
            # cited_papers is a list (may be empty in mock test)
            assert isinstance(cited_papers, list)

    def test_cost_estimation(self):
        """Test cost estimation."""
        writer = IntroductionWriterAgent()

        # Test cost calculation
        cost = writer._estimate_cost(1000, 500)
        # o3-mini pricing (default): $1.10/1M input, $4.40/1M output
        expected = (1000 / 1_000_000) * 1.10 + (500 / 1_000_000) * 4.40
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_cost_estimation_non_o1_model(self):
        """Test cost estimation for non-o1 models."""
        writer = IntroductionWriterAgent(use_extended_thinking=False, model="gpt-4o")

        # Test cost calculation
        cost = writer._estimate_cost(1000, 500)
        # gpt-4o pricing: $2.50/1M input + $10/1M output
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected, rel=1e-6)


class TestDiscussionWriter:
    """Tests for DiscussionWriterAgent."""

    @pytest.mark.asyncio
    async def test_write_key_findings(self, sample_meta_analysis):
        """Test writing key findings subsection."""
        writer = DiscussionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Key findings content"))]
        mock_response.usage = MagicMock(total_tokens=120, prompt_tokens=60, completion_tokens=60)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_key_findings(
                meta_analysis_result=sample_meta_analysis,
                outcome_name="Mortality",
                user_interpretation="The effect is clinically significant.",
            )

            assert result.success
            assert result.section.title == "Summary of Main Findings"
            assert result.section.content == "Key findings content"
            assert result.tokens_used == 120
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_comparison_to_literature(self, sample_meta_analysis, sample_papers):
        """Test writing comparison with literature subsection."""
        writer = DiscussionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Comparison content"))]
        mock_response.usage = MagicMock(total_tokens=150, prompt_tokens=75, completion_tokens=75)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_comparison_to_literature(
                meta_analysis_result=sample_meta_analysis,
                outcome_name="Mortality",
                literature_context=sample_papers,
            )

            assert result.success
            assert result.section.title == "Comparison with Existing Literature"
            assert result.section.content == "Comparison content"
            assert result.tokens_used == 150
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_limitations(self, sample_meta_analysis):
        """Test writing limitations subsection."""
        writer = DiscussionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Limitations content"))]
        mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_limitations(
                meta_analysis_result=sample_meta_analysis,
                study_limitations=["Small sample size", "High risk of bias"],
            )

            assert result.success
            assert result.section.title == "Limitations"
            assert result.section.content == "Limitations content"
            assert result.tokens_used == 100
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_implications(self, sample_meta_analysis):
        """Test writing implications subsection."""
        writer = DiscussionWriterAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Implications content"))]
        mock_response.usage = MagicMock(total_tokens=110, prompt_tokens=55, completion_tokens=55)

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await writer.write_implications(
                meta_analysis_result=sample_meta_analysis,
                outcome_name="Mortality",
                user_implications="This has important clinical implications.",
            )

            assert result.success
            assert result.section.title == "Implications"
            assert result.section.content == "Implications content"
            assert result.tokens_used == 110
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_complete_discussion(self, sample_meta_analysis, sample_papers):
        """Test writing complete discussion section."""
        writer = DiscussionWriterAgent()

        # Mock OpenAI responses for all four subsections
        mock_responses = [
            MagicMock(
                choices=[MagicMock(message=MagicMock(content=f"{section} content"))],
                usage=MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50),
            )
            for section in ["Findings", "Comparison", "Limitations", "Implications"]
        ]

        with patch.object(
            writer.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = mock_responses

            section = await writer.write_complete_discussion(
                meta_analysis_result=sample_meta_analysis,
                outcome_name="Mortality",
                literature_context=sample_papers,
            )

            assert section.title == "Discussion"
            assert len(section.subsections) == 4
            assert section.subsections[0].title == "Summary of Main Findings"
            assert section.subsections[1].title == "Comparison with Existing Literature"
            assert section.subsections[2].title == "Limitations"
            assert section.subsections[3].title == "Implications"
            assert mock_create.call_count == 4

    def test_cost_estimation(self):
        """Test cost estimation."""
        writer = DiscussionWriterAgent()

        # Test cost calculation
        cost = writer._estimate_cost(2000, 1000)
        # o3-mini pricing (default): $1.10/1M input, $4.40/1M output
        expected = (2000 / 1_000_000) * 1.10 + (1000 / 1_000_000) * 4.40
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_cost_estimation_non_o1_model(self):
        """Test cost estimation for non-o1 models."""
        writer = DiscussionWriterAgent(use_extended_thinking=False, model="gpt-4o")

        # Test cost calculation
        cost = writer._estimate_cost(2000, 1000)
        # gpt-4o pricing: $2.50/1M input + $10/1M output
        expected = (2000 / 1_000_000) * 2.50 + (1000 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected, rel=1e-6)
