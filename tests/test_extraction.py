"""Tests for data extraction functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.agents.extractor import DataExtractionAgent
from arakis.models.extraction import (
    ExtractedData,
    ExtractionField,
    ExtractionMethod,
    ExtractionSchema,
    FieldType,
)
from arakis.models.paper import Paper, PaperSource


@pytest.fixture
def sample_paper():
    """Create a sample RCT paper for testing."""
    return Paper(
        id="test_rct_001",
        title="Effect of Drug X on Blood Pressure: A Randomized Controlled Trial",
        abstract=(
            "Background: Hypertension affects millions worldwide. "
            "Methods: We conducted a double-blind RCT with 120 participants (60 intervention, 60 control). "
            "Participants received either Drug X (10mg daily) or placebo for 12 weeks. "
            "Primary outcome was change in systolic blood pressure. "
            "Results: The intervention group showed a mean reduction of 15 mmHg (SD=5) "
            "compared to 3 mmHg (SD=4) in the control group (p<0.001). "
            "Conclusion: Drug X significantly reduces blood pressure."
        ),
        authors=[],
        year=2023,
        source=PaperSource.PUBMED,
    )


@pytest.fixture
def sample_schema():
    """Create a sample extraction schema for RCTs."""
    return ExtractionSchema(
        name="Test RCT Schema",
        description="Schema for testing RCT extraction",
        fields=[
            ExtractionField(
                name="study_design",
                description="Type of study design",
                field_type=FieldType.CATEGORICAL,
                required=True,
                validation_rules={
                    "allowed_values": ["RCT", "cohort", "case-control", "cross-sectional"]
                },
            ),
            ExtractionField(
                name="sample_size",
                description="Total number of participants",
                field_type=FieldType.NUMERIC,
                required=True,
                validation_rules={"min": 1, "max": 100000},
            ),
            ExtractionField(
                name="intervention_group_n",
                description="Number in intervention group",
                field_type=FieldType.NUMERIC,
                required=False,
                validation_rules={"min": 1},
            ),
            ExtractionField(
                name="control_group_n",
                description="Number in control group",
                field_type=FieldType.NUMERIC,
                required=False,
                validation_rules={"min": 1},
            ),
            ExtractionField(
                name="primary_outcome",
                description="Primary outcome measured",
                field_type=FieldType.TEXT,
                required=True,
            ),
            ExtractionField(
                name="intervention_description",
                description="Description of the intervention",
                field_type=FieldType.TEXT,
                required=True,
            ),
        ],
        study_types=["RCT"],
    )


class TestExtractionField:
    """Tests for ExtractionField validation."""

    def test_numeric_validation_success(self):
        """Test numeric field validation with valid value."""
        field = ExtractionField(
            name="age",
            description="Participant age",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 0, "max": 120},
        )

        is_valid, error = field.validate(45)
        assert is_valid
        assert error is None

    def test_numeric_validation_below_min(self):
        """Test numeric field validation with value below minimum."""
        field = ExtractionField(
            name="age",
            description="Participant age",
            field_type=FieldType.NUMERIC,
            validation_rules={"min": 18},
        )

        is_valid, error = field.validate(15)
        assert not is_valid
        assert "below minimum" in error

    def test_numeric_validation_above_max(self):
        """Test numeric field validation with value above maximum."""
        field = ExtractionField(
            name="sample_size",
            description="Study sample size",
            field_type=FieldType.NUMERIC,
            validation_rules={"max": 10000},
        )

        is_valid, error = field.validate(15000)
        assert not is_valid
        assert "exceeds maximum" in error

    def test_categorical_validation_success(self):
        """Test categorical field validation with allowed value."""
        field = ExtractionField(
            name="study_design",
            description="Study design type",
            field_type=FieldType.CATEGORICAL,
            validation_rules={"allowed_values": ["RCT", "cohort", "case-control"]},
        )

        is_valid, error = field.validate("RCT")
        assert is_valid
        assert error is None

    def test_categorical_validation_invalid(self):
        """Test categorical field validation with disallowed value."""
        field = ExtractionField(
            name="study_design",
            description="Study design type",
            field_type=FieldType.CATEGORICAL,
            validation_rules={"allowed_values": ["RCT", "cohort"]},
        )

        is_valid, error = field.validate("case-control")
        assert not is_valid
        assert "must be one of" in error

    def test_required_field_missing(self):
        """Test validation for missing required field."""
        field = ExtractionField(
            name="sample_size",
            description="Total participants",
            field_type=FieldType.NUMERIC,
            required=True,
        )

        is_valid, error = field.validate(None)
        assert not is_valid
        assert "required" in error

    def test_optional_field_missing(self):
        """Test validation for missing optional field."""
        field = ExtractionField(
            name="follow_up_duration",
            description="Follow-up period",
            field_type=FieldType.NUMERIC,
            required=False,
        )

        is_valid, error = field.validate(None)
        assert is_valid
        assert error is None


class TestExtractionSchema:
    """Tests for ExtractionSchema."""

    def test_required_fields(self, sample_schema):
        """Test getting required fields."""
        required = sample_schema.required_fields
        assert (
            len(required) == 4
        )  # study_design, sample_size, primary_outcome, intervention_description
        assert all(f.required for f in required)

    def test_optional_fields(self, sample_schema):
        """Test getting optional fields."""
        optional = sample_schema.optional_fields
        assert len(optional) == 2  # intervention_group_n, control_group_n
        assert all(not f.required for f in optional)

    def test_get_field_exists(self, sample_schema):
        """Test getting field by name."""
        field = sample_schema.get_field("sample_size")
        assert field is not None
        assert field.name == "sample_size"
        assert field.field_type == FieldType.NUMERIC

    def test_get_field_not_exists(self, sample_schema):
        """Test getting non-existent field."""
        field = sample_schema.get_field("nonexistent_field")
        assert field is None

    def test_schema_validation_success(self, sample_schema):
        """Test schema validation with valid schema."""
        errors = sample_schema.validate()
        assert len(errors) == 0

    def test_schema_validation_no_fields(self):
        """Test schema validation with no fields."""
        schema = ExtractionSchema(
            name="Empty Schema",
            description="Test schema",
            fields=[],
        )

        errors = schema.validate()
        assert len(errors) > 0
        assert any("at least one field" in e for e in errors)


class TestDataExtractionAgent:
    """Tests for DataExtractionAgent."""

    @pytest.mark.asyncio
    async def test_extract_single_paper(self, sample_paper, sample_schema):
        """Test extracting data from a single paper."""
        agent = DataExtractionAgent()

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="extract_data",
                    arguments='{"extractions": [{"field_name": "study_design", "value": "RCT", "confidence": 1.0, "reasoning": "States randomized controlled trial"}, {"field_name": "sample_size", "value": 120, "confidence": 1.0, "reasoning": "120 participants mentioned"}, {"field_name": "intervention_group_n", "value": 60, "confidence": 0.9}, {"field_name": "control_group_n", "value": 60, "confidence": 0.9}, {"field_name": "primary_outcome", "value": "change in systolic blood pressure", "confidence": 1.0}, {"field_name": "intervention_description", "value": "Drug X 10mg daily for 12 weeks", "confidence": 0.95}]}',
                )
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)

        with patch.object(agent, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            # Extract with single-pass mode
            extraction = await agent.extract_paper(sample_paper, sample_schema, triple_review=False)

            assert extraction.paper_id == sample_paper.id
            assert extraction.schema_name == sample_schema.name
            assert extraction.extraction_method == ExtractionMethod.SINGLE_PASS
            assert "study_design" in extraction.data
            assert extraction.data["study_design"] == "RCT"
            assert "sample_size" in extraction.data
            assert extraction.data["sample_size"] == 120
            assert extraction.extraction_quality > 0

    @pytest.mark.asyncio
    async def test_triple_review_consensus(self, sample_paper, sample_schema):
        """Test triple-review mode with consensus."""
        agent = DataExtractionAgent()

        # Mock three reviewer responses with consensus
        mock_responses = []
        for temp in [0.2, 0.5, 0.8]:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.tool_calls = [
                MagicMock(
                    function=MagicMock(
                        name="extract_data",
                        arguments='{"extractions": [{"field_name": "study_design", "value": "RCT", "confidence": 1.0}, {"field_name": "sample_size", "value": 120, "confidence": 0.95}, {"field_name": "primary_outcome", "value": "blood pressure", "confidence": 0.9}, {"field_name": "intervention_description", "value": "Drug X 10mg daily", "confidence": 0.85}]}',
                    )
                )
            ]
            mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)
            mock_responses.append(mock_response)

        with patch.object(agent, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = mock_responses

            extraction = await agent.extract_paper(sample_paper, sample_schema, triple_review=True)

            assert extraction.extraction_method == ExtractionMethod.TRIPLE_REVIEW
            # 3 reviewers × 4 fields = 12 decisions
            assert len(extraction.reviewer_decisions) == 12
            assert extraction.confidence["study_design"] == 1.0  # All agreed
            assert extraction.extraction_quality > 0.8  # High agreement
            assert not extraction.has_conflicts

    @pytest.mark.asyncio
    async def test_batch_extraction(self, sample_paper, sample_schema):
        """Test extracting from multiple papers."""
        agent = DataExtractionAgent()

        # Create 3 papers
        papers = [
            sample_paper,
            Paper(
                id="test_002",
                title="Paper 2",
                abstract="Test abstract 2",
                authors=[],
                year=2023,
                source=PaperSource.PUBMED,
            ),
            Paper(
                id="test_003",
                title="Paper 3",
                abstract="Test abstract 3",
                authors=[],
                year=2023,
                source=PaperSource.PUBMED,
            ),
        ]

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="extract_data",
                    arguments='{"extractions": [{"field_name": "study_design", "value": "RCT", "confidence": 1.0}, {"field_name": "sample_size", "value": 100, "confidence": 0.9}, {"field_name": "primary_outcome", "value": "test outcome", "confidence": 0.8}, {"field_name": "intervention_description", "value": "test intervention", "confidence": 0.8}]}',
                )
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)

        with patch.object(agent, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await agent.extract_batch(papers, sample_schema, triple_review=False)

            assert result.total_papers == 3
            assert len(result.extractions) == 3
            assert result.extraction_method == ExtractionMethod.SINGLE_PASS
            assert result.success_rate >= 0
            assert result.estimated_cost >= 0


class TestExtractedData:
    """Tests for ExtractedData model."""

    def test_needs_human_review_conflicts(self):
        """Test that papers with conflicts need review."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            conflicts=["sample_size"],
            extraction_quality=0.9,
        )

        assert extraction.has_conflicts
        assert extraction.needs_human_review

    def test_needs_human_review_low_confidence(self):
        """Test that low confidence fields trigger review."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            data={"sample_size": 100},
            confidence={"sample_size": 0.5},  # Low confidence
            extraction_quality=0.9,
        )

        assert len(extraction.low_confidence_fields) > 0
        assert extraction.needs_human_review

    def test_needs_human_review_low_quality(self):
        """Test that low quality extraction needs review."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            extraction_quality=0.6,  # Below threshold
        )

        assert extraction.needs_human_review

    def test_high_quality_extraction_no_review(self):
        """Test that high quality extraction doesn't need review."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            data={"sample_size": 100, "study_design": "RCT"},
            confidence={"sample_size": 0.95, "study_design": 1.0},
            conflicts=[],
            extraction_quality=0.95,
        )

        assert not extraction.has_conflicts
        assert len(extraction.low_confidence_fields) == 0
        assert not extraction.needs_human_review

    def test_average_confidence(self):
        """Test average confidence calculation."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.SINGLE_PASS,
            confidence={"field1": 0.9, "field2": 0.8, "field3": 1.0},
        )

        avg = extraction.average_confidence
        assert avg == pytest.approx(0.9, abs=0.01)

    def test_low_confidence_fields_flagged_at_threshold(self):
        """Test that fields below 0.8 confidence are flagged as low-confidence."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            data={
                "field_high": "value1",
                "field_medium": "value2",
                "field_low": "value3",
                "field_borderline": "value4",
            },
            confidence={
                "field_high": 0.95,  # Above threshold - NOT flagged
                "field_medium": 0.75,  # Below 0.8 - FLAGGED
                "field_low": 0.5,  # Well below - FLAGGED
                "field_borderline": 0.8,  # Exactly at threshold - NOT flagged
            },
            extraction_quality=0.9,
        )

        # Verify threshold is 0.8
        assert ExtractedData.LOW_CONFIDENCE_THRESHOLD == 0.8

        # Verify correct fields are flagged
        assert "field_high" not in extraction.low_confidence_fields
        assert "field_medium" in extraction.low_confidence_fields
        assert "field_low" in extraction.low_confidence_fields
        assert "field_borderline" not in extraction.low_confidence_fields

        # Verify count
        assert len(extraction.low_confidence_fields) == 2

        # Verify has_low_confidence property
        assert extraction.has_low_confidence

    def test_low_confidence_fields_triggers_human_review(self):
        """Test that any low-confidence field triggers needs_human_review."""
        extraction = ExtractedData(
            paper_id="test_001",
            schema_name="Test Schema",
            extraction_method=ExtractionMethod.SINGLE_PASS,
            data={"field1": "value1"},
            confidence={"field1": 0.79},  # Just below threshold
            extraction_quality=0.95,  # High quality
            conflicts=[],  # No conflicts
        )

        assert len(extraction.low_confidence_fields) == 1
        assert extraction.needs_human_review


class TestExtractionResultSerialization:
    """Tests for ExtractionResult serialization."""

    def test_to_dict_includes_low_confidence_fields(self, sample_schema):
        """Test that to_dict() includes low_confidence_fields in extractions."""
        from arakis.models.extraction import ExtractionResult

        extraction = ExtractedData(
            paper_id="test_001",
            schema_name=sample_schema.name,
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
            data={"sample_size": 100, "study_design": "RCT"},
            confidence={"sample_size": 0.6, "study_design": 0.95},  # sample_size is low
            extraction_quality=0.85,
        )

        result = ExtractionResult(
            schema=sample_schema,
            extractions=[extraction],
            extraction_method=ExtractionMethod.TRIPLE_REVIEW,
        )

        result_dict = result.to_dict()

        # Verify low_confidence_fields is included in serialization
        assert "extractions" in result_dict
        assert len(result_dict["extractions"]) == 1
        assert "low_confidence_fields" in result_dict["extractions"][0]
        assert "sample_size" in result_dict["extractions"][0]["low_confidence_fields"]
        assert "study_design" not in result_dict["extractions"][0]["low_confidence_fields"]
