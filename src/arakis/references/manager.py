"""Reference manager for collecting, validating, and formatting references."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from arakis.models.paper import Paper
from arakis.references.extractor import CitationExtractor
from arakis.references.formatter import CitationFormatter
from arakis.references.styles import CitationStyle

if TYPE_CHECKING:
    from arakis.models.writing import Section


@dataclass
class ReferenceValidationResult:
    """Result of validating references in a section.

    Attributes:
        valid: True if all citations have corresponding papers
        missing_papers: Paper IDs cited but not registered
        unused_papers: Papers registered but not cited
        citation_count: Total number of citations (including duplicates)
        unique_citation_count: Number of unique papers cited
    """

    valid: bool
    missing_papers: list[str]
    unused_papers: list[str]
    citation_count: int
    unique_citation_count: int


@dataclass
class FormattedReference:
    """A formatted reference entry.

    Attributes:
        paper_id: The paper identifier
        paper: The Paper object
        formatted_citation: The formatted citation string
        number: The reference number (1-indexed)
    """

    paper_id: str
    paper: Paper
    formatted_citation: str
    number: int


@dataclass
class ReferenceManager:
    """Manages references for a manuscript.

    Collects papers, validates citations, and generates reference lists.
    Ensures all references are properly formatted and verified.

    Example usage:
        manager = ReferenceManager()

        # Register papers from Perplexity search
        for paper in perplexity_papers:
            manager.register_paper(paper)

        # After writing, validate citations
        result = manager.validate_citations(intro_section)
        if not result.valid:
            print(f"Missing papers: {result.missing_papers}")

        # Generate reference list
        references = manager.generate_reference_list(intro_section)
        for ref in references:
            print(f"{ref.number}. {ref.formatted_citation}")
    """

    style: CitationStyle = CitationStyle.APA_7
    papers: dict[str, Paper] = field(default_factory=dict)
    _extractor: CitationExtractor = field(default_factory=CitationExtractor)
    _formatter: Optional[CitationFormatter] = field(default=None)

    def __post_init__(self):
        """Initialize the formatter after dataclass initialization."""
        if self._formatter is None:
            self._formatter = CitationFormatter(self.style)

    def register_paper(self, paper: Paper) -> str:
        """Register a paper and return its citation key.

        Args:
            paper: Paper to register

        Returns:
            Citation key (paper's best identifier)
        """
        key = paper.best_identifier
        self.papers[key] = paper

        # Also register by alternative identifiers for flexible matching
        if paper.doi and paper.doi != key:
            self.papers[paper.doi] = paper
        if paper.pmid and paper.pmid != key:
            self.papers[f"pmid:{paper.pmid}"] = paper
        if paper.s2_id and paper.s2_id != key:
            self.papers[f"s2_{paper.s2_id}"] = paper

        return key

    def register_papers(self, papers: list[Paper]) -> list[str]:
        """Register multiple papers.

        Args:
            papers: List of papers to register

        Returns:
            List of citation keys
        """
        return [self.register_paper(p) for p in papers]

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Get a paper by ID.

        Args:
            paper_id: Paper identifier to look up

        Returns:
            Paper if found, None otherwise
        """
        return self.papers.get(paper_id)

    def get_paper_by_any_id(self, paper_id: str) -> Optional[Paper]:
        """Get a paper by any of its identifiers.

        Tries various ID formats to find a match.

        Args:
            paper_id: Paper identifier

        Returns:
            Paper if found, None otherwise
        """
        # Direct lookup
        if paper_id in self.papers:
            return self.papers[paper_id]

        # Try with common prefixes
        variants = [
            paper_id,
            f"doi:{paper_id}",
            f"pmid:{paper_id}",
            f"s2_{paper_id}",
            paper_id.replace("doi:", ""),
            paper_id.replace("pmid:", ""),
        ]

        for variant in variants:
            if variant in self.papers:
                return self.papers[variant]

        return None

    def extract_citations_from_section(self, section: "Section") -> list[str]:
        """Extract all paper IDs cited in a section (including subsections).

        Args:
            section: Section to extract citations from

        Returns:
            List of unique paper IDs in order of appearance
        """
        all_ids: list[str] = []

        # Extract from main content
        if section.content:
            ids = self._extractor.extract_unique_paper_ids(section.content)
            all_ids.extend(ids)

        # Extract from subsections recursively
        for subsection in section.subsections:
            ids = self.extract_citations_from_section(subsection)
            all_ids.extend(ids)

        # Return unique, preserving order
        seen = set()
        unique = []
        for pid in all_ids:
            if pid not in seen:
                seen.add(pid)
                unique.append(pid)

        return unique

    def validate_citations(self, section: "Section") -> ReferenceValidationResult:
        """Validate that all citations in a section have registered papers.

        Args:
            section: Section to validate

        Returns:
            Validation result with details on missing/unused papers
        """
        cited_ids = self.extract_citations_from_section(section)

        # Check which cited papers are missing
        missing = []
        for pid in cited_ids:
            if self.get_paper_by_any_id(pid) is None:
                missing.append(pid)

        # Find unused registered papers
        used = set()
        for pid in cited_ids:
            paper = self.get_paper_by_any_id(pid)
            if paper:
                used.add(paper.id)

        # Get unique registered paper IDs
        registered_ids = {p.id for p in self.papers.values()}
        unused = [pid for pid in registered_ids if pid not in used]

        # Count total citations (including duplicates)
        total_citations = 0
        if section.content:
            total_citations += self._extractor.count_citations(section.content)
        for subsection in section.subsections:
            if subsection.content:
                total_citations += self._extractor.count_citations(subsection.content)

        return ReferenceValidationResult(
            valid=len(missing) == 0,
            missing_papers=missing,
            unused_papers=unused,
            citation_count=total_citations,
            unique_citation_count=len(cited_ids),
        )

    def generate_reference_list(self, section: "Section") -> list[FormattedReference]:
        """Generate ordered reference list from a section's citations.

        Args:
            section: Section to extract citations from

        Returns:
            List of FormattedReference objects in citation order
        """
        cited_ids = self.extract_citations_from_section(section)

        references = []
        for i, paper_id in enumerate(cited_ids, start=1):
            paper = self.get_paper_by_any_id(paper_id)
            if paper:
                formatted = self._formatter.format_citation(paper)
                references.append(
                    FormattedReference(
                        paper_id=paper_id,
                        paper=paper,
                        formatted_citation=formatted,
                        number=i,
                    )
                )

        return references

    def generate_reference_section_text(self, section: "Section", numbered: bool = True) -> str:
        """Generate reference section as formatted text.

        Args:
            section: Section to extract citations from
            numbered: Whether to include numbers

        Returns:
            Formatted reference section text
        """
        references = self.generate_reference_list(section)

        lines = []
        for ref in references:
            if numbered:
                lines.append(f"{ref.number}. {ref.formatted_citation}")
            else:
                lines.append(ref.formatted_citation)

        return "\n\n".join(lines)

    def get_papers_for_section(self, section: "Section") -> list[Paper]:
        """Get all Paper objects cited in a section.

        Args:
            section: Section to get papers from

        Returns:
            List of Paper objects in citation order
        """
        cited_ids = self.extract_citations_from_section(section)

        papers = []
        seen = set()
        for paper_id in cited_ids:
            paper = self.get_paper_by_any_id(paper_id)
            if paper and paper.id not in seen:
                papers.append(paper)
                seen.add(paper.id)

        return papers

    def update_section_citations(self, section: "Section") -> None:
        """Update a section's citations field with extracted paper IDs.

        This populates section.citations with the paper IDs found in the content.

        Args:
            section: Section to update
        """
        cited_ids = self.extract_citations_from_section(section)
        section.citations = cited_ids

    def replace_with_numbered_citations(self, section: "Section") -> str:
        """Replace paper ID citations with numbered references.

        Args:
            section: Section to process

        Returns:
            Section content with [1], [2], etc. instead of [Paper ID]
        """
        citation_order = self.extract_citations_from_section(section)
        return self._extractor.replace_citations_with_numbers(section.content, citation_order)

    def get_in_text_citation(self, paper_id: str) -> Optional[str]:
        """Get an in-text citation for a paper.

        Args:
            paper_id: Paper identifier

        Returns:
            In-text citation string (e.g., "Smith et al., 2023") or None
        """
        paper = self.get_paper_by_any_id(paper_id)
        if paper:
            return self._formatter.format_in_text(paper)
        return None

    def set_style(self, style: CitationStyle) -> None:
        """Change the citation style.

        Args:
            style: New citation style to use
        """
        self.style = style
        self._formatter = CitationFormatter(style)

    def ensure_all_citations_have_entries(self, section: "Section") -> tuple["Section", list[str]]:
        """Ensure all in-text citations have corresponding reference list entries.

        This method validates that every citation in the section has a registered
        paper, and removes any orphan citations that don't have entries. This
        ensures the integrity of the reference list.

        Args:
            section: Section to clean up

        Returns:
            Tuple of (updated_section, removed_citation_ids)
            The section content is modified in-place and also returned.
        """
        # Get all valid paper IDs (including alternate identifiers)
        valid_ids = set(self.papers.keys())

        removed_citations: list[str] = []

        # Process main content
        if section.content:
            cleaned_content, removed = self._extractor.remove_orphan_citations(
                section.content, valid_ids
            )
            section.content = cleaned_content
            removed_citations.extend(removed)

        # Process subsections recursively
        for subsection in section.subsections:
            _, sub_removed = self.ensure_all_citations_have_entries(subsection)
            removed_citations.extend(sub_removed)

        return section, removed_citations

    def clear(self) -> None:
        """Clear all registered papers."""
        self.papers.clear()

    @property
    def paper_count(self) -> int:
        """Number of unique papers registered."""
        return len({p.id for p in self.papers.values()})

    @property
    def all_papers(self) -> list[Paper]:
        """Get all unique registered papers."""
        seen = set()
        papers = []
        for paper in self.papers.values():
            if paper.id not in seen:
                papers.append(paper)
                seen.add(paper.id)
        return papers
