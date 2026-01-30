"""Tests for CLI workflow command, specifically the --schema option."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.extraction.schemas import (
    AVAILABLE_SCHEMAS,
    CASE_CONTROL_SCHEMA,
    COHORT_SCHEMA,
    DIAGNOSTIC_SCHEMA,
    RCT_SCHEMA,
    detect_schema,
    get_schema,
    get_schema_auto,
    list_schemas,
)


class TestGetSchema:
    """Tests for get_schema function."""

    def test_get_rct_schema(self):
        """Test getting RCT schema by name."""
        schema = get_schema("rct")
        assert schema.name == "rct"
        assert schema == RCT_SCHEMA
        assert "study_design" in [f.name for f in schema.fields]
        assert "randomization_method" in [f.name for f in schema.fields]

    def test_get_cohort_schema(self):
        """Test getting cohort schema by name."""
        schema = get_schema("cohort")
        assert schema.name == "cohort"
        assert schema == COHORT_SCHEMA
        assert "cohort_type" in [f.name for f in schema.fields]
        assert "exposure" in [f.name for f in schema.fields]
        # Cohort schema should NOT have RCT-specific fields
        field_names = [f.name for f in schema.fields]
        assert "randomization_method" not in field_names
        assert "blinding" not in field_names

    def test_get_case_control_schema(self):
        """Test getting case-control schema by name."""
        schema = get_schema("case_control")
        assert schema.name == "case_control"
        assert schema == CASE_CONTROL_SCHEMA
        assert "number_of_cases" in [f.name for f in schema.fields]
        assert "number_of_controls" in [f.name for f in schema.fields]
        assert "odds_ratio" in [f.name for f in schema.fields]

    def test_get_diagnostic_schema(self):
        """Test getting diagnostic schema by name."""
        schema = get_schema("diagnostic")
        assert schema.name == "diagnostic"
        assert schema == DIAGNOSTIC_SCHEMA
        assert "index_test" in [f.name for f in schema.fields]
        assert "reference_standard" in [f.name for f in schema.fields]
        assert "sensitivity" in [f.name for f in schema.fields]

    def test_get_invalid_schema_raises_error(self):
        """Test that invalid schema name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_schema("invalid_schema")

        assert "Unknown schema 'invalid_schema'" in str(exc_info.value)
        assert "Available schemas:" in str(exc_info.value)

    def test_get_schema_case_sensitive(self):
        """Test that schema names are case-sensitive."""
        with pytest.raises(ValueError):
            get_schema("RCT")  # Should be lowercase "rct"

        with pytest.raises(ValueError):
            get_schema("Cohort")  # Should be lowercase "cohort"


class TestListSchemas:
    """Tests for list_schemas function."""

    def test_list_schemas_returns_all(self):
        """Test that list_schemas returns all available schemas."""
        schemas = list_schemas()
        assert len(schemas) == 4
        assert "rct" in schemas
        assert "cohort" in schemas
        assert "case_control" in schemas
        assert "diagnostic" in schemas

    def test_list_schemas_returns_descriptions(self):
        """Test that list_schemas returns descriptions."""
        schemas = list_schemas()
        assert "Randomized Controlled Trials" in schemas["rct"]
        assert "Cohort Studies" in schemas["cohort"]
        assert "Case-Control Studies" in schemas["case_control"]
        assert "Diagnostic Accuracy Studies" in schemas["diagnostic"]


class TestAvailableSchemas:
    """Tests for AVAILABLE_SCHEMAS registry."""

    def test_all_schemas_have_unique_names(self):
        """Test that all schemas have unique names."""
        names = [schema.name for schema in AVAILABLE_SCHEMAS.values()]
        assert len(names) == len(set(names))

    def test_all_schemas_have_fields(self):
        """Test that all schemas have at least one field."""
        for name, schema in AVAILABLE_SCHEMAS.items():
            assert len(schema.fields) > 0, f"Schema '{name}' has no fields"

    def test_all_schemas_have_required_fields(self):
        """Test that all schemas have at least one required field."""
        for name, schema in AVAILABLE_SCHEMAS.items():
            required = [f for f in schema.fields if f.required]
            assert len(required) > 0, f"Schema '{name}' has no required fields"


class TestDetectSchema:
    """Tests for auto-detecting schema from text."""

    def test_detect_rct_from_randomized_trial(self):
        """Test detecting RCT schema from randomized trial mention."""
        text = "Effect of aspirin in randomized controlled trials"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "rct"
        assert confidence >= 0.6

    def test_detect_rct_from_clinical_trial(self):
        """Test detecting RCT schema from clinical trial mention."""
        text = "Double-blind placebo-controlled clinical trial of drug X"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "rct"
        assert confidence >= 0.8

    def test_detect_cohort_from_cohort_study(self):
        """Test detecting cohort schema from cohort study mention."""
        text = "Retrospective cohort study of diabetes outcomes"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "cohort"
        assert confidence >= 0.6

    def test_detect_cohort_from_observational(self):
        """Test detecting cohort schema from observational study mention."""
        text = "Observational study, prospective follow-up of patients"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "cohort"
        assert confidence >= 0.6

    def test_detect_case_control(self):
        """Test detecting case-control schema."""
        text = "Case-control study with matched controls"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "case_control"
        assert confidence >= 0.6

    def test_detect_diagnostic(self):
        """Test detecting diagnostic schema."""
        text = "Diagnostic accuracy study, sensitivity and specificity of the test"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "diagnostic"
        assert confidence >= 0.6

    def test_detect_default_rct_when_no_keywords(self):
        """Test default to RCT with low confidence when no keywords found."""
        text = "Effect of treatment on outcomes in patients"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "rct"
        assert confidence < 0.5  # Low confidence

    def test_detect_schema_case_insensitive(self):
        """Test that detection is case-insensitive."""
        text = "RANDOMIZED CONTROLLED TRIAL"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "rct"
        assert confidence >= 0.6

    def test_detect_cohort_from_inclusion_criteria(self):
        """Test detecting cohort from typical inclusion criteria."""
        text = "Type 2 diabetes, Metformin, Mortality, Cohort or observational studies"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "cohort"
        assert confidence >= 0.6

    def test_detect_rct_from_inclusion_criteria(self):
        """Test detecting RCT from typical RCT inclusion criteria."""
        text = "Hypertension, Drug intervention, RCTs only, Placebo-controlled"
        schema_name, confidence = detect_schema(text)
        assert schema_name == "rct"
        assert confidence >= 0.6

    def test_get_schema_auto(self):
        """Test get_schema_auto returns schema object and metadata."""
        text = "Retrospective cohort study of outcomes"
        schema, name, confidence = get_schema_auto(text)
        assert name == "cohort"
        assert schema == COHORT_SCHEMA
        assert confidence >= 0.6


class TestSchemaFieldDifferences:
    """Tests to verify schemas have appropriate fields for their study types."""

    def test_rct_has_randomization_fields(self):
        """Test that RCT schema has randomization-specific fields."""
        schema = get_schema("rct")
        field_names = [f.name for f in schema.fields]

        # RCT-specific fields
        assert "randomization_method" in field_names
        assert "allocation_concealment" in field_names
        assert "blinding" in field_names
        assert "intervention_name" in field_names
        assert "control_type" in field_names

    def test_cohort_has_exposure_fields(self):
        """Test that cohort schema has exposure-specific fields."""
        schema = get_schema("cohort")
        field_names = [f.name for f in schema.fields]

        # Cohort-specific fields
        assert "cohort_type" in field_names
        assert "exposure" in field_names
        assert "exposure_assessment" in field_names
        assert "sample_size_exposed" in field_names
        assert "sample_size_unexposed" in field_names
        assert "adjusted_for_confounders" in field_names

        # Should NOT have RCT fields
        assert "randomization_method" not in field_names
        assert "blinding" not in field_names

    def test_case_control_has_case_fields(self):
        """Test that case-control schema has case-specific fields."""
        schema = get_schema("case_control")
        field_names = [f.name for f in schema.fields]

        # Case-control-specific fields
        assert "number_of_cases" in field_names
        assert "number_of_controls" in field_names
        assert "case_definition" in field_names
        assert "control_selection" in field_names
        assert "matching_criteria" in field_names
        assert "odds_ratio" in field_names

    def test_diagnostic_has_accuracy_fields(self):
        """Test that diagnostic schema has accuracy-specific fields."""
        schema = get_schema("diagnostic")
        field_names = [f.name for f in schema.fields]

        # Diagnostic-specific fields
        assert "index_test" in field_names
        assert "reference_standard" in field_names
        assert "true_positives" in field_names
        assert "false_positives" in field_names
        assert "true_negatives" in field_names
        assert "false_negatives" in field_names
        assert "sensitivity" in field_names
        assert "specificity" in field_names


class TestWorkflowSchemaIntegration:
    """Integration tests for workflow schema option."""

    @pytest.mark.asyncio
    async def test_extraction_with_cohort_schema(self):
        """Test that extraction uses cohort schema fields when specified."""
        from arakis.agents.extractor import DataExtractionAgent
        from arakis.models.paper import Paper, PaperSource

        # Create a cohort study paper
        paper = Paper(
            id="test_cohort_001",
            title="Metformin and mortality in type 2 diabetes: A retrospective cohort study",
            abstract=(
                "Background: We conducted a retrospective cohort study of 10,000 patients "
                "with type 2 diabetes. Exposure: metformin use vs non-use. "
                "Follow-up: 5 years. Primary outcome: all-cause mortality. "
                "Results: Hazard ratio 0.75 (95% CI 0.65-0.87). "
                "Adjusted for age, sex, BMI, and comorbidities."
            ),
            authors=[],
            year=2023,
            source=PaperSource.PUBMED,
        )

        schema = get_schema("cohort")
        agent = DataExtractionAgent()

        # Mock OpenAI response with cohort-specific fields
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="extract_data",
                    arguments='{"extractions": ['
                    '{"field_name": "cohort_type", "value": "retrospective", "confidence": 0.95},'
                    '{"field_name": "sample_size_total", "value": 10000, "confidence": 0.9},'
                    '{"field_name": "exposure", "value": "metformin use", "confidence": 0.9},'
                    '{"field_name": "follow_up_duration", "value": "5 years", "confidence": 0.9},'
                    '{"field_name": "primary_outcome", "value": "all-cause mortality", "confidence": 0.95},'
                    '{"field_name": "effect_measure", "value": "HR 0.75 (95% CI 0.65-0.87)", "confidence": 0.9},'
                    '{"field_name": "population_description", "value": "Patients with type 2 diabetes", "confidence": 0.85}'
                    "]}",
                )
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)

        with patch.object(agent, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            extraction = await agent.extract_paper(paper, schema, triple_review=False)

            # Verify cohort-specific fields were extracted
            assert extraction.schema_name == "cohort"
            assert extraction.data.get("cohort_type") == "retrospective"
            assert extraction.data.get("exposure") == "metformin use"
            assert extraction.data.get("effect_measure") == "HR 0.75 (95% CI 0.65-0.87)"

            # Verify RCT fields were NOT extracted (not in schema)
            assert "randomization_method" not in extraction.data
            assert "blinding" not in extraction.data

    @pytest.mark.asyncio
    async def test_extraction_with_rct_schema(self):
        """Test that extraction uses RCT schema fields when specified."""
        from arakis.agents.extractor import DataExtractionAgent
        from arakis.models.paper import Paper, PaperSource

        # Create an RCT paper
        paper = Paper(
            id="test_rct_001",
            title="Effect of Drug X on Blood Pressure: A Randomized Controlled Trial",
            abstract=(
                "Methods: Double-blind RCT with 200 participants randomized 1:1. "
                "Intervention: Drug X 10mg. Control: placebo. "
                "Randomization: computer-generated. Blinding: participants and assessors. "
                "Primary outcome: systolic BP change at 12 weeks."
            ),
            authors=[],
            year=2023,
            source=PaperSource.PUBMED,
        )

        schema = get_schema("rct")
        agent = DataExtractionAgent()

        # Mock OpenAI response with RCT-specific fields
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="extract_data",
                    arguments='{"extractions": ['
                    '{"field_name": "study_design", "value": "parallel", "confidence": 0.95},'
                    '{"field_name": "sample_size_total", "value": 200, "confidence": 0.9},'
                    '{"field_name": "intervention_name", "value": "Drug X 10mg", "confidence": 0.9},'
                    '{"field_name": "control_type", "value": "placebo", "confidence": 0.95},'
                    '{"field_name": "randomization_method", "value": "computer-generated", "confidence": 0.9},'
                    '{"field_name": "blinding", "value": ["participants", "outcome_assessors"], "confidence": 0.85},'
                    '{"field_name": "primary_outcome", "value": "systolic BP change", "confidence": 0.9},'
                    '{"field_name": "primary_outcome_result", "value": "Significant reduction", "confidence": 0.8},'
                    '{"field_name": "population_description", "value": "Hypertensive adults", "confidence": 0.8}'
                    "]}",
                )
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=500, completion_tokens=100)

        with patch.object(agent, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            extraction = await agent.extract_paper(paper, schema, triple_review=False)

            # Verify RCT-specific fields were extracted
            assert extraction.schema_name == "rct"
            assert extraction.data.get("study_design") == "parallel"
            assert extraction.data.get("randomization_method") == "computer-generated"
            assert extraction.data.get("control_type") == "placebo"

            # Verify cohort fields were NOT extracted (not in schema)
            assert "cohort_type" not in extraction.data
            assert "exposure" not in extraction.data

    def test_schema_field_count_differences(self):
        """Test that different schemas have different field counts."""
        rct = get_schema("rct")
        cohort = get_schema("cohort")
        case_control = get_schema("case_control")
        diagnostic = get_schema("diagnostic")

        # Each schema should have a reasonable number of fields
        assert len(rct.fields) >= 10
        assert len(cohort.fields) >= 10
        assert len(case_control.fields) >= 8
        assert len(diagnostic.fields) >= 10

        # Verify they're different schemas (not just copies)
        rct_names = set(f.name for f in rct.fields)
        cohort_names = set(f.name for f in cohort.fields)

        # Some fields are unique to each
        assert "randomization_method" in rct_names
        assert "randomization_method" not in cohort_names
        assert "cohort_type" in cohort_names
        assert "cohort_type" not in rct_names
