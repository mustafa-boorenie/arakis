"""Data models for manuscript writing.

Models for sections, manuscripts, and writing results.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from arakis.models.paper import Paper
from arakis.models.visualization import Figure, Table


@dataclass
class Section:
    """Manuscript section."""

    title: str
    content: str  # Markdown or plain text
    subsections: list["Section"] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)  # Paper IDs referenced
    figures: list[str] = field(default_factory=list)  # Figure IDs referenced
    tables: list[str] = field(default_factory=list)  # Table IDs referenced
    word_count: int = 0

    def __post_init__(self):
        """Calculate word count."""
        if self.content:
            self.word_count = len(self.content.split())

    def add_subsection(self, subsection: "Section") -> None:
        """Add a subsection.

        Args:
            subsection: Section to add
        """
        self.subsections.append(subsection)

    def add_citation(self, paper_id: str) -> None:
        """Add a citation reference.

        Args:
            paper_id: Paper ID to cite
        """
        if paper_id not in self.citations:
            self.citations.append(paper_id)

    def add_figure(self, figure_id: str) -> None:
        """Add a figure reference.

        Args:
            figure_id: Figure ID to reference
        """
        if figure_id not in self.figures:
            self.figures.append(figure_id)

    def add_table(self, table_id: str) -> None:
        """Add a table reference.

        Args:
            table_id: Table ID to reference
        """
        if table_id not in self.tables:
            self.tables.append(table_id)

    @property
    def total_word_count(self) -> int:
        """Total word count including subsections."""
        count = self.word_count
        for subsection in self.subsections:
            count += subsection.total_word_count
        return count

    def to_markdown(self, level: int = 1) -> str:
        """Convert section to markdown format.

        Args:
            level: Heading level (1 for #, 2 for ##, etc.)

        Returns:
            Markdown string
        """
        lines = []

        # Title
        heading = "#" * level
        lines.append(f"{heading} {self.title}")
        lines.append("")

        # Content
        if self.content:
            lines.append(self.content)
            lines.append("")

        # Subsections
        for subsection in self.subsections:
            lines.append(subsection.to_markdown(level + 1))
            lines.append("")

        return "\n".join(lines)


@dataclass
class Manuscript:
    """Complete systematic review manuscript."""

    title: str
    abstract: Optional[Section] = None
    introduction: Optional[Section] = None
    methods: Optional[Section] = None
    results: Optional[Section] = None
    discussion: Optional[Section] = None
    conclusions: Optional[Section] = None

    # References
    references: list[Paper] = field(default_factory=list)

    # Figures and tables
    figures: dict[str, Figure] = field(default_factory=dict)  # figure_id -> Figure
    tables: dict[str, Table] = field(default_factory=dict)  # table_id -> Table

    # Metadata
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    funding: str = ""
    conflicts_of_interest: str = ""
    acknowledgments: str = ""

    @property
    def word_count(self) -> int:
        """Total manuscript word count."""
        count = 0
        for section in [
            self.abstract,
            self.introduction,
            self.methods,
            self.results,
            self.discussion,
            self.conclusions,
        ]:
            if section:
                count += section.total_word_count
        return count

    @property
    def sections(self) -> list[Section]:
        """Get all non-None sections."""
        sections = []
        for section in [
            self.abstract,
            self.introduction,
            self.methods,
            self.results,
            self.discussion,
            self.conclusions,
        ]:
            if section:
                sections.append(section)
        return sections

    def add_figure(self, figure: Figure) -> None:
        """Add a figure to manuscript.

        Args:
            figure: Figure to add
        """
        self.figures[figure.id] = figure

    def add_table(self, table: Table) -> None:
        """Add a table to manuscript.

        Args:
            table: Table to add
        """
        self.tables[table.id] = table

    def add_reference(self, paper: Paper) -> None:
        """Add a reference.

        Args:
            paper: Paper to add to references
        """
        if paper not in self.references:
            self.references.append(paper)

    def to_markdown(self) -> str:
        """Convert manuscript to markdown format.

        Returns:
            Complete manuscript as markdown
        """
        lines = []

        # Title
        lines.append(f"# {self.title}")
        lines.append("")

        # Authors
        if self.authors:
            lines.append("**Authors:** " + ", ".join(self.authors))
            lines.append("")

        # Keywords
        if self.keywords:
            lines.append("**Keywords:** " + ", ".join(self.keywords))
            lines.append("")
            lines.append("---")
            lines.append("")

        # Sections
        for section in self.sections:
            lines.append(section.to_markdown())
            lines.append("")

        # Figures
        if self.figures:
            lines.append("## Figures")
            lines.append("")
            for fig_id, figure in self.figures.items():
                lines.append(f"### {figure.title}")
                lines.append(f"![{figure.title}]({figure.file_path})")
                lines.append(f"*{figure.caption}*")
                lines.append("")

        # Tables
        if self.tables:
            lines.append("## Tables")
            lines.append("")
            for table_id, table in self.tables.items():
                lines.append(f"### {table.title}")
                lines.append(table.markdown)
                lines.append(f"*{table.caption}*")
                lines.append("")

        # References
        if self.references:
            lines.append("## References")
            lines.append("")
            for i, paper in enumerate(self.references, 1):
                citation = self._format_citation(paper, i)
                lines.append(f"{i}. {citation}")
                lines.append("")

        # Supplementary sections
        if self.funding:
            lines.append("## Funding")
            lines.append(self.funding)
            lines.append("")

        if self.conflicts_of_interest:
            lines.append("## Conflicts of Interest")
            lines.append(self.conflicts_of_interest)
            lines.append("")

        if self.acknowledgments:
            lines.append("## Acknowledgments")
            lines.append(self.acknowledgments)
            lines.append("")

        return "\n".join(lines)

    def _format_citation(self, paper: Paper, number: int) -> str:
        """Format a paper citation.

        Args:
            paper: Paper to cite
            number: Citation number

        Returns:
            Formatted citation string
        """
        # Authors
        authors_str = ""
        if paper.authors:
            if len(paper.authors) > 3:
                authors_str = f"{paper.authors[0].name} et al."
            else:
                authors_str = ", ".join(a.name for a in paper.authors)

        # Title
        title_str = paper.title

        # Journal and year
        journal_str = paper.journal or "Journal"
        year_str = str(paper.year) if paper.year else "n.d."

        # DOI if available
        doi_str = f" doi:{paper.doi}" if paper.doi else ""

        return f"{authors_str} {title_str}. {journal_str}. {year_str}.{doi_str}"

    def to_dict(self) -> dict[str, Any]:
        """Convert manuscript to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "word_count": self.word_count,
            "sections": {
                "abstract": self.abstract.to_markdown() if self.abstract else None,
                "introduction": self.introduction.to_markdown() if self.introduction else None,
                "methods": self.methods.to_markdown() if self.methods else None,
                "results": self.results.to_markdown() if self.results else None,
                "discussion": self.discussion.to_markdown() if self.discussion else None,
                "conclusions": self.conclusions.to_markdown() if self.conclusions else None,
            },
            "figures": {
                fig_id: {
                    "title": fig.title,
                    "caption": fig.caption,
                    "file_path": fig.file_path,
                    "type": fig.figure_type,
                }
                for fig_id, fig in self.figures.items()
            },
            "tables": {
                table_id: {
                    "title": table.title,
                    "caption": table.caption,
                    "markdown": table.markdown,
                }
                for table_id, table in self.tables.items()
            },
            "metadata": {
                "authors": self.authors,
                "affiliations": self.affiliations,
                "keywords": self.keywords,
                "funding": self.funding,
                "conflicts_of_interest": self.conflicts_of_interest,
                "acknowledgments": self.acknowledgments,
            },
            "references_count": len(self.references),
        }


@dataclass
class WritingResult:
    """Result from writing a manuscript section."""

    section: Section
    generation_time_ms: int
    tokens_used: int
    cost_usd: float
    success: bool
    error_message: str = ""
