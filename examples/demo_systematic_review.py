"""
Complete Systematic Review Demo

Demonstrates the full Arakis pipeline from search to manuscript writing.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from arakis.orchestrator import SearchOrchestrator
from arakis.agents.screener import ScreeningAgent
from arakis.agents.extractor import DataExtractionAgent
from arakis.agents.intro_writer import IntroductionWriterAgent
from arakis.agents.results_writer import ResultsWriterAgent
from arakis.models.screening import ScreeningCriteria, ScreeningStatus
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType
from arakis.analysis.engine import StatisticalEngine
from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow

console = Console()


class DemoResults:
    """Track demo results."""

    def __init__(self):
        self.stages = {}
        self.start_time = datetime.now()
        self.total_cost = 0.0

    def add_stage(self, name, status, details=None, cost=0.0):
        """Add stage result."""
        self.stages[name] = {
            "status": status,
            "details": details or {},
            "cost": cost,
            "timestamp": datetime.now()
        }
        self.total_cost += cost

    def print_summary(self):
        """Print results summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        table = Table(title="Demo Results Summary", show_header=True, header_style="bold cyan")
        table.add_column("Stage", style="cyan", width=25)
        table.add_column("Status", width=10)
        table.add_column("Cost", justify="right", width=10)
        table.add_column("Details", width=50)

        for name, result in self.stages.items():
            status = result["status"]
            status_icon = "✓" if status == "success" else "✗" if status == "failed" else "⚠"
            status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"

            details_str = ", ".join([f"{k}: {v}" for k, v in result["details"].items()])
            cost_str = f"${result['cost']:.2f}" if result['cost'] > 0 else "FREE"

            table.add_row(
                name,
                f"[{status_color}]{status_icon} {status}[/{status_color}]",
                cost_str,
                details_str
            )

        table.add_row("", "", "", "", end_section=True)
        table.add_row("TOTAL", "", f"[bold]${self.total_cost:.2f}[/bold]", f"Time: {elapsed:.1f}s")

        console.print("\n")
        console.print(table)


async def demo_systematic_review():
    """Run complete systematic review demo."""

    results = DemoResults()

    # Print header
    console.print(Panel.fit(
        "[bold cyan]Arakis Systematic Review Demo[/bold cyan]\n"
        "[white]Complete pipeline demonstration[/white]\n"
        "[dim]Research Question: Effect of aspirin on mortality in sepsis patients[/dim]",
        border_style="cyan"
    ))

    # Create demo directory
    demo_dir = Path("demo_output")
    demo_dir.mkdir(exist_ok=True)

    # ========================================================================
    # STAGE 1: SEARCH
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 1: Search ═══[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Searching PubMed...", total=None)

            orchestrator = SearchOrchestrator()
            search_result = await orchestrator.search_single_database(
                query="aspirin[tiab] AND sepsis[tiab]",
                database="pubmed",
                max_results=20
            )

            progress.update(task, completed=True)

        # Save results
        with open(demo_dir / "1_search_results.json", "w") as f:
            json.dump([asdict(p) for p in search_result.papers], f, indent=2, default=str)

        results.add_stage(
            "Search",
            "success",
            {
                "papers": len(search_result.papers),
                "database": "PubMed",
                "time_ms": search_result.execution_time_ms
            },
            cost=0.0
        )

        console.print(f"  [green]✓[/green] Found {len(search_result.papers)} papers")
        console.print(f"  [dim]Saved to: demo_output/1_search_results.json[/dim]")

    except Exception as e:
        results.add_stage("Search", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Search failed: {e}")
        raise

    # ========================================================================
    # STAGE 2: SCREENING
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 2: Screening ═══[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Screening papers with AI (dual-review)...", total=None)

            agent = ScreeningAgent()
            criteria = ScreeningCriteria(
                inclusion=[
                    "Human adult patients (≥18 years)",
                    "Sepsis or septic shock as primary condition",
                    "Aspirin as intervention",
                    "Mortality or clinical outcomes reported"
                ],
                exclusion=[
                    "Pediatric patients (<18 years)",
                    "Animal or in vitro studies",
                    "Review articles or meta-analyses"
                ]
            )

            # Screen first 5 papers for demo
            papers_to_screen = search_result.papers[:5]
            decisions = await agent.screen_batch(
                papers=papers_to_screen,
                criteria=criteria,
                dual_review=True
            )

            progress.update(task, completed=True)

        # Analyze decisions
        included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
        excluded = [d for d in decisions if d.status == ScreeningStatus.EXCLUDE]
        maybe = [d for d in decisions if d.status == ScreeningStatus.MAYBE]
        conflicts = [d for d in decisions if d.is_conflict]

        # Save decisions
        with open(demo_dir / "2_screening_decisions.json", "w") as f:
            json.dump([asdict(d) for d in decisions], f, indent=2, default=str)

        results.add_stage(
            "Screening",
            "success",
            {
                "screened": len(decisions),
                "included": len(included),
                "excluded": len(excluded),
                "conflicts": len(conflicts)
            },
            cost=len(papers_to_screen) * 0.02
        )

        console.print(f"  [green]✓[/green] Screened {len(decisions)} papers")
        console.print(f"    • Included: [green]{len(included)}[/green]")
        console.print(f"    • Excluded: [red]{len(excluded)}[/red]")
        console.print(f"    • Maybe: [yellow]{len(maybe)}[/yellow]")
        console.print(f"    • Conflicts: {len(conflicts)}")
        console.print(f"  [dim]Saved to: demo_output/2_screening_decisions.json[/dim]")

        # Show example decision
        if included:
            example = included[0]
            console.print(f"\n  [dim]Example included paper:[/dim]")
            console.print(f"  [dim]• Decision: {example.status.value}[/dim]")
            console.print(f"  [dim]• Confidence: {example.confidence:.2f}[/dim]")
            console.print(f"  [dim]• Reason: {example.reason[:80]}...[/dim]")

    except Exception as e:
        results.add_stage("Screening", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Screening failed: {e}")
        raise

    # ========================================================================
    # STAGE 3: EXTRACTION
    # ========================================================================
    if len(included) > 0:
        console.print("\n[bold cyan]═══ Stage 3: Extraction ═══[/bold cyan]")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Extracting data (single-pass mode)...", total=None)

                extractor = DataExtractionAgent()
                schema = ExtractionSchema(
                    name="Demo RCT Schema",
                    description="Extract basic RCT data",
                    fields=[
                        ExtractionField(
                            name="sample_size",
                            description="Total number of participants",
                            field_type=FieldType.NUMERIC,
                            required=True,
                            validation_rules={"min": 1, "max": 100000}
                        ),
                        ExtractionField(
                            name="intervention",
                            description="Intervention description",
                            field_type=FieldType.TEXT,
                            required=True
                        ),
                        ExtractionField(
                            name="primary_outcome",
                            description="Primary outcome measured",
                            field_type=FieldType.TEXT,
                            required=True
                        )
                    ]
                )

                # Extract from first included paper
                included_papers = [p for p in search_result.papers if p.id in [d.paper_id for d in included]]
                paper_to_extract = included_papers[0]

                extraction = await extractor.extract_paper(
                    paper=paper_to_extract,
                    schema=schema,
                    triple_review=False  # Single-pass for demo speed
                )

                progress.update(task, completed=True)

            # Save extraction
            with open(demo_dir / "3_extraction.json", "w") as f:
                json.dump(asdict(extraction), f, indent=2, default=str)

            results.add_stage(
                "Extraction",
                "success",
                {
                    "papers": 1,
                    "fields": len(extraction.data),
                    "quality": f"{extraction.extraction_quality:.2f}"
                },
                cost=0.20
            )

            console.print(f"  [green]✓[/green] Extracted data from 1 paper")
            console.print(f"    • Fields extracted: {len(extraction.data)}")
            console.print(f"    • Quality score: {extraction.extraction_quality:.2f}")
            console.print(f"    • Needs review: {extraction.needs_human_review}")
            console.print(f"  [dim]Saved to: demo_output/3_extraction.json[/dim]")

            # Show extracted data
            console.print(f"\n  [dim]Extracted data:[/dim]")
            for field, value in extraction.data.items():
                console.print(f"  [dim]• {field}: {value}[/dim]")

        except Exception as e:
            results.add_stage("Extraction", "failed", {"error": str(e)})
            console.print(f"  [red]✗[/red] Extraction failed: {e}")
    else:
        console.print("\n[bold cyan]═══ Stage 3: Extraction ═══[/bold cyan]")
        console.print("  [yellow]⚠[/yellow] Skipped (no included papers)")
        results.add_stage("Extraction", "skipped", {"reason": "no included papers"})

    # ========================================================================
    # STAGE 4: ANALYSIS
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 4: Statistical Analysis ═══[/bold cyan]")

    try:
        # Demo with sample data
        console.print("  [dim]Running t-test on sample data...[/dim]")

        engine = StatisticalEngine()
        control = [12.5, 13.2, 11.8, 14.1, 12.9]
        treatment = [15.3, 16.1, 14.8, 15.9, 16.4]

        analysis_result = engine.independent_t_test(control, treatment)

        results.add_stage(
            "Analysis",
            "success",
            {
                "test": "t-test",
                "p_value": f"{analysis_result.p_value:.4f}",
                "significant": analysis_result.is_significant
            },
            cost=0.0
        )

        console.print(f"  [green]✓[/green] Statistical analysis complete")
        console.print(f"    • Test: Independent t-test")
        console.print(f"    • p-value: {analysis_result.p_value:.4f}")
        console.print(f"    • Significant: {analysis_result.is_significant}")
        console.print(f"    • Effect size: {analysis_result.effect_size:.2f}")
        console.print(f"  [dim]Cost: FREE (no LLM)[/dim]")

    except Exception as e:
        results.add_stage("Analysis", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Analysis failed: {e}")

    # ========================================================================
    # STAGE 5: VISUALIZATION
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 5: Visualization ═══[/bold cyan]")

    try:
        console.print("  [dim]Generating PRISMA diagram...[/dim]")

        flow = PRISMAFlow(
            records_identified_total=len(search_result.papers),
            records_identified_databases={"pubmed": len(search_result.papers)},
            records_removed_duplicates=0,
            records_screened=len(decisions),
            records_excluded=len(excluded),
            studies_included=len(included)
        )

        generator = PRISMADiagramGenerator()
        diagram = generator.generate(flow, str(demo_dir / "4_prisma_diagram.png"))

        results.add_stage(
            "Visualization",
            "success",
            {
                "diagram": "PRISMA",
                "format": "PNG (300 DPI)"
            },
            cost=0.0
        )

        console.print(f"  [green]✓[/green] PRISMA diagram generated")
        console.print(f"  [dim]Saved to: demo_output/4_prisma_diagram.png[/dim]")
        console.print(f"  [dim]Cost: FREE (no LLM)[/dim]")

    except Exception as e:
        results.add_stage("Visualization", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Visualization failed: {e}")

    # ========================================================================
    # STAGE 6: WRITING - INTRODUCTION
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 6: Writing (Introduction) ═══[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Writing introduction...", total=None)

            writer = IntroductionWriterAgent()
            intro = await writer.write_complete_introduction(
                research_question="Effect of aspirin on mortality in patients with sepsis",
                inclusion_criteria=criteria.inclusion,
                primary_outcome="mortality"
            )

            progress.update(task, completed=True)

        # Save introduction
        with open(demo_dir / "5_introduction.md", "w") as f:
            f.write(intro.to_markdown())

        results.add_stage(
            "Writing (Intro)",
            "success",
            {
                "subsections": len(intro.subsections),
                "words": intro.total_word_count
            },
            cost=1.00
        )

        console.print(f"  [green]✓[/green] Introduction written")
        console.print(f"    • Subsections: {len(intro.subsections)}")
        console.print(f"    • Word count: {intro.total_word_count}")
        console.print(f"  [dim]Saved to: demo_output/5_introduction.md[/dim]")

    except Exception as e:
        results.add_stage("Writing (Intro)", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Introduction writing failed: {e}")

    # ========================================================================
    # STAGE 7: WRITING - RESULTS
    # ========================================================================
    console.print("\n[bold cyan]═══ Stage 7: Writing (Results) ═══[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Writing results section...", total=None)

            results_writer = ResultsWriterAgent()
            results_section = await results_writer.write_study_selection(
                prisma_flow=flow,
                total_papers_searched=len(search_result.papers),
                screening_summary={
                    "screened": len(decisions),
                    "included": len(included),
                    "excluded": len(excluded)
                }
            )

            progress.update(task, completed=True)

        # Save results
        with open(demo_dir / "6_results.md", "w") as f:
            f.write(results_section.section.to_markdown())

        results.add_stage(
            "Writing (Results)",
            "success",
            {
                "subsections": 1,
                "words": results_section.section.total_word_count
            },
            cost=0.30
        )

        console.print(f"  [green]✓[/green] Results section written")
        console.print(f"    • Word count: {results_section.section.total_word_count}")
        console.print(f"  [dim]Saved to: demo_output/6_results.md[/dim]")

    except Exception as e:
        results.add_stage("Writing (Results)", "failed", {"error": str(e)})
        console.print(f"  [red]✗[/red] Results writing failed: {e}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]Demo Complete![/bold green]\n"
        f"[white]All files saved to: [cyan]demo_output/[/cyan][/white]",
        border_style="green"
    ))

    results.print_summary()

    # List output files
    console.print("\n[bold]Output Files:[/bold]")
    output_files = sorted(demo_dir.glob("*"))
    for file in output_files:
        size = file.stat().st_size
        console.print(f"  • {file.name} [dim]({size:,} bytes)[/dim]")


if __name__ == "__main__":
    asyncio.run(demo_systematic_review())
