"""PRISMA 2020 flow diagram generator.

Creates PRISMA-compliant flow diagrams for systematic reviews.
Uses programmatic SVG generation - NO LLM INVOLVED.
"""

from pathlib import Path
from typing import Literal

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from arakis.models.visualization import PRISMADiagram, PRISMAFlow


class PRISMADiagramGenerator:
    """Generator for PRISMA 2020 flow diagrams.

    Creates PRISMA 2020 compliant flow diagrams programmatically.
    Uses matplotlib to generate both SVG and PNG outputs.
    NO LLM is used - pure code generation for 100% accuracy.
    """

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
        self,
        flow: PRISMAFlow,
        output_filename: str = "prisma_diagram",
        format: Literal["svg", "png", "both"] = "svg",
    ) -> PRISMADiagram:
        """Generate PRISMA 2020 flow diagram.

        Args:
            flow: PRISMA flow data
            output_filename: Output filename (without extension)
            format: Output format - "svg", "png", or "both"

        Returns:
            PRISMADiagram with generated visualization
        """
        # Generate both formats
        svg_content = None
        png_bytes = None
        svg_path = None
        png_path = None

        if format in ("svg", "both"):
            svg_content = self._generate_svg_content(flow)
            svg_path = str(self.output_dir / f"{output_filename}.svg")
            with open(svg_path, "w") as f:
                f.write(svg_content)

        if format in ("png", "both"):
            png_path = str(self.output_dir / f"{output_filename}.png")
            png_bytes = self._generate_png_bytes(flow, png_path)

        return PRISMADiagram(
            flow=flow,
            svg_content=svg_content,
            png_bytes=png_bytes,
            png_path=png_path,
            width=800,
            height=1000,
        )

    def _generate_svg_content(self, flow: PRISMAFlow) -> str:
        """Generate SVG content programmatically.

        Creates a clean SVG PRISMA 2020 flow diagram.
        """
        # SVG dimensions
        width = 800
        height = 1000

        # Colors
        box_fill = "#f5f5f5"
        box_stroke = "#757575"
        highlight_fill = "#e3f2fd"
        highlight_stroke = "#1976d2"
        exclusion_fill = "#ffebee"
        exclusion_stroke = "#c62828"
        arrow_color = "#424242"

        # Box dimensions
        box_w = 200
        box_h = 60
        box_rx = 8

        # Start building SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            '  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
            f'    <polygon points="0 0, 10 3.5, 0 7" fill="{arrow_color}"/>',
            "  </marker>",
            "</defs>",
            "<style>",
            "  .title { font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; }",
            "  .section-title { font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }",
            "  .box-text { font-family: Arial, sans-serif; font-size: 11px; }",
            "  .exclusion-text { font-family: Arial, sans-serif; font-size: 10px; }",
            "</style>",
        ]

        y = 40

        # Title
        svg_parts.append(
            f'<text x="{width / 2}" y="{y}" text-anchor="middle" class="title">PRISMA 2020 Flow Diagram</text>'
        )
        y += 50

        # === IDENTIFICATION ===
        svg_parts.append(f'<text x="50" y="{y}" class="section-title">Identification</text>')
        y += 40

        # Database searches box
        db_text = f"Records identified from databases: n = {flow.records_identified_total}"
        if flow.records_identified_databases:
            for db, count in flow.records_identified_databases.items():
                db_text += f"\\n{db}: n = {count}"

        svg_parts.extend(
            self._draw_box(
                50, y, box_w, box_h * 2, box_rx, box_fill, box_stroke, db_text, "box-text"
            )
        )

        # Registers box (if applicable)
        if flow.records_identified_registers > 0:
            reg_text = f"Records identified from registers: n = {flow.records_identified_registers}"
            svg_parts.extend(
                self._draw_box(
                    300, y, box_w, box_h, box_rx, box_fill, box_stroke, reg_text, "box-text"
                )
            )

        y += box_h * 2 + 20

        # Duplicates removed (exclusion box on right)
        removed_total = (
            flow.records_removed_duplicates
            + flow.records_removed_automated
            + flow.records_removed_other
        )
        if removed_total > 0:
            removed_text = f"Records removed: n = {removed_total}"
            if flow.records_removed_duplicates > 0:
                removed_text += f"\\nDuplicates: {flow.records_removed_duplicates}"
            if flow.records_removed_automated > 0:
                removed_text += f"\\nAutomated: {flow.records_removed_automated}"
            svg_parts.extend(
                self._draw_box(
                    450,
                    y - 40,
                    box_w,
                    box_h,
                    box_rx,
                    exclusion_fill,
                    exclusion_stroke,
                    removed_text,
                    "exclusion-text",
                )
            )
            # Arrow from duplicates box
            svg_parts.append(
                f'<line x1="450" y1="{y - 20}" x2="280" y2="{y - 20}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
            )

        # Arrow down
        svg_parts.append(
            f'<line x1="150" y1="{y - 20}" x2="150" y2="{y}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
        )
        y += 30

        # === SCREENING ===
        svg_parts.append(f'<text x="50" y="{y}" class="section-title">Screening</text>')
        y += 40

        # Records screened
        screened_text = f"Records screened: n = {flow.records_screened}"
        svg_parts.extend(
            self._draw_box(
                50, y, box_w, box_h, box_rx, box_fill, box_stroke, screened_text, "box-text"
            )
        )

        # Records excluded
        if flow.records_excluded > 0:
            excluded_text = f"Records excluded: n = {flow.records_excluded}"
            if flow.exclusion_reasons:
                for reason, count in list(flow.exclusion_reasons.items())[:3]:  # Top 3 reasons
                    excluded_text += f"\\n{reason}: {count}"
            svg_parts.extend(
                self._draw_box(
                    450,
                    y,
                    box_w,
                    box_h,
                    box_rx,
                    exclusion_fill,
                    exclusion_stroke,
                    excluded_text,
                    "exclusion-text",
                )
            )
            # Arrow to exclusion
            svg_parts.append(
                f'<line x1="250" y1="{y + box_h / 2}" x2="450" y2="{y + box_h / 2}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
            )

        # Arrow down
        svg_parts.append(
            f'<line x1="150" y1="{y + box_h}" x2="150" y2="{y + box_h + 20}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
        )
        y += box_h + 30

        # Reports sought
        sought_text = f"Reports sought for retrieval: n = {flow.reports_sought}"
        svg_parts.extend(
            self._draw_box(
                50, y, box_w, box_h, box_rx, box_fill, box_stroke, sought_text, "box-text"
            )
        )

        # Reports not retrieved
        if flow.reports_not_retrieved > 0:
            not_retrieved_text = f"Reports not retrieved: n = {flow.reports_not_retrieved}"
            svg_parts.extend(
                self._draw_box(
                    450,
                    y,
                    box_w,
                    box_h,
                    box_rx,
                    exclusion_fill,
                    exclusion_stroke,
                    not_retrieved_text,
                    "exclusion-text",
                )
            )
            svg_parts.append(
                f'<line x1="250" y1="{y + box_h / 2}" x2="450" y2="{y + box_h / 2}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
            )

        # Arrow down
        svg_parts.append(
            f'<line x1="150" y1="{y + box_h}" x2="150" y2="{y + box_h + 20}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
        )
        y += box_h + 30

        # === ELIGIBILITY ===
        svg_parts.append(f'<text x="50" y="{y}" class="section-title">Eligibility</text>')
        y += 40

        # Reports assessed
        assessed_text = f"Reports assessed for eligibility: n = {flow.reports_assessed}"
        svg_parts.extend(
            self._draw_box(
                50, y, box_w, box_h, box_rx, box_fill, box_stroke, assessed_text, "box-text"
            )
        )

        # Reports excluded
        if flow.reports_excluded > 0:
            reports_excluded_text = f"Reports excluded: n = {flow.reports_excluded}"
            if flow.reports_exclusion_reasons:
                for reason, count in list(flow.reports_exclusion_reasons.items())[:3]:
                    reports_excluded_text += f"\\n{reason}: {count}"
            svg_parts.extend(
                self._draw_box(
                    450,
                    y,
                    box_w,
                    box_h,
                    box_rx,
                    exclusion_fill,
                    exclusion_stroke,
                    reports_excluded_text,
                    "exclusion-text",
                )
            )
            svg_parts.append(
                f'<line x1="250" y1="{y + box_h / 2}" x2="450" y2="{y + box_h / 2}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
            )

        # Arrow down
        svg_parts.append(
            f'<line x1="150" y1="{y + box_h}" x2="150" y2="{y + box_h + 20}" stroke="{arrow_color}" marker-end="url(#arrowhead)"/>'
        )
        y += box_h + 30

        # === INCLUDED ===
        svg_parts.append(f'<text x="50" y="{y}" class="section-title">Included</text>')
        y += 40

        # Studies included (highlighted)
        included_text = f"Studies included: n = {flow.studies_included}"
        if flow.reports_included != flow.studies_included:
            included_text += f"\\nReports included: n = {flow.reports_included}"
        svg_parts.extend(
            self._draw_box(
                50,
                y,
                box_w,
                box_h,
                box_rx,
                highlight_fill,
                highlight_stroke,
                included_text,
                "box-text",
            )
        )

        # Close SVG
        svg_parts.append("</svg>")

        return "\n".join(svg_parts)

    def _draw_box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        rx: int,
        fill: str,
        stroke: str,
        text: str,
        text_class: str,
    ) -> list[str]:
        """Draw an SVG box with text."""
        lines = text.split("\\n")
        text_y = y + h / 2 - (len(lines) - 1) * 7

        svg_parts = [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
        ]

        for i, line in enumerate(lines):
            svg_parts.append(
                f'<text x="{x + w / 2}" y="{text_y + i * 14}" text-anchor="middle" class="{text_class}">{line}</text>'
            )

        return svg_parts

    def _generate_png_bytes(self, flow: PRISMAFlow, output_path: str) -> bytes:
        """Generate PNG using matplotlib."""
        # Temporarily switch to non-interactive backend
        original_backend = matplotlib.get_backend()
        matplotlib.use("Agg")

        try:
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

            y = 12.5

            # === IDENTIFICATION ===
            ax.text(1, y, "Identification", fontsize=self.title_font_size, fontweight="bold")
            y -= 0.5

            databases_text = (
                f"Records identified from databases:\nn = {flow.records_identified_total}"
            )
            if flow.records_identified_databases:
                databases_text += "\n" + "\n".join(
                    f"{db}: n = {count}" for db, count in flow.records_identified_databases.items()
                )
            self._draw_box_matplotlib(ax, 1.25, y, databases_text)

            if flow.records_identified_registers > 0:
                self._draw_box_matplotlib(
                    ax,
                    5.5,
                    y,
                    f"Records identified from\nregisters:\nn = {flow.records_identified_registers}",
                )

            y -= self.box_height + 0.3

            removed_total = (
                flow.records_removed_duplicates
                + flow.records_removed_automated
                + flow.records_removed_other
            )
            if removed_total > 0:
                removed_text = "Records removed:\n"
                removed_text += f"Duplicates: n = {flow.records_removed_duplicates}"
                if flow.records_removed_automated > 0:
                    removed_text += f"\nAutomated: n = {flow.records_removed_automated}"
                self._draw_exclusion_box_matplotlib(ax, 6.5, y + 0.4, removed_text)

            self._draw_arrow_matplotlib(ax, 2.5, y + 0.8, 2.5, y + 0.2)
            y -= self.box_spacing_y

            # === SCREENING ===
            ax.text(1, y, "Screening", fontsize=self.title_font_size, fontweight="bold")
            y -= 0.5

            self._draw_box_matplotlib(
                ax, 1.25, y, f"Records screened:\nn = {flow.records_screened}"
            )

            if flow.records_excluded > 0:
                excluded_text = f"Records excluded:\nn = {flow.records_excluded}"
                if flow.exclusion_reasons:
                    excluded_text += "\n" + "\n".join(
                        f"{reason}: {count}"
                        for reason, count in list(flow.exclusion_reasons.items())[:3]
                    )
                self._draw_exclusion_box_matplotlib(ax, 6.5, y, excluded_text)

            self._draw_arrow_matplotlib(ax, 2.5, y - 0.2, 2.5, y - 0.8)
            y -= self.box_height + self.box_spacing_y

            # Reports sought
            self._draw_box_matplotlib(ax, 1.25, y, f"Reports sought:\nn = {flow.reports_sought}")

            if flow.reports_not_retrieved > 0:
                self._draw_exclusion_box_matplotlib(
                    ax, 6.5, y, f"Not retrieved:\nn = {flow.reports_not_retrieved}"
                )

            self._draw_arrow_matplotlib(ax, 2.5, y - 0.2, 2.5, y - 0.8)
            y -= self.box_height + self.box_spacing_y

            # === ELIGIBILITY ===
            ax.text(1, y + 0.2, "Eligibility", fontsize=self.title_font_size, fontweight="bold")
            y -= 0.5

            self._draw_box_matplotlib(
                ax, 1.25, y, f"Reports assessed:\nn = {flow.reports_assessed}"
            )

            if flow.reports_excluded > 0:
                excluded_text = f"Reports excluded:\nn = {flow.reports_excluded}"
                if flow.reports_exclusion_reasons:
                    excluded_text += "\n" + "\n".join(
                        f"{reason}: {count}"
                        for reason, count in list(flow.reports_exclusion_reasons.items())[:3]
                    )
                self._draw_exclusion_box_matplotlib(ax, 6.5, y, excluded_text)

            self._draw_arrow_matplotlib(ax, 2.5, y - 0.2, 2.5, y - 0.8)
            y -= self.box_height + self.box_spacing_y

            # === INCLUDED ===
            included_text = f"Studies included:\nn = {flow.studies_included}"
            if flow.reports_included != flow.studies_included:
                included_text += f"\nReports: n = {flow.reports_included}"
            self._draw_box_matplotlib(ax, 1.25, y, included_text, highlight=True)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")

            with open(output_path, "rb") as f:
                png_bytes = f.read()

            plt.close()

            return png_bytes

        finally:
            # Restore original backend
            matplotlib.use(original_backend)

    def _draw_box_matplotlib(
        self, ax, x: float, y: float, text: str, highlight: bool = False
    ) -> None:
        """Draw a flow diagram box (matplotlib version)."""
        facecolor = "#e3f2fd" if highlight else "#f5f5f5"
        edgecolor = "#1976d2" if highlight else "#757575"
        linewidth = 2 if highlight else 1

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

        ax.text(
            x + self.box_width / 2,
            y,
            text,
            ha="center",
            va="center",
            fontsize=self.font_size,
            wrap=True,
        )

    def _draw_exclusion_box_matplotlib(self, ax, x: float, y: float, text: str) -> None:
        """Draw an exclusion box (matplotlib version)."""
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

        ax.text(
            x + self.box_width / 2,
            y,
            text,
            ha="center",
            va="center",
            fontsize=self.font_size - 1,
            wrap=True,
        )

    def _draw_arrow_matplotlib(self, ax, x1: float, y1: float, x2: float, y2: float) -> None:
        """Draw an arrow between two points (matplotlib version)."""
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
