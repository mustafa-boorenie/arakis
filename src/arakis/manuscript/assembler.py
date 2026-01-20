"""Manuscript assembler for combining workflow outputs into a complete markdown file.

This module provides functionality to assemble all workflow outputs (sections,
tables, figures) into a single, publication-ready markdown manuscript.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Optional

from arakis.models.paper import Paper
from arakis.models.visualization import Figure, PRISMAFlow, Table
from arakis.models.writing import Manuscript, Section


class ManuscriptAssembler:
    """Assembles workflow outputs into a complete manuscript.

    Takes individual section files (introduction, results, etc.), extraction
    results, and figures generated during the workflow, and combines them
    into a single markdown file with properly formatted tables and figures
    at the end.
    """

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize the assembler.

        Args:
            output_dir: Directory containing workflow outputs
        """
        self.output_dir = Path(output_dir)
        self.figures_dir = self.output_dir / "figures"

    def assemble(
        self,
        research_question: str,
        extraction_results: Optional[dict[str, Any]] = None,
        included_papers: Optional[list[Paper]] = None,
        prisma_flow: Optional[PRISMAFlow] = None,
        keywords: Optional[list[str]] = None,
    ) -> tuple[Manuscript, Path]:
        """Assemble a complete manuscript from workflow outputs.

        Args:
            research_question: The systematic review research question (used as title)
            extraction_results: Data extraction results dictionary
            included_papers: List of included papers for references
            prisma_flow: PRISMA flow data for diagram
            keywords: Optional keywords for manuscript

        Returns:
            Tuple of (Manuscript object, path to saved markdown file)
        """
        # Create figures directory and organize figures
        self._organize_figures()

        # Create manuscript
        manuscript = Manuscript(
            title=research_question,
            keywords=keywords or [],
        )

        # Load and add sections
        self._load_sections(manuscript)

        # Generate and add tables
        self._add_tables(manuscript, extraction_results)

        # Add figures
        self._add_figures(manuscript)

        # Add references from included papers
        if included_papers:
            manuscript.add_references(included_papers)

        # Save manuscript
        output_path = self._save_manuscript(manuscript)

        return manuscript, output_path

    def _organize_figures(self) -> None:
        """Organize all figures into the ./figures/ subdirectory."""
        self.figures_dir.mkdir(exist_ok=True)

        # Copy PRISMA diagram
        prisma_src = self.output_dir / "5_prisma_diagram.png"
        if prisma_src.exists():
            prisma_dst = self.figures_dir / "prisma_diagram.png"
            shutil.copy2(prisma_src, prisma_dst)

        # Copy any other plot files
        for pattern in ["forest_plot*.png", "funnel_plot*.png", "*_plot.png"]:
            for src_file in self.output_dir.glob(pattern):
                if src_file.parent != self.figures_dir:
                    dst_file = self.figures_dir / src_file.name
                    if not dst_file.exists():
                        shutil.copy2(src_file, dst_file)

    def _load_sections(self, manuscript: Manuscript) -> None:
        """Load section files and add to manuscript."""
        # Introduction
        intro_file = self.output_dir / "6_introduction.md"
        if intro_file.exists():
            content = intro_file.read_text()
            # Remove the first heading line if present (it duplicates section title)
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).strip()
            manuscript.introduction = Section(
                title="Introduction",
                content=content,
            )

        # Results
        results_file = self.output_dir / "7_results.md"
        if results_file.exists():
            content = results_file.read_text()
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).strip()
            manuscript.results = Section(
                title="Results",
                content=content,
            )

        # Methods (if exists)
        methods_file = self.output_dir / "methods.md"
        if methods_file.exists():
            content = methods_file.read_text()
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).strip()
            manuscript.methods = Section(
                title="Methods",
                content=content,
            )

        # Discussion (if exists)
        discussion_file = self.output_dir / "discussion.md"
        if discussion_file.exists():
            content = discussion_file.read_text()
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).strip()
            manuscript.discussion = Section(
                title="Discussion",
                content=content,
            )

        # Conclusions (if exists)
        conclusions_file = self.output_dir / "conclusions.md"
        if conclusions_file.exists():
            content = conclusions_file.read_text()
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                content = "\n".join(lines[1:]).strip()
            manuscript.conclusions = Section(
                title="Conclusions",
                content=content,
            )

    def _add_tables(
        self,
        manuscript: Manuscript,
        extraction_results: Optional[dict[str, Any]],
    ) -> None:
        """Generate and add tables to manuscript."""
        # Table 1: Study Characteristics
        if extraction_results:
            study_table = self._generate_study_characteristics_table(extraction_results)
            if study_table:
                manuscript.add_table(study_table)

        # Table 2: Risk of Bias (if available)
        rob_file = self.output_dir / "risk_of_bias.json"
        if rob_file.exists():
            rob_table = self._load_risk_of_bias_table(rob_file)
            if rob_table:
                manuscript.add_table(rob_table)

        # Table 3: GRADE Summary of Findings (if available)
        grade_file = self.output_dir / "grade_sof.json"
        if grade_file.exists():
            grade_table = self._load_grade_table(grade_file)
            if grade_table:
                manuscript.add_table(grade_table)

    def _generate_study_characteristics_table(
        self,
        extraction_results: dict[str, Any],
    ) -> Optional[Table]:
        """Generate Table 1: Study Characteristics from extraction results.

        Args:
            extraction_results: Extraction results dictionary

        Returns:
            Table object or None if no data
        """
        extractions = extraction_results.get("extractions", [])
        if not extractions:
            return None

        # Determine columns based on available data across all extractions
        all_keys: set[str] = set()
        for extraction in extractions:
            data = extraction.get("data", {})
            all_keys.update(data.keys())

        # Standard column order (prioritized)
        priority_columns = [
            "author_year",
            "first_author",
            "study_design",
            "country",
            "setting",
            "population",
            "sample_size_total",
            "intervention",
            "comparator",
            "outcomes",
            "follow_up_duration",
        ]

        # Build headers from available columns
        headers = ["Study"]
        column_keys = []

        for col in priority_columns:
            if col in all_keys:
                # Convert key to header name
                header_name = col.replace("_", " ").title()
                if col == "sample_size_total":
                    header_name = "N"
                headers.append(header_name)
                column_keys.append(col)

        # Add remaining columns not in priority list
        remaining = sorted(all_keys - set(priority_columns))
        for col in remaining[:5]:  # Limit additional columns
            header_name = col.replace("_", " ").title()
            headers.append(header_name)
            column_keys.append(col)

        # Build rows
        rows = []
        for extraction in extractions:
            paper_id = extraction.get("paper_id", "Unknown")
            data = extraction.get("data", {})

            # Use author_year if available, otherwise paper_id
            study_name = data.get("author_year") or data.get("first_author") or paper_id
            if study_name == paper_id and "first_author" in data:
                year = data.get("publication_year", "")
                study_name = f"{data['first_author']} ({year})" if year else data["first_author"]

            row = [study_name]
            for key in column_keys:
                value = data.get(key, "NR")  # NR = Not Reported
                if value is None:
                    value = "NR"
                elif isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                else:
                    value = str(value)
                row.append(value)

            rows.append(row)

        if not rows:
            return None

        return Table(
            id="table1",
            title="Table 1: Characteristics of Included Studies",
            caption="Summary of key characteristics of studies included in this systematic review.",
            headers=headers,
            rows=rows,
            footnotes=[
                "NR = Not Reported",
                "N = Total sample size",
            ],
        )

    def _load_risk_of_bias_table(self, rob_file: Path) -> Optional[Table]:
        """Load pre-generated risk of bias table."""
        try:
            with open(rob_file) as f:
                rob_data = json.load(f)

            # If it's a summary with studies
            studies = rob_data.get("studies", [])
            if not studies:
                return None

            # Build table from summary data
            domain_names = rob_data.get("domain_names", [])
            headers = ["Study"] + domain_names + ["Overall"]

            rows = []
            for study in studies:
                row = [study.get("study_name", "Unknown")]
                for domain in study.get("domains", []):
                    row.append(domain.get("judgment", "?"))
                row.append(study.get("overall_judgment", "?"))
                rows.append(row)

            return Table(
                id="table2",
                title="Table 2: Risk of Bias Assessment",
                caption=rob_data.get("caption", "Risk of bias assessment for included studies."),
                headers=headers,
                rows=rows,
                footnotes=rob_data.get("footnotes", []),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _load_grade_table(self, grade_file: Path) -> Optional[Table]:
        """Load pre-generated GRADE Summary of Findings table."""
        try:
            with open(grade_file) as f:
                grade_data = json.load(f)

            # Standard GRADE SoF headers
            headers = [
                "Outcomes",
                "No. of participants (studies)",
                "Relative effect (95% CI)",
                "Anticipated absolute effects",
                "Certainty",
                "Comments",
            ]

            rows = []
            for outcome in grade_data.get("outcomes", []):
                row = [
                    outcome.get("outcome_name", ""),
                    f"{outcome.get('n_participants', '')} ({outcome.get('n_studies', '')} studies)",
                    outcome.get("relative_effect", ""),
                    outcome.get("absolute_effect", ""),
                    outcome.get("certainty", ""),
                    outcome.get("comments", ""),
                ]
                rows.append(row)

            if not rows:
                return None

            return Table(
                id="table3",
                title="Table 3: Summary of Findings (GRADE)",
                caption=grade_data.get(
                    "caption",
                    "GRADE Summary of Findings table for primary outcomes.",
                ),
                headers=headers,
                rows=rows,
                footnotes=grade_data.get(
                    "footnotes",
                    [
                        "GRADE certainty ratings: HIGH, MODERATE, LOW, VERY LOW",
                    ],
                ),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _add_figures(self, manuscript: Manuscript) -> None:
        """Add figures to manuscript."""
        # PRISMA diagram
        prisma_path = self.figures_dir / "prisma_diagram.png"
        if prisma_path.exists():
            manuscript.add_figure(
                Figure(
                    id="fig1",
                    title="Figure 1: PRISMA 2020 Flow Diagram",
                    caption="PRISMA 2020 flow diagram showing the study selection process.",
                    file_path="figures/prisma_diagram.png",
                    figure_type="prisma",
                )
            )

        # Forest plot
        forest_plots = list(self.figures_dir.glob("forest_plot*.png"))
        for i, plot_path in enumerate(forest_plots):
            fig_num = len(manuscript.figures) + 1
            manuscript.add_figure(
                Figure(
                    id=f"fig{fig_num}",
                    title=f"Figure {fig_num}: Forest Plot",
                    caption="Forest plot showing individual study effects and pooled estimate.",
                    file_path=f"figures/{plot_path.name}",
                    figure_type="forest_plot",
                )
            )

        # Funnel plot
        funnel_plots = list(self.figures_dir.glob("funnel_plot*.png"))
        for plot_path in funnel_plots:
            fig_num = len(manuscript.figures) + 1
            manuscript.add_figure(
                Figure(
                    id=f"fig{fig_num}",
                    title=f"Figure {fig_num}: Funnel Plot",
                    caption="Funnel plot for assessment of publication bias.",
                    file_path=f"figures/{plot_path.name}",
                    figure_type="funnel_plot",
                )
            )

    def _save_manuscript(self, manuscript: Manuscript) -> Path:
        """Save manuscript to markdown file.

        Args:
            manuscript: Manuscript object to save

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / "manuscript.md"

        # Generate markdown
        markdown_content = manuscript.to_markdown()

        # Write to file
        output_path.write_text(markdown_content)

        return output_path

    def load_extraction_results(self) -> Optional[dict[str, Any]]:
        """Load extraction results from workflow output.

        Returns:
            Extraction results dictionary or None
        """
        extraction_file = self.output_dir / "3_extraction_results.json"
        if extraction_file.exists():
            with open(extraction_file) as f:
                return json.load(f)
        return None

    def load_included_papers(self) -> list[Paper]:
        """Load included papers from search and screening results.

        Returns:
            List of Paper objects that were included
        """
        papers: list[Paper] = []

        # Load search results
        search_file = self.output_dir / "1_search_results.json"
        if not search_file.exists():
            return papers

        with open(search_file) as f:
            search_data = json.load(f)

        # Load screening decisions
        screening_file = self.output_dir / "2_screening_decisions.json"
        if not screening_file.exists():
            return papers

        with open(screening_file) as f:
            screening_data = json.load(f)

        # Get included paper IDs
        included_ids = set()
        for decision in screening_data:
            if decision.get("status") == "include":
                included_ids.add(decision.get("paper_id"))

        # Build Paper objects for included papers
        for paper_data in search_data:
            if paper_data.get("id") in included_ids:
                try:
                    paper = Paper(
                        id=paper_data.get("id", ""),
                        title=paper_data.get("title", ""),
                        abstract=paper_data.get("abstract"),
                        authors=paper_data.get("authors", []),
                        year=paper_data.get("year"),
                        doi=paper_data.get("doi"),
                        pmid=paper_data.get("pmid"),
                        journal=paper_data.get("journal"),
                        source=paper_data.get("source", "unknown"),
                    )
                    papers.append(paper)
                except Exception:
                    continue

        return papers
