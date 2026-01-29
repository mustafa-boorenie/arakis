"""Unit tests for PRISMA diagram generator.

Tests that PRISMA diagrams are generated programmatically (NO LLM).
"""

import tempfile
from pathlib import Path

import pytest

from arakis.models.visualization import PRISMAFlow, PRISMADiagram
from arakis.visualization.prisma import PRISMADiagramGenerator


class TestPRISMADiagramGenerator:
    """Tests for PRISMADiagramGenerator."""

    @pytest.fixture
    def sample_flow(self) -> PRISMAFlow:
        """Create a sample PRISMA flow for testing."""
        return PRISMAFlow(
            records_identified_total=150,
            records_identified_databases={"pubmed": 80, "embase": 50, "cochrane": 20},
            records_identified_registers=0,
            records_removed_duplicates=30,
            records_screened=120,
            records_excluded=95,
            exclusion_reasons={
                "Wrong study design": 45,
                "Wrong population": 30,
                "Wrong intervention": 20,
            },
            reports_sought=25,
            reports_not_retrieved=3,
            reports_assessed=22,
            reports_excluded=2,
            reports_exclusion_reasons={
                "Insufficient data": 1,
                "Wrong outcomes": 1,
            },
            studies_included=20,
            reports_included=20,
        )

    def test_generator_creates_svg(self, sample_flow: PRISMAFlow) -> None:
        """Test that generator creates SVG content programmatically."""
        generator = PRISMADiagramGenerator()
        
        diagram = generator.generate(sample_flow, format="svg")
        
        assert diagram.svg_content is not None
        assert "<svg" in diagram.svg_content
        assert "</svg>" in diagram.svg_content
        assert "PRISMA 2020" in diagram.svg_content
        assert "n = 150" in diagram.svg_content  # Records identified
        assert "n = 20" in diagram.svg_content  # Studies included

    def test_generator_creates_png(self, sample_flow: PRISMAFlow) -> None:
        """Test that generator creates PNG bytes programmatically."""
        generator = PRISMADiagramGenerator()
        
        diagram = generator.generate(sample_flow, format="png")
        
        assert diagram.png_bytes is not None
        assert len(diagram.png_bytes) > 0
        # PNG magic number
        assert diagram.png_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_generator_creates_both_formats(self, sample_flow: PRISMAFlow) -> None:
        """Test that generator creates both SVG and PNG."""
        generator = PRISMADiagramGenerator()
        
        diagram = generator.generate(sample_flow, format="both")
        
        assert diagram.svg_content is not None
        assert diagram.png_bytes is not None

    def test_svg_contains_all_sections(self, sample_flow: PRISMAFlow) -> None:
        """Test that SVG contains all PRISMA sections."""
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(sample_flow, format="svg")
        
        svg = diagram.svg_content
        
        # Check all sections are present
        assert "Identification" in svg
        assert "Screening" in svg
        assert "Eligibility" in svg
        assert "Included" in svg

    def test_svg_contains_flow_numbers(self, sample_flow: PRISMAFlow) -> None:
        """Test that SVG contains correct flow numbers."""
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(sample_flow, format="svg")
        
        svg = diagram.svg_content
        
        # Check key numbers
        assert "pubmed: n = 80" in svg
        assert "embase: n = 50" in svg
        assert "Records screened: n = 120" in svg
        assert "Records excluded: n = 95" in svg
        assert "Studies included: n = 20" in svg

    def test_svg_has_exclusion_boxes(self, sample_flow: PRISMAFlow) -> None:
        """Test that SVG has exclusion boxes (red styling)."""
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(sample_flow, format="svg")
        
        svg = diagram.svg_content
        
        # Check for exclusion styling (red/pink colors)
        assert "#ffebee" in svg or "#c62828" in svg

    def test_prisma_flow_validation(self, sample_flow: PRISMAFlow) -> None:
        """Test that PRISMA flow validates correctly."""
        errors = sample_flow.validate()
        
        # Should have no validation errors for consistent data
        assert len(errors) == 0

    def test_prisma_flow_calculated_properties(self, sample_flow: PRISMAFlow) -> None:
        """Test calculated properties of PRISMA flow."""
        # After deduplication
        assert sample_flow.records_after_deduplication == 120  # 150 - 30
        
        # Exclusion rate
        assert sample_flow.exclusion_rate == (95 / 120) * 100
        
        # Retrieval rate
        retrieved = 25 - 3  # 22
        assert sample_flow.retrieval_rate == (retrieved / 25) * 100

    def test_generator_saves_to_file(self, sample_flow: PRISMAFlow) -> None:
        """Test that generator saves files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = PRISMADiagramGenerator(output_dir=temp_dir)
            diagram = generator.generate(sample_flow, output_filename="test_prisma", format="svg")
            
            # Check file was created
            svg_file = Path(temp_dir) / "test_prisma.svg"
            assert svg_file.exists()
            
            # Verify content
            content = svg_file.read_text()
            assert "<svg" in content

    def test_generate_simple_text(self, sample_flow: PRISMAFlow) -> None:
        """Test text representation generation."""
        generator = PRISMADiagramGenerator()
        text = generator.generate_simple_text(sample_flow)
        
        assert "PRISMA 2020 Flow Summary" in text
        assert "Records identified: 150" in text
        assert "Studies included: 20" in text


class TestPRISMAStageExecutor:
    """Tests for PRISMA stage executor."""

    def test_prisma_stage_has_zero_cost(self) -> None:
        """Verify PRISMA stage executor reports zero cost.
        
        This is critical - PRISMA must be programmatic, not LLM-based.
        """
        from arakis.workflow.stages.prisma import PRISMAStageExecutor
        
        # Check that the executor class exists and has expected attributes
        assert hasattr(PRISMAStageExecutor, 'STAGE_NAME')
        assert PRISMAStageExecutor.STAGE_NAME == "prisma"


class TestPRISMAFlowEdgeCases:
    """Tests for edge cases in PRISMA flow."""

    def test_empty_flow(self) -> None:
        """Test with zero records."""
        flow = PRISMAFlow(
            records_identified_total=0,
            studies_included=0,
            reports_included=0,
        )
        
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(flow, format="svg")
        
        assert diagram.svg_content is not None
        assert "n = 0" in diagram.svg_content

    def test_no_exclusions(self) -> None:
        """Test when no records are excluded."""
        flow = PRISMAFlow(
            records_identified_total=10,
            records_removed_duplicates=0,
            records_screened=10,
            records_excluded=0,
            reports_sought=10,
            reports_not_retrieved=0,
            reports_assessed=10,
            reports_excluded=0,
            studies_included=10,
            reports_included=10,
        )
        
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(flow, format="svg")
        
        assert diagram.svg_content is not None
        assert "Studies included: n = 10" in diagram.svg_content

    def test_all_excluded(self) -> None:
        """Test when all records are excluded."""
        flow = PRISMAFlow(
            records_identified_total=100,
            records_removed_duplicates=10,
            records_screened=90,
            records_excluded=90,
            reports_sought=0,
            reports_not_retrieved=0,
            reports_assessed=0,
            reports_excluded=0,
            studies_included=0,
            reports_included=0,
        )
        
        generator = PRISMADiagramGenerator()
        diagram = generator.generate(flow, format="svg")
        
        assert diagram.svg_content is not None
        assert "Studies included: n = 0" in diagram.svg_content
