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
        """Records remaining after duplicate removal."""
        return self.records_identified_total - self.records_removed_duplicates

    @property
    def exclusion_rate(self) -> float:
        """Percentage of screened records excluded."""
        if self.records_screened == 0:
            return 0.0
        return (self.records_excluded / self.records_screened) * 100

    @property
    def retrieval_rate(self) -> float:
        """Percentage of sought reports successfully retrieved."""
        if self.reports_sought == 0:
            return 0.0
        retrieved = self.reports_sought - self.reports_not_retrieved
        return (retrieved / self.reports_sought) * 100


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
