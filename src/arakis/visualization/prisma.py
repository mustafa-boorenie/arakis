"""PRISMA 2020 flow diagram generator.

Creates PRISMA-compliant flow diagrams for systematic reviews.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from arakis.models.visualization import PRISMADiagram, PRISMAFlow


class PRISMADiagramGenerator:
    """Generator for PRISMA 2020 flow diagrams."""

    def __init__(self, output_dir: str = "."):
        """Initialize PRISMA diagram generator.

        Args:
            output_dir: Directory to save diagrams
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Styling constants
        self.box_width = 2.5
        self.box_height = 0.8
        self.box_spacing_y = 0.6
        self.box_spacing_x = 0.4
        self.font_size = 9
        self.title_font_size = 11

    def generate(
        self, flow: PRISMAFlow, output_filename: str = "prisma_diagram.png"
    ) -> PRISMADiagram:
        """Generate PRISMA 2020 flow diagram.

        Args:
            flow: PRISMA flow data
            output_filename: Output filename

        Returns:
            PRISMADiagram with generated visualization
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 14))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 14)
        ax.axis("off")

        # Title
        ax.text(
            5,
            13.5,
            "PRISMA 2020 Flow Diagram",
            ha="center",
            va="center",
            fontsize=self.title_font_size + 2,
            fontweight="bold",
        )

        # Current y position
        y = 12.5

        # ==== IDENTIFICATION ====
        ax.text(1, y, "Identification", fontsize=self.title_font_size, fontweight="bold")
        y -= 0.5

        # Database searches
        databases_text = f"Records identified from databases:\nn = {flow.records_identified_total}"
        if flow.records_identified_databases:
            databases_text += "\n" + "\n".join(
                f"{db}: n = {count}" for db, count in flow.records_identified_databases.items()
            )

        self._draw_box(ax, 1.25, y, databases_text)

        # Registers (if any)
        if flow.records_identified_registers > 0:
            self._draw_box(
                ax, 5.5, y, f"Records identified from\nregisters:\nn = {flow.records_identified_registers}"
            )

        y -= self.box_height + 0.3

        # Records removed before screening
        removed_total = (
            flow.records_removed_duplicates
            + flow.records_removed_automated
            + flow.records_removed_other
        )

        if removed_total > 0:
            removed_text = f"Records removed before screening:\n"
            removed_text += f"Duplicate records: n = {flow.records_removed_duplicates}\n"
            if flow.records_removed_automated > 0:
                removed_text += f"Automated tools: n = {flow.records_removed_automated}\n"
            if flow.records_removed_other > 0:
                removed_text += f"Other reasons: n = {flow.records_removed_other}"

            self._draw_exclusion_box(ax, 6.5, y + 0.4, removed_text)

        # Arrow down
        self._draw_arrow(ax, 2.5, y + 0.8, 2.5, y + 0.2)
        y -= self.box_spacing_y

        # ==== SCREENING ====
        ax.text(1, y, "Screening", fontsize=self.title_font_size, fontweight="bold")
        y -= 0.5

        # Records screened
        self._draw_box(ax, 1.25, y, f"Records screened:\nn = {flow.records_screened}")

        # Records excluded
        if flow.records_excluded > 0:
            excluded_text = f"Records excluded:\nn = {flow.records_excluded}"
            if flow.exclusion_reasons:
                excluded_text += "\n" + "\n".join(
                    f"{reason}: n = {count}" for reason, count in flow.exclusion_reasons.items()
                )

            self._draw_exclusion_box(ax, 6.5, y, excluded_text)

        # Arrow down
        self._draw_arrow(ax, 2.5, y - 0.2, 2.5, y - 0.8)
        y -= self.box_height + self.box_spacing_y

        # Reports sought for retrieval
        self._draw_box(ax, 1.25, y, f"Reports sought for retrieval:\nn = {flow.reports_sought}")

        # Reports not retrieved
        if flow.reports_not_retrieved > 0:
            self._draw_exclusion_box(
                ax, 6.5, y, f"Reports not retrieved:\nn = {flow.reports_not_retrieved}"
            )

        # Arrow down
        self._draw_arrow(ax, 2.5, y - 0.2, 2.5, y - 0.8)
        y -= self.box_height + self.box_spacing_y

        # ==== ELIGIBILITY ====
        ax.text(1, y + 0.2, "Included", fontsize=self.title_font_size, fontweight="bold")
        y -= 0.5

        # Reports assessed for eligibility
        self._draw_box(
            ax, 1.25, y, f"Reports assessed for eligibility:\nn = {flow.reports_assessed}"
        )

        # Reports excluded
        if flow.reports_excluded > 0:
            excluded_text = f"Reports excluded:\nn = {flow.reports_excluded}"
            if flow.reports_exclusion_reasons:
                excluded_text += "\n" + "\n".join(
                    f"{reason}: n = {count}"
                    for reason, count in flow.reports_exclusion_reasons.items()
                )

            self._draw_exclusion_box(ax, 6.5, y, excluded_text)

        # Arrow down
        self._draw_arrow(ax, 2.5, y - 0.2, 2.5, y - 0.8)
        y -= self.box_height + self.box_spacing_y

        # ==== INCLUDED ====
        # Studies included
        included_text = f"Studies included:\nn = {flow.studies_included}"
        if flow.reports_included != flow.studies_included:
            included_text += f"\nReports included:\nn = {flow.reports_included}"

        self._draw_box(ax, 1.25, y, included_text, highlight=True)

        plt.tight_layout()

        # Save to file
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")

        # Read PNG bytes
        png_bytes = None
        with open(output_path, "rb") as f:
            png_bytes = f.read()

        plt.close()

        return PRISMADiagram(
            flow=flow, png_bytes=png_bytes, png_path=str(output_path), width=800, height=1000
        )

    def _draw_box(
        self,
        ax,
        x: float,
        y: float,
        text: str,
        highlight: bool = False,
    ) -> None:
        """Draw a flow diagram box.

        Args:
            ax: Matplotlib axes
            x: X position (left edge)
            y: Y position (center)
            text: Text content
            highlight: Whether to highlight the box
        """
        # Box style
        facecolor = "#e3f2fd" if highlight else "#f5f5f5"
        edgecolor = "#1976d2" if highlight else "#757575"
        linewidth = 2 if highlight else 1

        # Draw box
        box = FancyBboxPatch(
            (x, y - self.box_height / 2),
            self.box_width,
            self.box_height,
            boxstyle="round,pad=0.1",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth,
        )
        ax.add_patch(box)

        # Add text
        ax.text(
            x + self.box_width / 2,
            y,
            text,
            ha="center",
            va="center",
            fontsize=self.font_size,
            wrap=True,
        )

    def _draw_exclusion_box(self, ax, x: float, y: float, text: str) -> None:
        """Draw an exclusion box (typically on the right side).

        Args:
            ax: Matplotlib axes
            x: X position (left edge)
            y: Y position (center)
            text: Text content
        """
        # Slightly different styling for exclusion boxes
        box = FancyBboxPatch(
            (x, y - self.box_height / 2),
            self.box_width,
            self.box_height,
            boxstyle="round,pad=0.1",
            facecolor="#ffebee",
            edgecolor="#c62828",
            linewidth=1,
        )
        ax.add_patch(box)

        # Add text
        ax.text(
            x + self.box_width / 2,
            y,
            text,
            ha="center",
            va="center",
            fontsize=self.font_size - 1,
            wrap=True,
        )

    def _draw_arrow(self, ax, x1: float, y1: float, x2: float, y2: float) -> None:
        """Draw an arrow between two points.

        Args:
            ax: Matplotlib axes
            x1: Start x position
            y1: Start y position
            x2: End x position
            y2: End y position
        """
        arrow = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="->",
            color="#424242",
            linewidth=1.5,
            mutation_scale=20,
        )
        ax.add_patch(arrow)

    def generate_simple_text(self, flow: PRISMAFlow) -> str:
        """Generate a simple text representation of PRISMA flow.

        Args:
            flow: PRISMA flow data

        Returns:
            Text representation
        """
        lines = []
        lines.append("PRISMA 2020 Flow Summary")
        lines.append("=" * 50)
        lines.append("")
        lines.append("IDENTIFICATION")
        lines.append(f"  Records identified: {flow.records_identified_total}")
        if flow.records_identified_databases:
            for db, count in flow.records_identified_databases.items():
                lines.append(f"    - {db}: {count}")
        lines.append(f"  Records removed (duplicates): {flow.records_removed_duplicates}")
        lines.append("")
        lines.append("SCREENING")
        lines.append(f"  Records screened: {flow.records_screened}")
        lines.append(f"  Records excluded: {flow.records_excluded}")
        if flow.exclusion_reasons:
            for reason, count in flow.exclusion_reasons.items():
                lines.append(f"    - {reason}: {count}")
        lines.append("")
        lines.append("ELIGIBILITY")
        lines.append(f"  Reports sought: {flow.reports_sought}")
        lines.append(f"  Reports not retrieved: {flow.reports_not_retrieved}")
        lines.append(f"  Reports assessed: {flow.reports_assessed}")
        lines.append(f"  Reports excluded: {flow.reports_excluded}")
        lines.append("")
        lines.append("INCLUDED")
        lines.append(f"  Studies included: {flow.studies_included}")
        lines.append(f"  Reports included: {flow.reports_included}")
        lines.append("")

        return "\n".join(lines)
