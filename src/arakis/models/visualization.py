"""Data models for visualizations and figures.

Models for PRISMA diagrams, manuscript figures, and tables.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Figure:
    """Manuscript figure."""

    id: str  # e.g., "fig1", "fig2"
    title: str
    caption: str
    file_path: str  # Path to image file
    figure_type: str  # "forest_plot", "funnel_plot", "prisma", "box_plot", etc.
    width_inches: float = 6.0  # Figure width for publication
    height_inches: float = 4.0  # Figure height for publication
    dpi: int = 300  # Resolution
    format: str = "png"  # File format


@dataclass
class Table:
    """Manuscript table."""

    id: str  # e.g., "table1", "table2"
    title: str
    caption: str
    headers: list[str]
    rows: list[list[str]]
    footnotes: list[str] = field(default_factory=list)

    @property
    def markdown(self) -> str:
        """Generate markdown representation of table."""
        lines = []

        # Header
        lines.append("| " + " | ".join(self.headers) + " |")

        # Separator
        lines.append("|" + "|".join(["---" for _ in self.headers]) + "|")

        # Rows
        for row in self.rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        result = "\n".join(lines)

        # Add footnotes if present
        if self.footnotes:
            result += "\n\n" + "\n".join(f"*{note}*" for note in self.footnotes)

        return result

    @property
    def html(self) -> str:
        """Generate HTML representation of table."""
        lines = ['<table border="1">']

        # Header
        lines.append("  <thead>")
        lines.append("    <tr>")
        for header in self.headers:
            lines.append(f"      <th>{header}</th>")
        lines.append("    </tr>")
        lines.append("  </thead>")

        # Body
        lines.append("  <tbody>")
        for row in self.rows:
            lines.append("    <tr>")
            for cell in row:
                lines.append(f"      <td>{cell}</td>")
            lines.append("    </tr>")
        lines.append("  </tbody>")

        lines.append("</table>")

        result = "\n".join(lines)

        # Add footnotes
        if self.footnotes:
            result += "\n<p><small>" + "<br>".join(self.footnotes) + "</small></p>"

        return result


@dataclass
class PRISMAFlow:
    """PRISMA 2020 flow diagram data.

    Tracks the flow of papers through the systematic review process.
    All numbers are validated for consistency to ensure accuracy and traceability.
    """

    # Identification
    records_identified_total: int
    records_identified_databases: dict[str, int] = field(default_factory=dict)
    records_identified_registers: int = 0
    records_removed_duplicates: int = 0
    records_removed_automated: int = 0
    records_removed_other: int = 0

    # Screening
    records_screened: int = 0
    records_excluded: int = 0
    exclusion_reasons: dict[str, int] = field(default_factory=dict)

    # Eligibility
    reports_sought: int = 0
    reports_not_retrieved: int = 0
    reports_assessed: int = 0
    reports_excluded: int = 0
    reports_exclusion_reasons: dict[str, int] = field(default_factory=dict)

    # Inclusion
    studies_included: int = 0
    reports_included: int = 0

    @property
    def records_after_deduplication(self) -> int:
        """Records remaining after duplicate removal.

        Formula: records_identified_total - records_removed_duplicates
        Source: PRISMA 2020 Statement (Page et al., BMJ 2021;372:n71)
        """
        return self.records_identified_total - self.records_removed_duplicates

    @property
    def exclusion_rate(self) -> float:
        """Percentage of screened records excluded.

        Formula: (records_excluded / records_screened) * 100
        Returns: Percentage (0.0-100.0)
        """
        if self.records_screened == 0:
            return 0.0
        return (self.records_excluded / self.records_screened) * 100

    @property
    def retrieval_rate(self) -> float:
        """Percentage of sought reports successfully retrieved.

        Formula: ((reports_sought - reports_not_retrieved) / reports_sought) * 100
        Returns: Percentage (0.0-100.0)
        """
        if self.reports_sought == 0:
            return 0.0
        retrieved = self.reports_sought - self.reports_not_retrieved
        return (retrieved / self.reports_sought) * 100

    def validate(self) -> list[str]:
        """Validate internal consistency of PRISMA flow numbers.

        Checks that numbers at each stage are mathematically consistent
        to ensure accuracy and traceability of reported values.

        Returns:
            List of validation error messages (empty if all checks pass)
        """
        from arakis.traceability import validate_prisma_flow

        return validate_prisma_flow(
            records_identified=self.records_identified_total,
            duplicates_removed=self.records_removed_duplicates,
            records_screened=self.records_screened,
            records_excluded=self.records_excluded,
            reports_sought=self.reports_sought,
            reports_not_retrieved=self.reports_not_retrieved,
            reports_assessed=self.reports_assessed,
            reports_excluded=self.reports_excluded,
            studies_included=self.studies_included,
        )

    def validate_database_totals(self) -> list[str]:
        """Validate that database counts sum to total.

        Returns:
            List of validation error messages (empty if all checks pass)
        """
        errors = []
        if self.records_identified_databases:
            db_sum = sum(self.records_identified_databases.values())
            if db_sum != self.records_identified_total:
                errors.append(
                    f"Database counts sum ({db_sum}) does not match "
                    f"records_identified_total ({self.records_identified_total}). "
                    f"Databases: {self.records_identified_databases}"
                )
        return errors

    def get_audit_summary(self) -> dict[str, any]:
        """Get a summary of all PRISMA flow numbers with derivations.

        Returns:
            Dictionary with all numbers and their sources/formulas
        """
        return {
            "identification": {
                "records_identified_total": {
                    "value": self.records_identified_total,
                    "source": "sum of database searches",
                    "breakdown": self.records_identified_databases,
                },
                "records_identified_registers": {
                    "value": self.records_identified_registers,
                    "source": "registry searches",
                },
                "duplicates_removed": {
                    "value": self.records_removed_duplicates,
                    "source": "deduplication algorithm (DOI, PMID, fuzzy title)",
                },
                "records_after_deduplication": {
                    "value": self.records_after_deduplication,
                    "formula": "records_identified_total - records_removed_duplicates",
                    "calculated": True,
                },
            },
            "screening": {
                "records_screened": {
                    "value": self.records_screened,
                    "source": "title/abstract screening",
                },
                "records_excluded": {
                    "value": self.records_excluded,
                    "source": "screening decisions",
                    "reasons": self.exclusion_reasons,
                },
                "exclusion_rate": {
                    "value": self.exclusion_rate,
                    "formula": "(records_excluded / records_screened) * 100",
                    "unit": "%",
                    "calculated": True,
                },
            },
            "eligibility": {
                "reports_sought": {
                    "value": self.reports_sought,
                    "source": "records passing screening",
                },
                "reports_not_retrieved": {
                    "value": self.reports_not_retrieved,
                    "source": "retrieval failures",
                },
                "reports_assessed": {
                    "value": self.reports_assessed,
                    "source": "full-text review",
                },
                "reports_excluded": {
                    "value": self.reports_excluded,
                    "source": "full-text screening",
                    "reasons": self.reports_exclusion_reasons,
                },
                "retrieval_rate": {
                    "value": self.retrieval_rate,
                    "formula": "((reports_sought - reports_not_retrieved) / reports_sought) * 100",
                    "unit": "%",
                    "calculated": True,
                },
            },
            "inclusion": {
                "studies_included": {
                    "value": self.studies_included,
                    "source": "reports_assessed - reports_excluded",
                },
                "reports_included": {
                    "value": self.reports_included,
                    "source": "included study reports",
                },
            },
            "validation_errors": self.validate() + self.validate_database_totals(),
        }


@dataclass
class PRISMADiagram:
    """PRISMA 2020 flow diagram with visualization."""

    flow: PRISMAFlow
    svg_content: Optional[str] = None  # SVG markup
    png_bytes: Optional[bytes] = None  # PNG for publications
    png_path: Optional[str] = None  # Path to saved PNG file
    width: int = 800  # Diagram width in pixels
    height: int = 1000  # Diagram height in pixels

    def save_png(self, file_path: str) -> None:
        """Save PNG to file.

        Args:
            file_path: Path to save PNG file
        """
        if self.png_bytes:
            with open(file_path, "wb") as f:
                f.write(self.png_bytes)
            self.png_path = file_path

    def save_svg(self, file_path: str) -> None:
        """Save SVG to file.

        Args:
            file_path: Path to save SVG file
        """
        if self.svg_content:
            with open(file_path, "w") as f:
                f.write(self.svg_content)
