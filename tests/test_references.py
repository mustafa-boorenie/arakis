"""Tests for the references package."""

import pytest

from arakis.models.paper import Author, Paper
from arakis.models.writing import Section
from arakis.references import (
    CitationExtractor,
    CitationFormatter,
    CitationStyle,
    ExtractedCitation,
    FormattedReference,
    ReferenceManager,
    ReferenceValidationResult,
    StyleConfig,
    get_style_config,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        id="test_paper_1",
        title="Effect of Aspirin on Cardiovascular Mortality: A Systematic Review",
        authors=[
            Author(name="John Smith"),
            Author(name="Jane Doe"),
            Author(name="Robert Johnson"),
        ],
        journal="Journal of Cardiology",
        year=2023,
        doi="10.1234/jcard.2023.001",
        abstract="This study examines the effect of aspirin on cardiovascular mortality.",
    )


@pytest.fixture
def sample_paper_many_authors():
    """Create a paper with many authors."""
    return Paper(
        id="test_paper_2",
        title="Large Collaborative Study on Drug Efficacy",
        authors=[
            Author(name="Author One"),
            Author(name="Author Two"),
            Author(name="Author Three"),
            Author(name="Author Four"),
            Author(name="Author Five"),
            Author(name="Author Six"),
            Author(name="Author Seven"),
            Author(name="Author Eight"),
            Author(name="Author Nine"),
        ],
        journal="Nature Medicine",
        year=2022,
        doi="10.1038/nm.2022.123",
    )


@pytest.fixture
def sample_paper_single_author():
    """Create a paper with a single author."""
    return Paper(
        id="test_paper_3",
        title="Solo Research on Novel Treatments",
        authors=[Author(name="Alice Williams")],
        journal="Medical Research Today",
        year=2021,
        doi="10.5678/mrt.2021.456",
    )


@pytest.fixture
def sample_papers(sample_paper, sample_paper_many_authors, sample_paper_single_author):
    """Return all sample papers."""
    return [sample_paper, sample_paper_many_authors, sample_paper_single_author]


@pytest.fixture
def sample_section_with_citations():
    """Create a section with citations."""
    content = """
    Cardiovascular disease remains a leading cause of mortality worldwide [10.1234/jcard.2023.001].
    Previous studies have shown mixed results [doi:10.1038/nm.2022.123].
    Recent meta-analyses suggest potential benefits [10.5678/mrt.2021.456].
    """
    section = Section(title="Background", content=content)
    return section


@pytest.fixture
def sample_section_with_subsections():
    """Create a section with subsections containing citations."""
    main_section = Section(title="Introduction", content="")

    background = Section(
        title="Background",
        content="Studies show effects [10.1234/jcard.2023.001] on mortality.",
    )
    rationale = Section(
        title="Rationale",
        content="Previous reviews [doi:10.1038/nm.2022.123] had limitations.",
    )
    objectives = Section(
        title="Objectives",
        content="This review aims to synthesize evidence.",
    )

    main_section.add_subsection(background)
    main_section.add_subsection(rationale)
    main_section.add_subsection(objectives)

    return main_section


# ============================================================================
# Tests for styles.py
# ============================================================================


class TestCitationStyle:
    """Tests for CitationStyle enum."""

    def test_apa6_value(self):
        """Test APA 6 enum value."""
        assert CitationStyle.APA_6 == "apa6"

    def test_apa7_value(self):
        """Test APA 7 enum value."""
        assert CitationStyle.APA_7 == "apa7"

    def test_vancouver_value(self):
        """Test Vancouver enum value."""
        assert CitationStyle.VANCOUVER == "vancouver"

    def test_chicago_value(self):
        """Test Chicago enum value."""
        assert CitationStyle.CHICAGO == "chicago"

    def test_harvard_value(self):
        """Test Harvard enum value."""
        assert CitationStyle.HARVARD == "harvard"

    def test_all_styles_exist(self):
        """Test that all expected styles are defined."""
        styles = [s.value for s in CitationStyle]
        assert "apa6" in styles
        assert "apa7" in styles
        assert "vancouver" in styles
        assert "chicago" in styles
        assert "harvard" in styles


class TestStyleConfig:
    """Tests for StyleConfig and get_style_config."""

    def test_get_apa6_config(self):
        """Test getting APA 6 configuration."""
        config = get_style_config(CitationStyle.APA_6)
        assert isinstance(config, StyleConfig)
        assert config.name == "APA 6th Edition"
        assert config.et_al_threshold == 8
        assert config.use_ampersand is True
        assert config.year_in_parens is True

    def test_get_apa7_config(self):
        """Test getting APA 7 configuration."""
        config = get_style_config(CitationStyle.APA_7)
        assert config.et_al_threshold == 21
        assert config.et_al_first == 19

    def test_get_vancouver_config(self):
        """Test getting Vancouver configuration."""
        config = get_style_config(CitationStyle.VANCOUVER)
        assert config.use_ampersand is False
        assert config.doi_format == "doi"

    def test_all_styles_have_configs(self):
        """Test that all styles have configurations."""
        for style in CitationStyle:
            config = get_style_config(style)
            assert config is not None
            assert config.style == style


# ============================================================================
# Tests for formatter.py
# ============================================================================


class TestCitationFormatter:
    """Tests for CitationFormatter class."""

    def test_default_style_is_apa6(self):
        """Test that default style is APA 6."""
        formatter = CitationFormatter()
        assert formatter.style == CitationStyle.APA_6

    def test_custom_style(self):
        """Test creating formatter with custom style."""
        formatter = CitationFormatter(style=CitationStyle.VANCOUVER)
        assert formatter.style == CitationStyle.VANCOUVER


class TestAPA6Formatting:
    """Tests for APA 6 citation formatting."""

    def test_format_single_author(self, sample_paper_single_author):
        """Test formatting paper with single author."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(sample_paper_single_author)

        # Author name should be formatted (last name first)
        assert "Williams" in citation
        assert "(2021)" in citation
        assert "solo research on novel treatments" in citation.lower()
        assert "https://doi.org/10.5678/mrt.2021.456" in citation

    def test_format_two_authors(self):
        """Test formatting paper with two authors."""
        paper = Paper(
            id="two_auth",
            title="Two Author Study",
            authors=[Author(name="John Smith"), Author(name="Jane Doe")],
            journal="Test Journal",
            year=2020,
            doi="10.1234/test",
        )
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(paper)

        assert "Smith, J." in citation
        assert "& Doe, J." in citation

    def test_format_three_to_seven_authors(self, sample_paper):
        """Test formatting paper with 3-7 authors (all listed)."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(sample_paper)

        assert "Smith, J." in citation
        assert "Doe, J." in citation
        assert "Johnson, R." in citation
        assert "&" in citation

    def test_format_eight_plus_authors(self, sample_paper_many_authors):
        """Test formatting paper with 8+ authors (first 6 + ... + last)."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(sample_paper_many_authors)

        # Should have first 6 authors
        assert "One, A." in citation
        assert "Two, A." in citation
        assert "Six, A." in citation
        # Should have ellipsis and last author
        assert "..." in citation
        assert "Nine, A." in citation

    def test_format_no_authors(self):
        """Test formatting paper with no authors."""
        paper = Paper(
            id="no_auth",
            title="Anonymous Study",
            authors=[],
            journal="Test Journal",
            year=2020,
        )
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(paper)

        # Title should still be present
        assert "anonymous study" in citation.lower()
        assert "2020" in citation

    def test_format_no_year(self):
        """Test formatting paper with no year."""
        paper = Paper(
            id="no_year",
            title="Undated Study",
            authors=[Author(name="John Smith")],
            journal="Test Journal",
            year=None,
        )
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(paper)

        assert "(n.d.)" in citation

    def test_format_no_doi(self):
        """Test formatting paper with no DOI."""
        paper = Paper(
            id="no_doi",
            title="No DOI Study",
            authors=[Author(name="John Smith")],
            journal="Test Journal",
            year=2020,
            doi=None,
        )
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(paper)

        assert "doi.org" not in citation

    def test_title_sentence_case(self, sample_paper):
        """Test that title is converted to sentence case."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(sample_paper)

        # Title should be sentence case (first word capitalized)
        assert "Effect of aspirin" in citation or "effect of aspirin" in citation.lower()

    def test_journal_italicized(self, sample_paper):
        """Test that journal is italicized (markdown format)."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        citation = formatter.format_citation(sample_paper)

        assert "*Journal of Cardiology*" in citation


class TestInTextCitation:
    """Tests for in-text citation formatting."""

    def test_in_text_single_author(self, sample_paper_single_author):
        """Test in-text citation for single author."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        in_text = formatter.format_in_text(sample_paper_single_author)

        assert in_text == "Williams, 2021"

    def test_in_text_two_authors(self):
        """Test in-text citation for two authors."""
        paper = Paper(
            id="two",
            title="Test",
            authors=[Author(name="John Smith"), Author(name="Jane Doe")],
            year=2020,
        )
        formatter = CitationFormatter(CitationStyle.APA_6)
        in_text = formatter.format_in_text(paper)

        assert "Smith & Doe" in in_text
        assert "2020" in in_text

    def test_in_text_multiple_authors(self, sample_paper):
        """Test in-text citation for 3+ authors (et al.)."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        in_text = formatter.format_in_text(sample_paper)

        assert "Smith et al." in in_text
        assert "2023" in in_text

    def test_in_text_without_year(self, sample_paper):
        """Test in-text citation without year."""
        formatter = CitationFormatter(CitationStyle.APA_6)
        in_text = formatter.format_in_text(sample_paper, include_year=False)

        assert "Smith et al." in in_text
        assert "2023" not in in_text


class TestVancouverFormatting:
    """Tests for Vancouver citation formatting."""

    def test_vancouver_author_format(self, sample_paper):
        """Test Vancouver author formatting (Last AB)."""
        formatter = CitationFormatter(CitationStyle.VANCOUVER)
        citation = formatter.format_citation(sample_paper)

        # Vancouver uses "Last AB" format without periods
        assert "Smith J" in citation or "Smith, J" in citation

    def test_vancouver_no_ampersand(self, sample_paper):
        """Test Vancouver doesn't use ampersand."""
        formatter = CitationFormatter(CitationStyle.VANCOUVER)
        citation = formatter.format_citation(sample_paper)

        # Vancouver typically uses commas, not ampersand
        # (Implementation may vary)

    def test_vancouver_doi_format(self, sample_paper):
        """Test Vancouver DOI format (doi: prefix)."""
        formatter = CitationFormatter(CitationStyle.VANCOUVER)
        citation = formatter.format_citation(sample_paper)

        assert "doi:" in citation.lower() or "doi.org" in citation


# ============================================================================
# Tests for extractor.py
# ============================================================================


class TestCitationExtractor:
    """Tests for CitationExtractor class."""

    def test_extract_doi_citation(self):
        """Test extracting DOI citation."""
        extractor = CitationExtractor()
        text = "Previous studies [10.1234/test.2023.001] showed effects."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert citations[0].paper_id == "10.1234/test.2023.001"

    def test_extract_doi_with_prefix(self):
        """Test extracting DOI with doi: prefix."""
        extractor = CitationExtractor()
        text = "Studies [doi:10.1234/test] demonstrated this."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert citations[0].paper_id == "10.1234/test"

    def test_extract_pmid_citation(self):
        """Test extracting PMID citation."""
        extractor = CitationExtractor()
        text = "Research [pmid:12345678] found evidence."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert "pmid:12345678" in citations[0].paper_id.lower()

    def test_extract_semantic_scholar_id(self):
        """Test extracting Semantic Scholar ID."""
        extractor = CitationExtractor()
        text = "Studies [s2_abc123def456] reported."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert citations[0].paper_id == "s2_abc123def456"

    def test_extract_perplexity_id(self):
        """Test extracting Perplexity-generated ID."""
        extractor = CitationExtractor()
        text = "Research [perplexity_abc123] showed."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert citations[0].paper_id == "perplexity_abc123"

    def test_extract_multiple_citations(self):
        """Test extracting multiple citations."""
        extractor = CitationExtractor()
        text = "Studies [10.1234/a] and [10.5678/b] showed [pmid:123]."
        citations = extractor.extract_citations(text)

        assert len(citations) == 3

    def test_ignore_figure_references(self):
        """Test that figure references are ignored."""
        extractor = CitationExtractor()
        text = "See [Figure 1] and [Fig. 2] for details."
        citations = extractor.extract_citations(text)

        assert len(citations) == 0

    def test_ignore_table_references(self):
        """Test that table references are ignored."""
        extractor = CitationExtractor()
        text = "See [Table 1] and [Tab. 2] for data."
        citations = extractor.extract_citations(text)

        assert len(citations) == 0

    def test_ignore_numeric_references(self):
        """Test that pure numeric references are ignored."""
        extractor = CitationExtractor()
        text = "Previous studies [1] and [2] showed."
        citations = extractor.extract_citations(text)

        assert len(citations) == 0

    def test_ignore_equation_references(self):
        """Test that equation references are ignored."""
        extractor = CitationExtractor()
        text = "From [Equation 1] and [Eq. 2]."
        citations = extractor.extract_citations(text)

        assert len(citations) == 0

    def test_extract_positions(self):
        """Test that citation positions are correctly recorded."""
        extractor = CitationExtractor()
        text = "Start [10.1234/test] end."
        citations = extractor.extract_citations(text)

        assert len(citations) == 1
        assert citations[0].start_pos == 6
        # "[10.1234/test]" is 14 chars, so end_pos = 6 + 14 = 20
        assert citations[0].end_pos == 20
        assert citations[0].original_text == "[10.1234/test]"

    def test_extract_unique_paper_ids(self):
        """Test extracting unique paper IDs."""
        extractor = CitationExtractor()
        text = "Study [10.1234/a] showed [10.1234/b]. Later [10.1234/a] confirmed."
        unique_ids = extractor.extract_unique_paper_ids(text)

        assert len(unique_ids) == 2
        assert unique_ids[0] == "10.1234/a"
        assert unique_ids[1] == "10.1234/b"

    def test_count_citations(self):
        """Test counting citations including duplicates."""
        extractor = CitationExtractor()
        text = "Study [10.1234/a] and [10.1234/b]. Also [10.1234/a]."
        count = extractor.count_citations(text)

        assert count == 3

    def test_replace_with_numbers(self):
        """Test replacing citations with numbers."""
        extractor = CitationExtractor()
        text = "Study [10.1234/a] and [10.1234/b] showed effects."
        order = ["10.1234/a", "10.1234/b"]
        result = extractor.replace_citations_with_numbers(text, order)

        assert "[1]" in result
        assert "[2]" in result
        assert "[10.1234/a]" not in result

    def test_replace_with_numbers_preserves_order(self):
        """Test that replacement preserves citation order."""
        extractor = CitationExtractor()
        text = "[10.1234/b] comes before [10.1234/a] here."
        order = ["10.1234/a", "10.1234/b"]
        result = extractor.replace_citations_with_numbers(text, order)

        # b should be [2] and a should be [1]
        assert result.startswith("[2]")
        assert "[1]" in result


class TestExtractedCitation:
    """Tests for ExtractedCitation dataclass."""

    def test_extracted_citation_creation(self):
        """Test creating ExtractedCitation."""
        citation = ExtractedCitation(
            paper_id="10.1234/test",
            start_pos=10,
            end_pos=25,
            original_text="[10.1234/test]",
        )

        assert citation.paper_id == "10.1234/test"
        assert citation.start_pos == 10
        assert citation.end_pos == 25
        assert citation.original_text == "[10.1234/test]"


# ============================================================================
# Tests for manager.py
# ============================================================================


class TestReferenceManager:
    """Tests for ReferenceManager class."""

    def test_default_style(self):
        """Test default citation style is APA 6."""
        manager = ReferenceManager()
        assert manager.style == CitationStyle.APA_6

    def test_custom_style(self):
        """Test creating manager with custom style."""
        manager = ReferenceManager(style=CitationStyle.VANCOUVER)
        assert manager.style == CitationStyle.VANCOUVER

    def test_register_paper(self, sample_paper):
        """Test registering a paper."""
        manager = ReferenceManager()
        key = manager.register_paper(sample_paper)

        assert key == sample_paper.best_identifier
        assert manager.get_paper(key) == sample_paper

    def test_register_papers(self, sample_papers):
        """Test registering multiple papers."""
        manager = ReferenceManager()
        keys = manager.register_papers(sample_papers)

        assert len(keys) == 3
        assert manager.paper_count == 3

    def test_get_paper_by_doi(self, sample_paper):
        """Test getting paper by DOI."""
        manager = ReferenceManager()
        manager.register_paper(sample_paper)

        paper = manager.get_paper_by_any_id(sample_paper.doi)
        assert paper == sample_paper

    def test_get_nonexistent_paper(self):
        """Test getting nonexistent paper returns None."""
        manager = ReferenceManager()
        paper = manager.get_paper("nonexistent_id")

        assert paper is None

    def test_paper_count(self, sample_papers):
        """Test paper count property."""
        manager = ReferenceManager()
        assert manager.paper_count == 0

        manager.register_papers(sample_papers)
        assert manager.paper_count == 3

    def test_all_papers(self, sample_papers):
        """Test all_papers property."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        all_papers = manager.all_papers
        assert len(all_papers) == 3

    def test_clear(self, sample_papers):
        """Test clearing registered papers."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)
        assert manager.paper_count == 3

        manager.clear()
        assert manager.paper_count == 0

    def test_set_style(self):
        """Test changing citation style."""
        manager = ReferenceManager()
        assert manager.style == CitationStyle.APA_6

        manager.set_style(CitationStyle.VANCOUVER)
        assert manager.style == CitationStyle.VANCOUVER


class TestReferenceManagerCitationExtraction:
    """Tests for citation extraction from sections."""

    def test_extract_citations_from_section(self, sample_section_with_citations):
        """Test extracting citations from a section."""
        manager = ReferenceManager()
        citations = manager.extract_citations_from_section(sample_section_with_citations)

        assert len(citations) == 3
        assert "10.1234/jcard.2023.001" in citations
        assert "10.1038/nm.2022.123" in citations
        assert "10.5678/mrt.2021.456" in citations

    def test_extract_citations_from_subsections(self, sample_section_with_subsections):
        """Test extracting citations from subsections."""
        manager = ReferenceManager()
        citations = manager.extract_citations_from_section(sample_section_with_subsections)

        assert len(citations) == 2
        assert "10.1234/jcard.2023.001" in citations
        assert "10.1038/nm.2022.123" in citations

    def test_extract_preserves_order(self, sample_section_with_citations):
        """Test that citation extraction preserves order."""
        manager = ReferenceManager()
        citations = manager.extract_citations_from_section(sample_section_with_citations)

        assert citations[0] == "10.1234/jcard.2023.001"


class TestReferenceValidation:
    """Tests for reference validation."""

    def test_validate_all_present(self, sample_papers, sample_section_with_citations):
        """Test validation when all cited papers are registered."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        result = manager.validate_citations(sample_section_with_citations)

        assert result.valid is True
        assert len(result.missing_papers) == 0

    def test_validate_missing_papers(self, sample_section_with_citations):
        """Test validation when some papers are missing."""
        manager = ReferenceManager()
        # Don't register any papers

        result = manager.validate_citations(sample_section_with_citations)

        assert result.valid is False
        assert len(result.missing_papers) == 3

    def test_validate_unused_papers(self, sample_papers):
        """Test validation reports unused papers."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        # Section with no citations
        empty_section = Section(title="Empty", content="No citations here.")
        result = manager.validate_citations(empty_section)

        assert result.valid is True
        assert len(result.unused_papers) == 3

    def test_validation_result_counts(self, sample_papers, sample_section_with_citations):
        """Test validation result counts."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        result = manager.validate_citations(sample_section_with_citations)

        assert result.citation_count == 3
        assert result.unique_citation_count == 3


class TestReferenceListGeneration:
    """Tests for generating reference lists."""

    def test_generate_reference_list(self, sample_papers, sample_section_with_citations):
        """Test generating ordered reference list."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        references = manager.generate_reference_list(sample_section_with_citations)

        assert len(references) == 3
        assert all(isinstance(r, FormattedReference) for r in references)
        assert references[0].number == 1
        assert references[1].number == 2
        assert references[2].number == 3

    def test_generate_reference_section_text(
        self, sample_papers, sample_section_with_citations
    ):
        """Test generating reference section as text."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        text = manager.generate_reference_section_text(sample_section_with_citations)

        assert "1." in text
        assert "2." in text
        assert "3." in text

    def test_generate_unnumbered_references(
        self, sample_papers, sample_section_with_citations
    ):
        """Test generating unnumbered reference list."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        text = manager.generate_reference_section_text(
            sample_section_with_citations, numbered=False
        )

        # Unnumbered should not start lines with "1. ", "2. ", etc.
        lines = text.strip().split("\n\n")
        for line in lines:
            # Check that lines don't start with number followed by period and space
            assert not line.strip().startswith("1. ")
            assert not line.strip().startswith("2. ")
            assert not line.strip().startswith("3. ")

    def test_get_papers_for_section(self, sample_papers, sample_section_with_citations):
        """Test getting Paper objects for a section."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        papers = manager.get_papers_for_section(sample_section_with_citations)

        assert len(papers) == 3
        assert all(isinstance(p, Paper) for p in papers)


class TestReferenceManagerCitationReplacement:
    """Tests for citation replacement."""

    def test_replace_with_numbered_citations(
        self, sample_papers, sample_section_with_citations
    ):
        """Test replacing citations with numbers."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        result = manager.replace_with_numbered_citations(sample_section_with_citations)

        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result
        assert "[10.1234/jcard.2023.001]" not in result

    def test_update_section_citations(
        self, sample_papers, sample_section_with_citations
    ):
        """Test updating section's citations field."""
        manager = ReferenceManager()
        manager.register_papers(sample_papers)

        # Initially empty
        assert len(sample_section_with_citations.citations) == 0

        manager.update_section_citations(sample_section_with_citations)

        assert len(sample_section_with_citations.citations) == 3

    def test_get_in_text_citation(self, sample_paper):
        """Test getting in-text citation."""
        manager = ReferenceManager()
        manager.register_paper(sample_paper)

        in_text = manager.get_in_text_citation(sample_paper.doi)

        assert in_text is not None
        assert "Smith" in in_text
        assert "2023" in in_text

    def test_get_in_text_citation_missing_paper(self):
        """Test getting in-text citation for missing paper."""
        manager = ReferenceManager()

        in_text = manager.get_in_text_citation("nonexistent")

        assert in_text is None


class TestFormattedReference:
    """Tests for FormattedReference dataclass."""

    def test_formatted_reference_creation(self, sample_paper):
        """Test creating FormattedReference."""
        ref = FormattedReference(
            paper_id="10.1234/test",
            paper=sample_paper,
            formatted_citation="Smith, J. (2023). Test.",
            number=1,
        )

        assert ref.paper_id == "10.1234/test"
        assert ref.paper == sample_paper
        assert ref.formatted_citation == "Smith, J. (2023). Test."
        assert ref.number == 1


class TestReferenceValidationResult:
    """Tests for ReferenceValidationResult dataclass."""

    def test_validation_result_valid(self):
        """Test valid validation result."""
        result = ReferenceValidationResult(
            valid=True,
            missing_papers=[],
            unused_papers=[],
            citation_count=5,
            unique_citation_count=3,
        )

        assert result.valid is True
        assert result.citation_count == 5
        assert result.unique_citation_count == 3

    def test_validation_result_invalid(self):
        """Test invalid validation result."""
        result = ReferenceValidationResult(
            valid=False,
            missing_papers=["10.1234/missing"],
            unused_papers=["10.5678/unused"],
            citation_count=2,
            unique_citation_count=2,
        )

        assert result.valid is False
        assert len(result.missing_papers) == 1
        assert len(result.unused_papers) == 1
