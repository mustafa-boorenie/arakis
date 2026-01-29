"""CLI interface for Arakis."""

import asyncio
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="arakis",
    help="AI-powered systematic review pipeline for academic research",
)
console = Console()


def _run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


@app.command()
def search(
    question: str = typer.Argument(..., help="Research question to search for"),
    databases: str = typer.Option(
        "pubmed,openalex,semantic_scholar",
        "--databases",
        "-d",
        help="Comma-separated list of databases to search",
    ),
    max_results: int = typer.Option(100, "--max-results", "-n", help="Maximum results per query"),
    validate: bool = typer.Option(
        False,
        "--validate",
        help="Validate and refine queries based on result counts (slower, more API calls)",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for results (JSON)"
    ),
):
    """
    Search multiple academic databases for a research question.

    Uses AI to generate optimized queries for each database,
    then deduplicates results.
    """
    import json

    from arakis.orchestrator import SearchOrchestrator

    db_list = [d.strip() for d in databases.split(",")]

    console.print(
        Panel.fit(f"[bold blue]Research Question:[/bold blue]\n{question}", title="Arakis Search")
    )

    orchestrator = SearchOrchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        def update_progress(stage: str, detail: str):
            progress.update(task, description=f"{stage}: {detail}")

        try:
            result = _run_async(
                orchestrator.comprehensive_search(
                    research_question=question,
                    databases=db_list,
                    max_results_per_query=max_results,
                    validate_queries=validate,
                    progress_callback=update_progress,
                )
            )
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    # Display results
    console.print("\n[bold green]Search Complete![/bold green]\n")

    # PRISMA flow table
    flow_table = Table(title="PRISMA Flow")
    flow_table.add_column("Stage", style="cyan")
    flow_table.add_column("Count", style="magenta")

    flow_table.add_row("Records Identified", str(result.prisma_flow.total_identified))
    for db, count in result.prisma_flow.records_identified.items():
        flow_table.add_row(f"  └─ {db}", str(count))
    flow_table.add_row("Duplicates Removed", str(result.prisma_flow.duplicates_removed))
    flow_table.add_row("Unique Papers", str(len(result.papers)))

    console.print(flow_table)

    # Papers table (first 10)
    if result.papers:
        papers_table = Table(
            title=f"\nTop Papers (showing {min(10, len(result.papers))} of {len(result.papers)})"
        )
        papers_table.add_column("#", style="dim", width=3)
        papers_table.add_column("Title", max_width=60)
        papers_table.add_column("Year", width=6)
        papers_table.add_column("Source", width=12)

        for i, paper in enumerate(result.papers[:10], 1):
            title = paper.title[:57] + "..." if len(paper.title) > 60 else paper.title
            papers_table.add_row(str(i), title, str(paper.year or "?"), paper.source.value)

        console.print(papers_table)

    # Save to file if requested
    if output:
        output_data = {
            "research_question": question,
            "summary": result.to_dict(),
            "papers": [
                {
                    "id": p.id,
                    "title": p.title,
                    "doi": p.doi,
                    "year": p.year,
                    "authors": [a.name for a in p.authors],
                    "abstract": p.abstract,
                    "source": p.source.value,
                }
                for p in result.papers
            ],
        }
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[dim]Results saved to {output}[/dim]")


@app.command()
def screen(
    input_file: str = typer.Argument(..., help="JSON file from search command"),
    include: str = typer.Option(..., "--include", "-i", help="Inclusion criteria"),
    exclude: str = typer.Option("", "--exclude", "-e", help="Exclusion criteria"),
    dual_review: bool = typer.Option(
        True,
        "--dual-review/--no-dual-review",
        help="Enable dual reviewer mode with conflict detection (default: True)",
    ),
    human_review: bool = typer.Option(
        False, "--human-review", help="Enable human-in-the-loop review (only with --no-dual-review)"
    ),
    batch_size: Optional[int] = typer.Option(
        None,
        "--batch-size",
        "-b",
        help="Number of papers to process concurrently (default: 5 from config)",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Screen papers against inclusion/exclusion criteria.

    Uses AI to evaluate each paper based on title and abstract.
    By default, uses dual-review mode (two independent passes) for higher reliability.

    For single-pass screening with human verification, use: --no-dual-review --human-review
    """
    import json

    from arakis.agents.screener import ScreeningAgent
    from arakis.models.paper import Author, Paper, PaperSource
    from arakis.models.screening import ScreeningCriteria

    # Load papers
    with open(input_file) as f:
        data = json.load(f)

    papers = [
        Paper(
            id=p["id"],
            title=p["title"],
            abstract=p.get("abstract"),
            year=p.get("year"),
            authors=[Author(name=n) for n in p.get("authors", [])],
            doi=p.get("doi"),
            source=PaperSource(p.get("source", "pubmed")),
        )
        for p in data.get("papers", [])
    ]

    if not papers:
        console.print("[yellow]No papers to screen[/yellow]")
        raise typer.Exit(0)

    # Validate parameters
    if human_review and dual_review:
        console.print(
            "[yellow]Warning: --human-review is ignored when --dual-review is enabled.[/yellow]"
        )
        console.print(
            "[yellow]Use --no-dual-review --human-review for human-in-the-loop screening.[/yellow]\n"
        )
        human_review = False

    # Display screening mode
    if dual_review:
        console.print(f"[bold]Screening {len(papers)} papers with dual-review mode...[/bold]")
    elif human_review:
        console.print(
            f"[bold]Screening {len(papers)} papers with human-in-the-loop review...[/bold]"
        )
        console.print("[dim]You will be prompted to review each AI decision.[/dim]")
    else:
        console.print(f"[bold]Screening {len(papers)} papers with single-pass AI...[/bold]")

    console.print()

    criteria = ScreeningCriteria(
        inclusion=[c.strip() for c in include.split(",")],
        exclusion=[c.strip() for c in exclude.split(",")] if exclude else [],
    )

    screener = ScreeningAgent()

    def display_screening_progress(current, total, paper, decision):
        """Display real-time screening progress with decision details."""
        # Truncate title for display
        title_display = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title

        # Status color based on decision
        status_colors = {
            "INCLUDE": "green",
            "EXCLUDE": "red",
            "MAYBE": "yellow",
        }
        status_color = status_colors.get(decision.status.value, "white")

        # Print progress line
        console.print(f"[dim][SCREEN][/dim] Processing paper {current}/{total}: \"{title_display}\"")
        console.print(
            f"[dim][SCREEN][/dim] Decision: [{status_color}]{decision.status.value}[/{status_color}] "
            f"(confidence: {decision.confidence:.2f})"
        )

        # Show matched criteria if any
        matched_criteria = []
        if decision.matched_inclusion:
            matched_criteria.extend(decision.matched_inclusion)
        if matched_criteria:
            console.print(f"[dim][SCREEN][/dim] Matched criteria: {', '.join(matched_criteria)}")

        # Show conflict indicator if dual review had a conflict
        if decision.is_conflict:
            console.print("[dim][SCREEN][/dim] [yellow]⚠ Dual-review conflict detected[/yellow]")

        console.print()  # Empty line between papers

    # Note: Progress bar disabled for human review mode
    if human_review:
        decisions = _run_async(
            screener.screen_batch(
                papers, criteria, dual_review, human_review, None, batch_size=batch_size
            )
        )
    else:
        decisions = _run_async(
            screener.screen_batch(
                papers, criteria, dual_review, human_review, display_screening_progress, batch_size=batch_size
            )
        )

    # Summary
    summary = screener.summarize_screening(decisions)

    summary_table = Table(title="Screening Summary")
    summary_table.add_column("Status", style="cyan")
    summary_table.add_column("Count", style="magenta")

    summary_table.add_row("Included", str(summary["included"]))
    summary_table.add_row("Excluded", str(summary["excluded"]))
    summary_table.add_row("Maybe (needs review)", str(summary["maybe"]))
    if dual_review:
        summary_table.add_row("Conflicts", str(summary["conflicts"]))
    if summary["human_reviewed"] > 0:
        summary_table.add_row("Human Reviewed", str(summary["human_reviewed"]))
        summary_table.add_row("Human Overrides", str(summary["human_overrides"]))
        if summary["human_reviewed"] > 0:
            summary_table.add_row("Override Rate", f"{summary['override_rate']:.1%}")

    console.print(summary_table)

    # Save results
    if output:
        output_data = {
            "criteria": {"inclusion": criteria.inclusion, "exclusion": criteria.exclusion},
            "summary": summary,
            "decisions": [
                {
                    "paper_id": d.paper_id,
                    "status": d.status.value,
                    "reason": d.reason,
                    "confidence": d.confidence,
                    "human_reviewed": d.human_reviewed,
                    "overridden": d.overridden,
                    "ai_decision": d.ai_decision.value if d.ai_decision else None,
                    "human_decision": d.human_decision.value if d.human_decision else None,
                    "human_reason": d.human_reason,
                }
                for d in decisions
            ],
        }
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[dim]Screening results saved to {output}[/dim]")


@app.command()
def fetch(
    input_file: str = typer.Argument(..., help="JSON file with papers"),
    output_dir: str = typer.Option("./papers", "--output", "-o", help="Output directory for PDFs"),
    download: bool = typer.Option(False, "--download", help="Download PDFs (not just URLs)"),
    extract_text: bool = typer.Option(
        False, "--extract-text", help="Extract full text from PDFs (requires --download)"
    ),
    batch_size: Optional[int] = typer.Option(
        None,
        "--batch-size",
        "-b",
        help="Number of papers to fetch concurrently (default: 10 from config)",
    ),
):
    """
    Fetch full-text papers from open access sources.
    """
    import json
    import os

    from arakis.models.paper import Paper, PaperSource
    from arakis.retrieval.fetcher import PaperFetcher

    # Validate parameters
    if extract_text and not download:
        console.print(
            "[yellow]Warning: --extract-text requires --download. Enabling download.[/yellow]"
        )
        download = True

    # Load papers
    with open(input_file) as f:
        data = json.load(f)

    papers = [
        Paper(
            id=p["id"],
            title=p["title"],
            doi=p.get("doi"),
            pmid=p.get("pmid"),
            pmcid=p.get("pmcid"),
            arxiv_id=p.get("arxiv_id"),
            source=PaperSource(p.get("source", "pubmed")),
        )
        for p in data.get("papers", [])
    ]

    if not papers:
        console.print("[yellow]No papers to fetch[/yellow]")
        raise typer.Exit(0)

    action = "Extracting text from" if extract_text else ("Downloading" if download else "Fetching")
    console.print(f"[bold]{action} {len(papers)} papers...[/bold]\n")

    fetcher = PaperFetcher()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Fetching 0/{len(papers)}...", total=len(papers))

        def update(current, total, paper):
            progress.update(task, description=f"Fetching {current}/{total}: {paper.title[:30]}...")
            progress.advance(task)

        results = _run_async(
            fetcher.fetch_batch(papers, download, extract_text, update, batch_size=batch_size)
        )

    # Summary
    summary = fetcher.summarize_batch(results)

    summary_table = Table(title="Fetch Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta")

    summary_table.add_row("Total Papers", str(summary["total"]))
    summary_table.add_row("Successfully Retrieved", str(summary["successful"]))
    summary_table.add_row("Failed", str(summary["failed"]))
    summary_table.add_row("Success Rate", f"{summary['success_rate']:.1%}")

    for source, count in summary.get("by_source", {}).items():
        summary_table.add_row(f"  └─ {source}", str(count))

    console.print(summary_table)

    # Save URLs or download PDFs
    os.makedirs(output_dir, exist_ok=True)

    if download:
        saved = 0
        for result in results:
            if result.success and result.retrieval_result and result.retrieval_result.content:
                filename = f"{result.paper.id}.pdf"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(result.retrieval_result.content)
                saved += 1
        console.print(f"\n[dim]Downloaded {saved} PDFs to {output_dir}[/dim]")

        # Save extracted text if requested
        if extract_text:
            text_data = []
            for result in results:
                if result.success and result.paper.has_full_text:
                    text_data.append(
                        {
                            "paper_id": result.paper.id,
                            "title": result.paper.title,
                            "full_text": result.paper.full_text,
                            "char_count": result.paper.text_length,
                            "extraction_method": result.paper.text_extraction_method,
                            "quality_score": result.paper.text_quality_score,
                            "extracted_at": result.paper.full_text_extracted_at.isoformat()
                            if result.paper.full_text_extracted_at
                            else None,
                        }
                    )

            if text_data:
                text_file = os.path.join(output_dir, "extracted_texts.json")
                with open(text_file, "w") as f:
                    json.dump(text_data, f, indent=2)
                console.print(
                    f"[dim]Extracted text from {len(text_data)} papers saved to {text_file}[/dim]"
                )
    else:
        urls_file = os.path.join(output_dir, "paper_urls.json")
        urls_data = [
            {
                "paper_id": r.paper.id,
                "title": r.paper.title,
                "url": r.pdf_url,
                "source": r.retrieval_result.source_name if r.retrieval_result else None,
            }
            for r in results
            if r.success
        ]
        with open(urls_file, "w") as f:
            json.dump(urls_data, f, indent=2)
        console.print(f"\n[dim]Paper URLs saved to {urls_file}[/dim]")


@app.command()
def extract(
    input_file: str = typer.Argument(..., help="JSON file with screening results"),
    schema: str = typer.Option(
        "auto",
        "--schema",
        "-s",
        help="Extraction schema: auto (detect from papers), rct, cohort, case_control, diagnostic",
    ),
    mode: str = typer.Option(
        "balanced",
        "--mode",
        "-m",
        help="Extraction mode (fast=single-pass, balanced=triple-review)",
    ),
    use_full_text: bool = typer.Option(
        True, "--use-full-text/--no-full-text", help="Use full text if available (default: True)"
    ),
    batch_size: Optional[int] = typer.Option(
        None,
        "--batch-size",
        "-b",
        help="Number of papers to extract concurrently (default: 3 from config)",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Extract structured data from papers using AI.

    By default uses triple-review mode for high reliability and full-text extraction.
    Use --mode fast for single-pass extraction (cheaper, less reliable).
    Use --no-full-text to extract from abstracts only (not recommended).

    Schema is auto-detected from paper titles/abstracts by default:
    - auto: Detect study type from paper content (default)
    - rct: Randomized controlled trials
    - cohort: Cohort/observational studies
    - case_control: Case-control studies
    - diagnostic: Diagnostic accuracy studies
    """
    import json

    from arakis.agents.extractor import DataExtractionAgent
    from arakis.extraction.schemas import detect_schema, get_schema, list_schemas
    from arakis.models.paper import Author, Paper, PaperSource

    # Load papers from screening results
    with open(input_file) as f:
        data = json.load(f)

    # Get included papers only
    included_paper_ids = [
        d["paper_id"] for d in data.get("decisions", []) if d.get("status") == "include"
    ]

    if not included_paper_ids:
        console.print("[yellow]No included papers found in screening results[/yellow]")
        raise typer.Exit(0)

    # Load paper details
    papers_data = data.get("papers", []) if "papers" in data else []
    if not papers_data:
        # Try to load from search results
        search_file = input_file.replace("screening", "search")
        try:
            with open(search_file) as f:
                search_data = json.load(f)
                papers_data = search_data.get("papers", [])
        except FileNotFoundError:
            console.print(
                f"[red]Could not find paper details. Expected papers in {input_file} or {search_file}[/red]"
            )
            raise typer.Exit(1)

    # Filter to included papers
    papers = [
        Paper(
            id=p["id"],
            title=p["title"],
            abstract=p.get("abstract"),
            year=p.get("year"),
            authors=[Author(name=n) for n in p.get("authors", [])],
            doi=p.get("doi"),
            source=PaperSource(p.get("source", "pubmed")),
            journal=p.get("journal"),
            publication_types=p.get("publication_types", []),
            full_text=p.get("full_text"),
            text_extraction_method=p.get("text_extraction_method"),
            text_quality_score=p.get("text_quality_score"),
        )
        for p in papers_data
        if p["id"] in included_paper_ids
    ]

    if not papers:
        console.print("[red]No papers found matching included IDs[/red]")
        raise typer.Exit(1)

    # Check full text availability
    papers_with_full_text = sum(1 for p in papers if p.has_full_text)
    if use_full_text:
        if papers_with_full_text == 0:
            console.print(
                "[yellow]Warning: --use-full-text enabled but no papers have full text. "
                "Using abstracts only.[/yellow]"
            )
            console.print(
                "[dim]Tip: Use 'arakis fetch --download --extract-text' to extract full text first.[/dim]\n"
            )
        else:
            console.print(
                f"[dim]Using full text for {papers_with_full_text}/{len(papers)} papers[/dim]"
            )

    # Get extraction schema (auto-detect or explicit)
    if schema == "auto":
        # Auto-detect schema from paper titles and abstracts
        detection_text = " ".join(
            f"{p.title or ''} {p.abstract or ''}"
            for p in papers[:10]  # Use first 10 papers
        )
        detected_schema_name, confidence = detect_schema(detection_text)
        extraction_schema = get_schema(detected_schema_name)
        console.print(
            f"[dim]Schema: {detected_schema_name} (auto-detected from papers, confidence: {confidence:.0%})[/dim]"
        )
    else:
        try:
            extraction_schema = get_schema(schema)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            console.print("\n[bold]Available schemas:[/bold]")
            for name, desc in list_schemas().items():
                console.print(f"  • {name}: {desc}")
            raise typer.Exit(1)
        console.print(f"[dim]Schema: {extraction_schema.name}[/dim]")

    # Determine mode
    triple_review = mode != "fast"
    mode_desc = "triple-review (high reliability)" if triple_review else "single-pass (fast)"

    console.print(f"\n[bold]Extracting data from {len(papers)} papers with {mode_desc}...[/bold]")
    console.print(f"[dim]Fields: {len(extraction_schema.fields)}[/dim]\n")

    # Create agent
    agent = DataExtractionAgent()

    # Extract
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Extracting 0/{len(papers)}...", total=len(papers))

        def update(current, total):
            progress.update(task, description=f"Extracting {current}/{total}...")
            progress.advance(task)

        result = _run_async(
            agent.extract_batch(
                papers,
                extraction_schema,
                triple_review,
                use_full_text,
                progress_callback=update,
                batch_size=batch_size,
            )
        )

    # Summary
    summary_table = Table(title="Extraction Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta")

    summary_table.add_row("Total Papers", str(result.total_papers))
    summary_table.add_row("Successful", str(result.successful_extractions))
    summary_table.add_row("Needs Review", str(result.papers_needing_review))
    summary_table.add_row("Average Quality", f"{result.average_quality:.2f}")
    summary_table.add_row("Average Confidence", f"{result.average_confidence:.2f}")
    summary_table.add_row("Conflict Rate", f"{result.conflict_rate:.1%}")
    summary_table.add_row("Extraction Time", f"{result.total_time_ms / 1000:.1f}s")
    summary_table.add_row("Estimated Cost", f"${result.estimated_cost:.2f}")

    console.print(summary_table)

    # Show papers needing review
    if result.papers_needing_review > 0:
        console.print(
            f"\n[yellow]{result.papers_needing_review} papers flagged for human review:[/yellow]"
        )
        for extraction in result.get_extractions_needing_review()[:5]:
            console.print(f"  • {extraction.paper_id}")
            if extraction.conflicts:
                console.print(f"    Conflicts: {', '.join(extraction.conflicts[:3])}")
        if result.papers_needing_review > 5:
            console.print(f"  ... and {result.papers_needing_review - 5} more")

    # Save results
    if output:
        output_data = result.to_dict()
        # Add full extraction details
        output_data["papers"] = [
            {
                "paper_id": e.paper_id,
                "data": e.data,
                "confidence": e.confidence,
                "quality": e.extraction_quality,
                "needs_review": e.needs_human_review,
                "conflicts": e.conflicts,
                "low_confidence_fields": e.low_confidence_fields,
                "extraction_time_ms": e.extraction_time_ms,
            }
            for e in result.extractions
        ]
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[dim]Extraction results saved to {output}[/dim]")


@app.command()
def analyze(
    input_file: str = typer.Argument(..., help="JSON file with extraction results"),
    outcome: Optional[str] = typer.Option(None, "--outcome", "-o", help="Outcome to analyze"),
    method: str = typer.Option(
        "random_effects",
        "--method",
        "-m",
        help="Meta-analysis method (random_effects or fixed_effects)",
    ),
    output: Optional[str] = typer.Option(None, "--output", help="Output file for analysis results"),
    figures_dir: str = typer.Option(
        "./figures", "--figures", "-f", help="Directory for saving figures"
    ),
):
    """
    Perform statistical analysis on extracted data.

    Recommends appropriate tests and conducts meta-analysis if feasible.
    """
    import json
    from datetime import datetime

    from arakis.analysis.meta_analysis import MetaAnalysisEngine
    from arakis.analysis.recommender import AnalysisRecommenderAgent
    from arakis.analysis.visualizer import VisualizationGenerator
    from arakis.models.analysis import AnalysisMethod, EffectMeasure, StudyData
    from arakis.models.extraction import ExtractionResult

    # Load extraction results
    with open(input_file) as f:
        data = json.load(f)

    # Convert to ExtractionResult
    try:
        extraction_result = ExtractionResult.from_dict(data)
    except Exception as e:
        console.print(f"[red]Error loading extraction results: {e}[/red]")
        raise typer.Exit(1)

    if extraction_result.total_papers == 0:
        console.print("[yellow]No papers found in extraction results[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Analyzing {extraction_result.total_papers} papers...[/bold]\n")

    # Step 1: Get recommendations
    console.print("[bold cyan]Step 1:[/bold cyan] Getting statistical test recommendations...")
    recommender = AnalysisRecommenderAgent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing data characteristics...", total=None)
        recommendation = _run_async(recommender.recommend_tests(extraction_result, outcome))

    # Display recommendations
    rec_table = Table(title="Recommended Tests")
    rec_table.add_column("Test", style="cyan")
    rec_table.add_column("Type", style="magenta")
    rec_table.add_column("Priority", style="yellow")

    for test in recommendation.recommended_tests:
        rec_table.add_row(
            test.test_name.replace("_", " ").title(),
            test.test_type.value,
            test.parameters.get("priority", "N/A"),
        )

    console.print(rec_table)
    console.print(f"\n[bold]Rationale:[/bold] {recommendation.rationale}\n")

    # Display warnings
    if recommendation.warnings:
        console.print("[yellow]⚠ Warnings:[/yellow]")
        for warning in recommendation.warnings:
            console.print(f"  • {warning}")
        console.print()

    # Step 2: Perform meta-analysis if feasible
    if recommendation.data_characteristics.get("meta_analysis_feasible", False):
        console.print("[bold cyan]Step 2:[/bold cyan] Performing meta-analysis...")

        # Prepare study data from extractions
        studies = []
        # Track categorical variables for subgroup analysis
        # Common subgroup variables from extraction schemas
        subgroup_variables = [
            "study_design",
            "control_type",
            "funding_source",
            "allocation_concealment",
            "cohort_type",
        ]
        study_subgroups: dict[str, dict[str, str]] = {}  # study_id -> {variable: value}

        for paper in extraction_result.papers:
            # Try to extract relevant data
            study = StudyData(
                study_id=paper.paper_id,
                study_name=paper.paper_id,
                sample_size=paper.data.get("sample_size_total"),
                intervention_n=paper.data.get("sample_size_intervention"),
                control_n=paper.data.get("sample_size_control"),
                intervention_mean=paper.data.get("intervention_mean"),
                intervention_sd=paper.data.get("intervention_sd"),
                control_mean=paper.data.get("control_mean"),
                control_sd=paper.data.get("control_sd"),
                intervention_events=paper.data.get("intervention_events"),
                control_events=paper.data.get("control_events"),
            )
            studies.append(study)

            # Collect subgroup variable values for this study
            study_subgroups[paper.paper_id] = {}
            for var in subgroup_variables:
                value = paper.data.get(var)
                if value is not None and isinstance(value, str) and value.strip():
                    study_subgroups[paper.paper_id][var] = value.strip()

        # Determine effect measure
        has_continuous = any(s.intervention_mean is not None for s in studies)
        has_binary = any(s.intervention_events is not None for s in studies)

        if has_continuous:
            effect_measure = EffectMeasure.MEAN_DIFFERENCE
        elif has_binary:
            effect_measure = EffectMeasure.ODDS_RATIO
        else:
            console.print("[yellow]Insufficient data for meta-analysis[/yellow]")
            raise typer.Exit(0)

        # Run meta-analysis
        analysis_method = (
            AnalysisMethod.RANDOM_EFFECTS
            if method == "random_effects"
            else AnalysisMethod.FIXED_EFFECTS
        )
        meta_engine = MetaAnalysisEngine()

        try:
            meta_result = meta_engine.calculate_pooled_effect(
                studies=studies, method=analysis_method, effect_measure=effect_measure
            )

            # Display results
            meta_table = Table(title="Meta-Analysis Results")
            meta_table.add_column("Metric", style="cyan")
            meta_table.add_column("Value", style="magenta")

            meta_table.add_row("Studies Included", str(meta_result.studies_included))
            meta_table.add_row("Total Sample Size", str(meta_result.total_sample_size))
            meta_table.add_row("Pooled Effect", f"{meta_result.pooled_effect:.3f}")
            meta_table.add_row(
                "95% CI",
                f"[{meta_result.confidence_interval.lower:.3f}, {meta_result.confidence_interval.upper:.3f}]",
            )
            meta_table.add_row("P-value", f"{meta_result.p_value:.4f}")
            meta_table.add_row("Significant", "Yes ✓" if meta_result.is_significant else "No")
            meta_table.add_row("I² (Heterogeneity)", f"{meta_result.heterogeneity.i_squared:.1f}%")
            meta_table.add_row("Tau²", f"{meta_result.heterogeneity.tau_squared:.3f}")
            meta_table.add_row("Q-statistic", f"{meta_result.heterogeneity.q_statistic:.2f}")
            meta_table.add_row("Q P-value", f"{meta_result.heterogeneity.q_p_value:.4f}")

            console.print(meta_table)

            # Interpretation
            if meta_result.has_high_heterogeneity:
                console.print("\n[yellow]⚠ Substantial heterogeneity detected (I² > 50%)[/yellow]")
                console.print(
                    "[dim]Consider subgroup analysis or investigate sources of heterogeneity[/dim]"
                )

            # Step 3: Generate visualizations
            console.print("\n[bold cyan]Step 3:[/bold cyan] Generating visualizations...")
            visualizer = VisualizationGenerator(output_dir=figures_dir)

            # Forest plot
            forest_path = visualizer.create_forest_plot(meta_result, "forest_plot.png")
            console.print(f"  ✓ Forest plot saved to {forest_path}")
            meta_result.forest_plot_path = forest_path

            # Funnel plot
            if len(studies) >= 5:  # Need at least 5 studies for meaningful funnel plot
                funnel_path = visualizer.create_funnel_plot(meta_result, "funnel_plot.png")
                console.print(f"  ✓ Funnel plot saved to {funnel_path}")
                meta_result.funnel_plot_path = funnel_path

                # Egger's test if ≥10 studies
                if len(studies) >= 10:
                    try:
                        egger_p = meta_engine.egger_test(studies)
                        meta_result.egger_test_p_value = egger_p
                        console.print(f"  ✓ Egger's test p-value: {egger_p:.4f}")
                        if egger_p < 0.05:
                            console.print(
                                "    [yellow]⚠ Significant publication bias detected[/yellow]"
                            )
                    except Exception as e:
                        console.print(f"    [dim]Egger's test failed: {e}[/dim]")

            # Step 4: Subgroup analysis (when applicable)
            # Requires: ≥4 studies total, and at least 2 subgroups with ≥2 studies each
            subgroup_results: dict[str, dict[str, Any]] = {}
            if len(studies) >= 4:
                console.print("\n[bold cyan]Step 4:[/bold cyan] Checking for applicable subgroup analyses...")

                # Build mapping of study_id to StudyData for quick lookup
                study_by_id = {s.study_id: s for s in studies}

                # Check each subgroup variable
                for var_name in subgroup_variables:
                    # Collect values for this variable across studies
                    var_values: dict[str, list[StudyData]] = {}
                    for study_id, subgroup_vals in study_subgroups.items():
                        if var_name in subgroup_vals and study_id in study_by_id:
                            value = subgroup_vals[var_name]
                            if value not in var_values:
                                var_values[value] = []
                            var_values[value].append(study_by_id[study_id])

                    # Check if subgroup analysis is applicable:
                    # Need at least 2 subgroups, each with at least 2 studies
                    valid_subgroups = {k: v for k, v in var_values.items() if len(v) >= 2}
                    if len(valid_subgroups) >= 2:
                        console.print(f"\n  [bold]Subgroup analysis by {var_name.replace('_', ' ').title()}:[/bold]")

                        try:
                            # Create subgroup function for this variable
                            def get_subgroup_value(study: StudyData, var: str = var_name) -> str:
                                return study_subgroups.get(study.study_id, {}).get(var, "Unknown")

                            # Perform subgroup analysis
                            subgroup_result = meta_engine.subgroup_analysis(
                                studies=studies,
                                subgroup_func=get_subgroup_value,
                                method=analysis_method,
                                effect_measure=effect_measure,
                            )

                            # Filter to only valid subgroups (exclude "Unknown")
                            subgroup_result = {k: v for k, v in subgroup_result.items() if k != "Unknown"}

                            if len(subgroup_result) >= 2:
                                # Display subgroup results
                                subgroup_table = Table(show_header=True, header_style="bold")
                                subgroup_table.add_column("Subgroup", style="cyan")
                                subgroup_table.add_column("N", justify="right")
                                subgroup_table.add_column("Effect", justify="right")
                                subgroup_table.add_column("95% CI", justify="center")
                                subgroup_table.add_column("P-value", justify="right")
                                subgroup_table.add_column("I²", justify="right")

                                for subgroup_name, result in subgroup_result.items():
                                    subgroup_table.add_row(
                                        subgroup_name.replace("_", " ").title(),
                                        str(result.studies_included),
                                        f"{result.pooled_effect:.3f}",
                                        f"[{result.confidence_interval.lower:.3f}, {result.confidence_interval.upper:.3f}]",
                                        f"{result.p_value:.4f}",
                                        f"{result.heterogeneity.i_squared:.1f}%",
                                    )

                                console.print(subgroup_table)

                                # Store results for output
                                subgroup_results[var_name] = {
                                    "variable": var_name,
                                    "subgroups": {
                                        name: {
                                            "studies_included": int(r.studies_included),
                                            "pooled_effect": float(r.pooled_effect),
                                            "confidence_interval": {
                                                "lower": float(r.confidence_interval.lower),
                                                "upper": float(r.confidence_interval.upper),
                                            },
                                            "p_value": float(r.p_value),
                                            "is_significant": bool(r.is_significant),
                                            "heterogeneity": {
                                                "i_squared": float(r.heterogeneity.i_squared),
                                                "tau_squared": float(r.heterogeneity.tau_squared),
                                            },
                                        }
                                        for name, r in subgroup_result.items()
                                    },
                                }

                                # Store in meta_result for future use
                                meta_result.subgroup_analyses.append(subgroup_results[var_name])
                            else:
                                console.print(f"    [dim]Insufficient valid subgroups for {var_name}[/dim]")

                        except Exception as e:
                            console.print(f"    [dim]Subgroup analysis for {var_name} failed: {e}[/dim]")

                if not subgroup_results:
                    console.print("  [dim]No applicable subgroup analyses (need ≥2 subgroups with ≥2 studies each)[/dim]")

            # Save results
            if output:
                output_data = {
                    "analysis_timestamp": datetime.now().isoformat(),
                    "input_file": input_file,
                    "outcome": outcome,
                    "recommendation": {
                        "recommended_tests": [
                            {
                                "test_name": t.test_name,
                                "test_type": t.test_type.value,
                                "description": t.description,
                                "parameters": t.parameters,
                            }
                            for t in recommendation.recommended_tests
                        ],
                        "rationale": recommendation.rationale,
                        "data_characteristics": recommendation.data_characteristics,
                        "assumptions_to_check": recommendation.assumptions_checked,
                        "warnings": recommendation.warnings,
                    },
                    "meta_analysis": {
                        "outcome_name": meta_result.outcome_name,
                        "studies_included": int(meta_result.studies_included),
                        "total_sample_size": int(meta_result.total_sample_size),
                        "pooled_effect": float(meta_result.pooled_effect),
                        "confidence_interval": {
                            "lower": float(meta_result.confidence_interval.lower),
                            "upper": float(meta_result.confidence_interval.upper),
                            "level": float(meta_result.confidence_interval.level),
                        },
                        "p_value": float(meta_result.p_value),
                        "is_significant": bool(meta_result.is_significant),
                        "effect_measure": meta_result.effect_measure.value,
                        "analysis_method": meta_result.analysis_method.value,
                        "heterogeneity": {
                            "i_squared": float(meta_result.heterogeneity.i_squared),
                            "tau_squared": float(meta_result.heterogeneity.tau_squared),
                            "q_statistic": float(meta_result.heterogeneity.q_statistic),
                            "q_p_value": float(meta_result.heterogeneity.q_p_value),
                        },
                        "forest_plot": meta_result.forest_plot_path,
                        "funnel_plot": meta_result.funnel_plot_path,
                        "egger_test_p_value": float(meta_result.egger_test_p_value)
                        if meta_result.egger_test_p_value is not None
                        else None,
                        "studies": [
                            {
                                "study_id": s.study_id,
                                "effect": float(s.effect) if s.effect is not None else None,
                                "standard_error": float(s.standard_error)
                                if s.standard_error is not None
                                else None,
                                "weight": float(s.weight) if s.weight is not None else None,
                                "sample_size": int(s.sample_size)
                                if s.sample_size is not None
                                else None,
                            }
                            for s in meta_result.studies
                        ],
                        "subgroup_analyses": list(subgroup_results.values()) if subgroup_results else [],
                    },
                }

                with open(output, "w") as f:
                    json.dump(output_data, f, indent=2)
                console.print(f"\n[dim]Analysis results saved to {output}[/dim]")

        except Exception as e:
            console.print(f"[red]Meta-analysis failed: {e}[/red]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")

    else:
        console.print("\n[yellow]Meta-analysis not feasible with current data[/yellow]")
        console.print("[dim]Reasons:[/dim]")
        for warning in recommendation.warnings:
            console.print(f"  • {warning}")

        # Perform narrative synthesis instead
        console.print("\n[bold cyan]Performing narrative synthesis instead...[/bold cyan]")

        from arakis.analysis.narrative_synthesis import NarrativeSynthesizer, SynthesisConfig

        config = SynthesisConfig(output_dir=figures_dir)
        synthesizer = NarrativeSynthesizer(config=config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Synthesizing findings narratively...", total=None)
            synthesis_result = synthesizer.synthesize(
                extraction_result=extraction_result,
                outcome=outcome,
                meta_analysis_barriers=recommendation.warnings,
            )

        # Display narrative synthesis results
        console.print("\n[bold]Narrative Synthesis Results[/bold]\n")

        # Summary table
        summary_table = Table(title="Synthesis Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")

        summary_table.add_row("Studies Included", str(synthesis_result.studies_included))
        summary_table.add_row("Total Sample Size", str(synthesis_result.total_sample_size))
        summary_table.add_row("Confidence in Evidence", synthesis_result.confidence_in_evidence.title())

        if synthesis_result.vote_count:
            vc = synthesis_result.vote_count
            summary_table.add_row(
                "Effect Direction",
                f"{vc.positive} positive, {vc.negative} negative, {vc.null} null, {vc.mixed} mixed"
            )
            summary_table.add_row("Predominant Direction", vc.predominant_direction.title())
            summary_table.add_row("Consistency", vc.consistency.title())

        console.print(summary_table)

        # Summary of findings
        console.print(f"\n[bold]Summary of Findings:[/bold]")
        console.print(synthesis_result.summary_of_findings)

        # Heterogeneity explanation
        if synthesis_result.heterogeneity_explanation:
            console.print(f"\n[bold]Heterogeneity:[/bold]")
            console.print(synthesis_result.heterogeneity_explanation)

        # Evidence quality
        if synthesis_result.evidence_quality_assessment:
            console.print(f"\n[bold]Evidence Quality:[/bold]")
            console.print(synthesis_result.evidence_quality_assessment)

        # Patterns identified
        if synthesis_result.patterns_identified:
            console.print("\n[bold]Patterns Identified:[/bold]")
            for pattern in synthesis_result.patterns_identified:
                console.print(f"  • {pattern}")

        # Inconsistencies
        if synthesis_result.inconsistencies:
            console.print("\n[yellow]Inconsistencies:[/yellow]")
            for inconsistency in synthesis_result.inconsistencies:
                console.print(f"  • {inconsistency}")

        # Gaps in evidence
        if synthesis_result.gaps_in_evidence:
            console.print("\n[yellow]Gaps in Evidence:[/yellow]")
            for gap in synthesis_result.gaps_in_evidence:
                console.print(f"  • {gap}")

        # Display study-level summary table
        if synthesis_result.study_summaries:
            console.print("\n")
            study_table = Table(title="Study-Level Summary")
            study_table.add_column("Study", style="cyan", max_width=30)
            study_table.add_column("N", style="magenta")
            study_table.add_column("Design", style="blue")
            study_table.add_column("Direction", style="yellow")
            study_table.add_column("Magnitude", style="green")

            for study in synthesis_result.study_summaries:
                # Determine direction color
                direction = study.effect_direction or "unknown"
                if direction == "positive":
                    direction_display = "[green]Positive[/green]"
                elif direction == "negative":
                    direction_display = "[red]Negative[/red]"
                elif direction == "null":
                    direction_display = "[dim]Null[/dim]"
                else:
                    direction_display = "[yellow]Mixed[/yellow]"

                study_table.add_row(
                    study.study_id[:30],
                    str(study.sample_size) if study.sample_size else "NR",
                    study.study_design or "NR",
                    direction_display,
                    study.effect_magnitude or "unknown",
                )

            console.print(study_table)

        # Effect direction chart
        if synthesis_result.effect_direction_chart_path:
            console.print(f"\n[dim]Effect direction chart saved to {synthesis_result.effect_direction_chart_path}[/dim]")

        # Save results
        if output:
            output_data = {
                "analysis_type": "narrative_synthesis",
                "timestamp": datetime.now().isoformat(),
                "input_file": input_file,
                "recommendation": {
                    "recommended_tests": [
                        {"name": t.test_name, "type": t.test_type.value}
                        for t in recommendation.recommended_tests
                    ],
                    "rationale": recommendation.rationale,
                    "data_characteristics": recommendation.data_characteristics,
                    "warnings": recommendation.warnings,
                },
                "narrative_synthesis": synthesis_result.to_dict(),
            }

            with open(output, "w") as f:
                json.dump(output_data, f, indent=2)
            console.print(f"\n[dim]Narrative synthesis results saved to {output}[/dim]")


@app.command()
def prisma_diagram(
    input_file: str = typer.Argument(..., help="JSON file with search/screening results"),
    output: str = typer.Option("prisma_diagram.png", "--output", "-o", help="Output PNG file"),
):
    """
    Generate PRISMA 2020 flow diagram from search/screening results.
    """
    import json

    from arakis.models.visualization import PRISMAFlow
    from arakis.visualization.prisma import PRISMADiagramGenerator

    # Load data
    with open(input_file) as f:
        data = json.load(f)

    # Extract PRISMA flow data
    # Check if this is search results or screening results
    if "summary" in data and "papers" in data:
        # Search results format
        summary = data.get("summary", {})
        prisma_data = summary.get("prisma_flow", {})

        flow = PRISMAFlow(
            records_identified_total=prisma_data.get("total_identified", 0),
            records_identified_databases=prisma_data.get("records_identified", {}),
            records_removed_duplicates=prisma_data.get("duplicates_removed", 0),
            records_screened=len(data.get("papers", [])),
        )
    elif "decisions" in data:
        # Screening results format
        decisions = data.get("decisions", [])
        summary = data.get("summary", {})

        # Count screening outcomes
        included = sum(1 for d in decisions if d.get("status") == "include")
        excluded = sum(1 for d in decisions if d.get("status") == "exclude")
        maybe = sum(1 for d in decisions if d.get("status") == "maybe")

        flow = PRISMAFlow(
            records_identified_total=len(decisions),
            records_screened=len(decisions),
            records_excluded=excluded,
            reports_sought=included + maybe,
            reports_assessed=included + maybe,
            studies_included=included,
            reports_included=included,
        )
    else:
        console.print("[red]Could not parse PRISMA flow data from input file[/red]")
        raise typer.Exit(1)

    console.print("[bold]Generating PRISMA diagram...[/bold]\n")

    # Generate diagram
    generator = PRISMADiagramGenerator(output_dir=".")
    generator.generate(flow, output)

    # Display summary
    summary_table = Table(title="PRISMA Flow Summary")
    summary_table.add_column("Stage", style="cyan")
    summary_table.add_column("Count", style="magenta")

    summary_table.add_row("Records Identified", str(flow.records_identified_total))
    summary_table.add_row("Duplicates Removed", str(flow.records_removed_duplicates))
    summary_table.add_row("Records Screened", str(flow.records_screened))
    summary_table.add_row("Records Excluded", str(flow.records_excluded))
    summary_table.add_row("Studies Included", str(flow.studies_included))

    console.print(summary_table)
    console.print(f"\n[dim]PRISMA diagram saved to {output}[/dim]")


@app.command()
def write_results(
    search_file: str = typer.Option(..., "--search", "-s", help="Search results JSON"),
    screening_file: str = typer.Option(..., "--screening", "-c", help="Screening results JSON"),
    analysis_file: Optional[str] = typer.Option(
        None, "--analysis", "-a", help="Analysis results JSON"
    ),
    outcome: str = typer.Option("primary outcome", "--outcome", "-o", help="Outcome name"),
    output: Optional[str] = typer.Option(None, "--output", help="Output markdown file"),
):
    """
    Write results section for systematic review manuscript.

    Generates study selection, characteristics, and synthesis subsections.
    """
    import json

    from arakis.agents.results_writer import ResultsWriterAgent
    from arakis.models.analysis import (
        AnalysisMethod,
        ConfidenceInterval,
        EffectMeasure,
        Heterogeneity,
        MetaAnalysisResult,
    )
    from arakis.models.paper import Author, Paper, PaperSource
    from arakis.models.visualization import PRISMAFlow

    # Load search results
    console.print("[bold]Loading data...[/bold]")
    with open(search_file) as f:
        search_data = json.load(f)

    # Load screening results
    with open(screening_file) as f:
        screening_data = json.load(f)

    # Extract PRISMA flow
    summary = search_data.get("summary", {})
    prisma_data = summary.get("prisma_flow", {})

    screening_summary = screening_data.get("summary", {})

    flow = PRISMAFlow(
        records_identified_total=prisma_data.get("total_identified", 0),
        records_identified_databases=prisma_data.get("records_identified", {}),
        records_removed_duplicates=prisma_data.get("duplicates_removed", 0),
        records_screened=len(screening_data.get("decisions", [])),
        records_excluded=screening_summary.get("excluded", 0),
        reports_sought=screening_summary.get("included", 0),
        reports_assessed=screening_summary.get("included", 0),
        studies_included=screening_summary.get("included", 0),
        reports_included=screening_summary.get("included", 0),
    )

    # Extract included papers
    included_ids = [
        d["paper_id"] for d in screening_data.get("decisions", []) if d.get("status") == "include"
    ]

    papers = [
        Paper(
            id=p["id"],
            title=p["title"],
            year=p.get("year"),
            journal=p.get("journal"),
            authors=[Author(name=n) for n in p.get("authors", [])],
            doi=p.get("doi"),
            source=PaperSource(p.get("source", "pubmed")),
        )
        for p in search_data.get("papers", [])
        if p["id"] in included_ids
    ]

    # Load meta-analysis if available
    meta_result = None
    if analysis_file:
        with open(analysis_file) as f:
            analysis_data = json.load(f)

        if "meta_analysis" in analysis_data:
            ma = analysis_data["meta_analysis"]
            meta_result = MetaAnalysisResult(
                outcome_name=ma["outcome_name"],
                studies_included=ma["studies_included"],
                total_sample_size=ma["total_sample_size"],
                pooled_effect=ma["pooled_effect"],
                confidence_interval=ConfidenceInterval(
                    lower=ma["confidence_interval"]["lower"],
                    upper=ma["confidence_interval"]["upper"],
                    level=ma["confidence_interval"]["level"],
                ),
                z_statistic=0.0,  # Not saved in JSON, recalculate if needed
                p_value=ma["p_value"],
                effect_measure=EffectMeasure(ma["effect_measure"]),
                analysis_method=AnalysisMethod(ma["analysis_method"]),
                heterogeneity=Heterogeneity(
                    i_squared=ma["heterogeneity"]["i_squared"],
                    tau_squared=ma["heterogeneity"]["tau_squared"],
                    q_statistic=ma["heterogeneity"]["q_statistic"],
                    q_p_value=ma["heterogeneity"]["q_p_value"],
                ),
                studies=[],  # Studies not needed for writing
            )

    # Write results section
    console.print("[bold cyan]Writing results section...[/bold cyan]\n")

    writer = ResultsWriterAgent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating results section...", total=None)
        results_section = _run_async(
            writer.write_complete_results_section(
                prisma_flow=flow,
                included_papers=papers,
                meta_analysis_result=meta_result,
                outcome_name=outcome,
            )
        )

    # Display results
    console.print("\n[bold green]Results Section Generated![/bold green]\n")

    results_table = Table(title="Section Summary")
    results_table.add_column("Subsection", style="cyan")
    results_table.add_column("Word Count", style="magenta")

    for subsection in results_section.subsections:
        results_table.add_row(subsection.title, str(subsection.word_count))

    results_table.add_row("[bold]Total[/bold]", f"[bold]{results_section.total_word_count}[/bold]")

    console.print(results_table)

    # Display preview
    console.print("\n[bold]Preview:[/bold]")
    preview_lines = results_section.to_markdown().split("\n")[:20]
    console.print("\n".join(preview_lines))
    if len(results_section.to_markdown().split("\n")) > 20:
        console.print("[dim]... (truncated)[/dim]")

    # Save to file
    if output:
        with open(output, "w") as f:
            f.write(results_section.to_markdown())
        console.print(f"\n[dim]Results section saved to {output}[/dim]")


@app.command()
def write_intro(
    research_question: str = typer.Argument(..., help="Research question for the review"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output markdown file"),
    literature: Optional[str] = typer.Option(
        None, "--literature", "-l", help="JSON file with relevant papers for context"
    ),
    use_rag: bool = typer.Option(
        False, "--use-rag", help="Use RAG system to retrieve literature context"
    ),
    use_perplexity: bool = typer.Option(
        True, "--use-web-search/--no-web-search", help="Use OpenAI web search for literature research (default: enabled)"
    ),
    save_references: bool = typer.Option(
        True, "--save-references/--no-references", help="Save references to separate file"
    ),
):
    """
    Write introduction section for a systematic review.

    Generates background, rationale, and objectives subsections.
    Uses OpenAI web search by default to fetch relevant background literature
    (separate from systematic review search results).
    """
    import json

    from arakis.agents.intro_writer import IntroductionWriterAgent
    from arakis.models.paper import Paper
    from arakis.rag import Retriever

    console.print("[bold]Writing Introduction Section...[/bold]\n")

    # Check OpenAI web search configuration
    writer = IntroductionWriterAgent()
    if use_perplexity:  # Parameter still named use_perplexity for backward compatibility
        if writer.literature_client.is_configured:
            console.print("[cyan]Using OpenAI web search for literature research[/cyan]\n")
        else:
            console.print(
                "[yellow]Warning: OpenAI API key not configured. "
                "Set OPENAI_API_KEY in your environment.[/yellow]\n"
            )
            use_perplexity = False

    # Load literature context if provided
    papers = None
    if literature:
        with open(literature) as f:
            data = json.load(f)
        papers = [Paper(**p) for p in data.get("papers", [])]
        console.print(f"Loaded {len(papers)} papers for context\n")

    # Initialize retriever if using RAG
    retriever = None
    if use_rag:
        if not papers:
            console.print(
                "[yellow]Warning: RAG requested but no literature provided. Skipping RAG.[/yellow]\n"
            )
        else:
            console.print("[cyan]Indexing papers for RAG...[/cyan]")
            retriever = Retriever(cache_dir=".arakis_cache")
            _run_async(retriever.index_papers(papers, show_progress=False))
            console.print("[green]✓ Papers indexed[/green]\n")

    # Write introduction
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating introduction...", total=None)
        intro_section, cited_papers = _run_async(
            writer.write_complete_introduction(
                research_question=research_question,
                literature_context=papers,
                retriever=retriever,
                use_perplexity=use_perplexity,
            )
        )

    # Display warnings if any
    if writer.warnings:
        console.print("\n[yellow]Warnings during generation:[/yellow]")
        for warning in writer.warnings:
            console.print(f"  [yellow]⚠ {warning}[/yellow]")

    # Display literature sources used
    if writer.literature_sources:
        sources_str = ", ".join(set(s.split(":")[1] for s in writer.literature_sources if ":" in s))
        console.print(f"\n[dim]Literature sources used: {sources_str}[/dim]")

    # Display results
    console.print("\n[bold green]Introduction Section Generated![/bold green]\n")

    intro_table = Table(title="Section Summary")
    intro_table.add_column("Subsection", style="cyan")
    intro_table.add_column("Word Count", style="magenta")

    for subsection in intro_section.subsections:
        intro_table.add_row(subsection.title, str(subsection.word_count))

    intro_table.add_row("[bold]Total[/bold]", f"[bold]{intro_section.total_word_count}[/bold]")

    console.print(intro_table)

    # Validate and display citation status
    validation = writer.validate_citations(intro_section)
    if validation["valid"]:
        console.print(f"\n[green]✓ Citation validation: All {validation['unique_citation_count']} citations verified[/green]")
    else:
        console.print(f"\n[yellow]⚠ Citation validation: {len(validation['missing_papers'])} missing references[/yellow]")
        if validation['missing_papers']:
            for missing in validation['missing_papers'][:5]:
                console.print(f"  [yellow]- {missing}[/yellow]")

    # Display cited papers
    if cited_papers:
        console.print(f"\n[bold]References ({len(cited_papers)} papers cited):[/bold]")
        for i, paper in enumerate(cited_papers, 1):
            year_str = f" ({paper.year})" if paper.year else ""
            console.print(f"  {i}. {paper.title[:70]}{'...' if len(paper.title) > 70 else ''}{year_str}")

    # Display preview
    console.print("\n[bold]Preview:[/bold]")
    preview_lines = intro_section.to_markdown().split("\n")[:25]
    console.print("\n".join(preview_lines))
    if len(intro_section.to_markdown().split("\n")) > 25:
        console.print("[dim]... (truncated)[/dim]")

    # Save to file
    if output:
        with open(output, "w") as f:
            f.write(intro_section.to_markdown())
        console.print(f"\n[dim]✓ Introduction saved to {output}[/dim]")

        # Save references to separate file
        if save_references and cited_papers:
            ref_output = output.replace(".md", "_references.md") if output.endswith(".md") else f"{output}_references.md"
            ref_text = writer.generate_reference_list(intro_section)
            with open(ref_output, "w") as f:
                f.write("# References\n\n")
                f.write(ref_text)
            console.print(f"[dim]✓ References saved to {ref_output}[/dim]")


@app.command()
def write_discussion(
    analysis_file: str = typer.Argument(..., help="JSON file with meta-analysis results"),
    outcome: str = typer.Option("primary outcome", "--outcome", "-o", help="Name of the outcome"),
    output: Optional[str] = typer.Option(None, "--output", help="Output markdown file"),
    literature: Optional[str] = typer.Option(
        None, "--literature", "-l", help="JSON file with relevant papers for comparison"
    ),
    use_rag: bool = typer.Option(
        False, "--use-rag", help="Use RAG system for literature comparison"
    ),
    interpretation: Optional[str] = typer.Option(
        None, "--interpretation", help="Your interpretation notes"
    ),
    limitations: Optional[str] = typer.Option(
        None, "--limitations", help="Additional limitations to mention"
    ),
    implications: Optional[str] = typer.Option(
        None, "--implications", help="Implications to discuss"
    ),
):
    """
    Write discussion section for a systematic review.

    Generates summary of findings, comparison with literature, limitations, and implications.
    """
    import json

    from arakis.agents.discussion_writer import DiscussionWriterAgent
    from arakis.models.analysis import MetaAnalysisResult
    from arakis.models.paper import Paper
    from arakis.rag import Retriever

    console.print("[bold]Writing Discussion Section...[/bold]\n")

    # Load analysis results
    with open(analysis_file) as f:
        analysis_data = json.load(f)

    # Reconstruct MetaAnalysisResult
    try:
        meta_result = MetaAnalysisResult.from_dict(analysis_data)
    except Exception as e:
        console.print(f"[red]Error loading analysis results: {e}[/red]")
        raise typer.Exit(1)

    console.print(
        f"Loaded meta-analysis: {meta_result.studies_included} studies, n={meta_result.total_sample_size}\n"
    )

    # Load literature context if provided
    papers = None
    if literature:
        with open(literature) as f:
            data = json.load(f)
        papers = [Paper(**p) for p in data.get("papers", [])]
        console.print(f"Loaded {len(papers)} papers for comparison\n")

    # Initialize retriever if using RAG
    retriever = None
    if use_rag:
        if not papers:
            console.print(
                "[yellow]Warning: RAG requested but no literature provided. Skipping RAG.[/yellow]\n"
            )
        else:
            console.print("[cyan]Indexing papers for RAG...[/cyan]")
            retriever = Retriever(cache_dir=".arakis_cache")
            _run_async(retriever.index_papers(papers, show_progress=False))
            console.print("[green]✓ Papers indexed[/green]\n")

    # Write discussion
    writer = DiscussionWriterAgent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating discussion...", total=None)
        discussion_section = _run_async(
            writer.write_complete_discussion(
                meta_analysis_result=meta_result,
                outcome_name=outcome,
                retriever=retriever,
                literature_context=papers,
                user_interpretation=interpretation,
                user_implications=implications,
                user_limitation_notes=limitations,
            )
        )

    # Display results
    console.print("\n[bold green]Discussion Section Generated![/bold green]\n")

    discussion_table = Table(title="Section Summary")
    discussion_table.add_column("Subsection", style="cyan")
    discussion_table.add_column("Word Count", style="magenta")

    for subsection in discussion_section.subsections:
        discussion_table.add_row(subsection.title, str(subsection.word_count))

    discussion_table.add_row(
        "[bold]Total[/bold]", f"[bold]{discussion_section.total_word_count}[/bold]"
    )

    console.print(discussion_table)

    # Display preview
    console.print("\n[bold]Preview:[/bold]")
    preview_lines = discussion_section.to_markdown().split("\n")[:25]
    console.print("\n".join(preview_lines))
    if len(discussion_section.to_markdown().split("\n")) > 25:
        console.print("[dim]... (truncated)[/dim]")

    # Save to file
    if output:
        with open(output, "w") as f:
            f.write(discussion_section.to_markdown())
        console.print(f"\n[dim]✓ Discussion saved to {output}[/dim]")


@app.command()
def write_abstract(
    manuscript_file: str = typer.Argument(
        ..., help="JSON file with manuscript sections or introduction/results/discussion files"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output markdown file"),
    format: str = typer.Option(
        "structured", "--format", "-f", help="Format: 'structured' (IMRAD) or 'unstructured'"
    ),
    word_limit: int = typer.Option(300, "--word-limit", "-w", help="Maximum word count"),
    introduction: Optional[str] = typer.Option(
        None, "--introduction", help="Introduction markdown file"
    ),
    methods: Optional[str] = typer.Option(None, "--methods", help="Methods markdown file"),
    results: Optional[str] = typer.Option(None, "--results", help="Results markdown file"),
    discussion: Optional[str] = typer.Option(None, "--discussion", help="Discussion markdown file"),
):
    """
    Write an abstract for a systematic review.

    Can generate from a complete manuscript JSON file or from individual section files.

    Examples:
        # From manuscript JSON
        arakis write-abstract manuscript.json --output abstract.md

        # From individual sections
        arakis write-abstract dummy.json --introduction intro.md --results results.md --output abstract.md

        # Unstructured format
        arakis write-abstract manuscript.json --format unstructured --word-limit 250
    """
    import json

    from arakis.agents.abstract_writer import AbstractWriterAgent
    from arakis.models.writing import Manuscript, Section

    console.print("[bold]Writing Abstract...[/bold]\n")

    # Validate format
    if format not in ["structured", "unstructured"]:
        console.print(
            f"[red]Invalid format: {format}. Must be 'structured' or 'unstructured'[/red]"
        )
        raise typer.Exit(1)

    structured = format == "structured"

    # Load manuscript
    manuscript = None

    # Option 1: Load from individual section files
    if any([introduction, methods, results, discussion]):
        console.print("[cyan]Loading sections from individual files...[/cyan]")

        # Read section files
        intro_text = None
        methods_text = None
        results_text = None
        discussion_text = None

        if introduction:
            with open(introduction) as f:
                intro_text = f.read()

        if methods:
            with open(methods) as f:
                methods_text = f.read()

        if results:
            with open(results) as f:
                results_text = f.read()

        if discussion:
            with open(discussion) as f:
                discussion_text = f.read()

        # Use the from_sections method
        writer = AbstractWriterAgent()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Generating abstract from sections...", total=None)
            result = _run_async(
                writer.write_abstract_from_sections(
                    title="Systematic Review",
                    introduction_text=intro_text,
                    methods_text=methods_text,
                    results_text=results_text,
                    discussion_text=discussion_text,
                    structured=structured,
                    word_limit=word_limit,
                )
            )

    # Option 2: Load from manuscript JSON file
    else:
        console.print("[cyan]Loading manuscript from JSON...[/cyan]")

        try:
            with open(manuscript_file) as f:
                data = json.load(f)
        except FileNotFoundError:
            console.print(f"[red]File not found: {manuscript_file}[/red]")
            raise typer.Exit(1)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON: {e}[/red]")
            raise typer.Exit(1)

        # Try to load as Manuscript object
        try:
            # Reconstruct manuscript from dict
            manuscript = Manuscript(title=data.get("title", "Systematic Review"))

            if "sections" in data:
                sections_data = data["sections"]
                if sections_data.get("introduction"):
                    manuscript.introduction = Section(
                        title="Introduction", content=sections_data["introduction"]
                    )
                if sections_data.get("methods"):
                    manuscript.methods = Section(title="Methods", content=sections_data["methods"])
                if sections_data.get("results"):
                    manuscript.results = Section(title="Results", content=sections_data["results"])
                if sections_data.get("discussion"):
                    manuscript.discussion = Section(
                        title="Discussion", content=sections_data["discussion"]
                    )

        except Exception as e:
            console.print(f"[red]Error loading manuscript: {e}[/red]")
            raise typer.Exit(1)

        # Check if manuscript has content
        if not any(
            [manuscript.introduction, manuscript.methods, manuscript.results, manuscript.discussion]
        ):
            console.print(
                "[yellow]Warning: No sections found in manuscript. Abstract may be incomplete.[/yellow]\n"
            )

        # Generate abstract
        writer = AbstractWriterAgent()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Generating abstract...", total=None)
            result = _run_async(
                writer.write_abstract(manuscript, structured=structured, word_limit=word_limit)
            )

    # Display results
    console.print("\n[bold green]Abstract Generated![/bold green]\n")

    abstract_table = Table(title="Abstract Summary")
    abstract_table.add_column("Metric", style="cyan")
    abstract_table.add_column("Value", style="magenta")

    abstract_table.add_row("Format", format.title())
    abstract_table.add_row("Word Count", str(result.section.word_count))
    abstract_table.add_row("Word Limit", str(word_limit))
    abstract_table.add_row("Generation Time", f"{result.generation_time_ms}ms")
    abstract_table.add_row("Tokens Used", str(result.tokens_used))
    abstract_table.add_row("Cost", f"${result.cost_usd:.4f}")

    console.print(abstract_table)

    # Check word limit
    if result.section.word_count > word_limit:
        console.print(
            f"\n[yellow]⚠ Word count ({result.section.word_count}) exceeds limit ({word_limit})[/yellow]"
        )

    # Display abstract
    console.print("\n[bold]Generated Abstract:[/bold]\n")
    console.print(f"[dim]{result.section.content}[/dim]\n")

    # Save to file
    if output:
        with open(output, "w") as f:
            f.write(result.section.content)
        console.print(f"[dim]✓ Abstract saved to {output}[/dim]")


@app.command()
def workflow(
    research_question: str = typer.Option(
        None, "--question", "-q", help="Research question for the systematic review"
    ),
    include: str = typer.Option(
        None, "--include", "-i", help="Inclusion criteria (comma-separated)"
    ),
    exclude: str = typer.Option("", "--exclude", "-e", help="Exclusion criteria (comma-separated)"),
    databases: str = typer.Option(
        "pubmed", "--databases", "-d", help="Comma-separated list of databases"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Maximum results per database"),
    output_dir: str = typer.Option("./workflow_output", "--output", "-o", help="Output directory"),
    fast_mode: bool = typer.Option(
        False, "--fast", help="Fast mode: single-pass screening and extraction"
    ),
    extract_text: bool = typer.Option(
        True, "--extract-text/--no-extract-text", help="Extract full text from PDFs (default: True)"
    ),
    use_full_text: bool = typer.Option(
        True, "--use-full-text/--no-full-text", help="Use full text for extraction (default: True)"
    ),
    skip_analysis: bool = typer.Option(False, "--skip-analysis", help="Skip statistical analysis"),
    skip_writing: bool = typer.Option(False, "--skip-writing", help="Skip manuscript writing"),
    schema: str = typer.Option(
        "auto",
        "--schema",
        "-s",
        help="Extraction schema: auto (detect from question), rct, cohort, case_control, diagnostic",
    ),
    resume: bool = typer.Option(
        False, "--resume", "-r", help="Resume workflow from last checkpoint"
    ),
):
    """
    Run complete systematic review workflow end-to-end.

    This streamlined command runs all pipeline stages:
    1. Literature search across databases
    2. AI-powered paper screening with dual-review
    3. Full-text PDF extraction (default enabled)
    4. Data extraction from included papers using full text
    5. Statistical analysis and meta-analysis
    6. PRISMA diagram generation
    7. Manuscript writing (introduction and results)

    By default, the workflow extracts and uses full PDF text for higher quality
    data extraction. Use --no-extract-text or --no-full-text to disable.

    Use --schema to specify the extraction schema based on study design:
    - auto: Auto-detect from research question and criteria (default)
    - rct: Randomized controlled trials
    - cohort: Cohort/observational studies
    - case_control: Case-control studies
    - diagnostic: Diagnostic accuracy studies

    Use --resume to continue a previously interrupted workflow from the last
    completed checkpoint.
    """
    import json
    from dataclasses import asdict
    from datetime import datetime
    from pathlib import Path

    from arakis.models.workflow_state import WorkflowStage
    from arakis.workflow.state_manager import WorkflowStateManager

    # Setup
    start_time = datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Initialize state manager
    state_manager = WorkflowStateManager(output_path)

    # Handle resume mode
    if resume:
        if not state_manager.can_resume():
            console.print("[red]No resumable workflow found in this directory.[/red]")
            console.print(f"[dim]Looking for: {state_manager.state_file}[/dim]")
            raise typer.Exit(1)

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(
                Panel.fit(
                    f"[bold blue]Resuming Workflow[/bold blue]\n\n"
                    f"[cyan]Workflow ID:[/cyan] {resume_info['workflow_id']}\n"
                    f"[cyan]Research Question:[/cyan]\n{resume_info['research_question']}\n\n"
                    f"[cyan]Progress:[/cyan] {resume_info['progress']}\n"
                    f"[cyan]Completed Stages:[/cyan] {', '.join(resume_info['completed_stages'])}\n"
                    f"[cyan]Resuming from:[/cyan] {resume_info['resume_stage']}\n\n"
                    f"[dim]Output: {output_dir}[/dim]",
                    title="🔄 Resuming Workflow",
                )
            )

        # Load state and get config
        state = state_manager.load_state()
        if state is None:
            console.print("[red]Failed to load workflow state.[/red]")
            raise typer.Exit(1)

        # Restore configuration from state
        research_question = state.research_question
        include = ",".join(state.inclusion_criteria)
        exclude = ",".join(state.exclusion_criteria)
        databases = ",".join(state.databases)
        max_results = state.max_results
        fast_mode = state.fast_mode
        extract_text = state.extract_text
        use_full_text = state.use_full_text
        skip_analysis = state.skip_analysis
        skip_writing = state.skip_writing
        schema = state.schema

        resume_stage = state.get_resume_stage()
    else:
        # Validate required arguments for new workflow
        if research_question is None:
            console.print("[red]--question is required for new workflows[/red]")
            raise typer.Exit(1)
        if include is None:
            console.print("[red]--include is required for new workflows[/red]")
            raise typer.Exit(1)

        # Check if there's an existing incomplete workflow
        if state_manager.can_resume():
            resume_info = state_manager.get_resume_info()
            console.print(
                Panel.fit(
                    f"[yellow]Found incomplete workflow in this directory[/yellow]\n\n"
                    f"[cyan]Workflow ID:[/cyan] {resume_info['workflow_id']}\n"
                    f"[cyan]Progress:[/cyan] {resume_info['progress']}\n\n"
                    f"Use --resume to continue, or choose a different output directory.",
                    title="⚠️ Existing Workflow Found",
                )
            )
            raise typer.Exit(1)

        # Create new workflow state
        inclusion_criteria = [c.strip() for c in include.split(",")]
        exclusion_criteria = [c.strip() for c in exclude.split(",")] if exclude else []
        db_list = [d.strip() for d in databases.split(",")]

        state_manager.create_new_state(
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            databases=db_list,
            max_results=max_results,
            fast_mode=fast_mode,
            extract_text=extract_text,
            use_full_text=use_full_text,
            skip_analysis=skip_analysis,
            skip_writing=skip_writing,
            schema=schema,
        )

        resume_stage = None

        console.print(
            Panel.fit(
                f"[bold blue]Arakis Systematic Review Workflow[/bold blue]\n\n"
                f"[cyan]Research Question:[/cyan]\n{research_question}\n\n"
                f"[cyan]Inclusion:[/cyan] {include}\n"
                f"[cyan]Exclusion:[/cyan] {exclude or '(none)'}\n\n"
                f"[dim]Output: {output_dir}[/dim]",
                title="🚀 Starting Workflow",
            )
        )

    workflow_results = {
        "research_question": research_question,
        "started_at": start_time.isoformat(),
        "stages": {},
        "total_cost": state_manager.state.total_cost if state_manager.state else 0.0,
    }

    # Stage 1: Search
    search_result = None
    search_file = output_path / "1_search_results.json"

    if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.SEARCH):
        console.print("\n[bold cyan]Stage 1/8:[/bold cyan] Literature Search [dim](cached)[/dim]")

        # Load cached search results
        cached_papers = state_manager.load_search_results()
        if cached_papers:
            from arakis.models.paper import PRISMAFlow as PRISMAFlowModel

            # Reconstruct minimal search result for downstream use
            class CachedSearchResult:
                def __init__(self, papers_data, stage_data):
                    from arakis.models.paper import Author, Paper, PaperSource

                    self.papers = []
                    for p in papers_data:
                        authors = [
                            Author(name=a["name"], affiliation=a.get("affiliation"), orcid=a.get("orcid"))
                            if isinstance(a, dict) else Author(name=str(a))
                            for a in p.get("authors", [])
                        ]
                        paper = Paper(
                            id=p["id"],
                            title=p.get("title", ""),
                            abstract=p.get("abstract"),
                            year=p.get("year"),
                            authors=authors,
                            doi=p.get("doi"),
                            pmid=p.get("pmid"),
                            source=PaperSource(p.get("source", "pubmed")),
                        )
                        self.papers.append(paper)

                    self.prisma_flow = PRISMAFlowModel(
                        records_identified=stage_data.get("records_identified", {}),
                        duplicates_removed=stage_data.get("duplicates_removed", 0),
                    )

            stage_data = state_manager.state.get_stage_data(WorkflowStage.SEARCH)
            search_result = CachedSearchResult(cached_papers, stage_data)
            console.print(f"[green]✓ Loaded {len(search_result.papers)} papers from cache[/green]\n")

            workflow_results["stages"]["search"] = {
                "papers_found": len(search_result.papers),
                "duplicates_removed": stage_data.get("duplicates_removed", 0),
                "file": str(search_file),
            }
        else:
            console.print("[yellow]Cache file missing, re-running search...[/yellow]")
            state_manager.state.stages[WorkflowStage.SEARCH.value].status = state_manager.state.stages[WorkflowStage.SEARCH.value].status.__class__.PENDING

    if search_result is None:
        console.print("\n[bold cyan]Stage 1/8:[/bold cyan] Literature Search")
        console.print(f"[dim]Searching {databases}...[/dim]\n")

        state_manager.start_stage(WorkflowStage.SEARCH)

        from arakis.orchestrator import SearchOrchestrator

        db_list = [d.strip() for d in databases.split(",")]
        orchestrator = SearchOrchestrator()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Searching databases...", total=None)

            def update_search(stage: str, detail: str):
                progress.update(task, description=f"{stage}: {detail}")

            search_result = _run_async(
                orchestrator.comprehensive_search(
                    research_question=research_question,
                    databases=db_list,
                    max_results_per_query=max_results,
                    validate_queries=False,
                    progress_callback=update_search,
                )
            )

        # Save search results
        with open(search_file, "w") as f:
            json.dump([asdict(p) for p in search_result.papers], f, indent=2, default=str)

        console.print(f"[green]✓ Found {len(search_result.papers)} unique papers[/green]")
        console.print(f"[dim]Saved to {search_file}[/dim]\n")

        workflow_results["stages"]["search"] = {
            "papers_found": len(search_result.papers),
            "duplicates_removed": search_result.prisma_flow.duplicates_removed,
            "file": str(search_file),
        }

        # Save checkpoint
        state_manager.complete_stage(
            WorkflowStage.SEARCH,
            output_file=str(search_file),
            data={
                "papers_found": len(search_result.papers),
                "duplicates_removed": search_result.prisma_flow.duplicates_removed,
                "records_identified": dict(search_result.prisma_flow.records_identified),
            },
        )

    if len(search_result.papers) == 0:
        console.print("[yellow]No papers found. Workflow cannot continue.[/yellow]")
        raise typer.Exit(0)

    # Stage 2: Screening
    decisions = None
    summary = None
    screening_file = output_path / "2_screening_decisions.json"

    from arakis.agents.screener import ScreeningAgent
    from arakis.models.paper import Paper
    from arakis.models.screening import ScreeningCriteria, ScreeningDecision, ScreeningStatus

    # Build papers list from search results (needed for both cached and fresh runs)
    papers = [
        Paper(
            id=p.id,
            title=p.title,
            abstract=p.abstract,
            year=p.year,
            authors=p.authors,
            doi=p.doi,
            source=p.source,
        )
        for p in search_result.papers
    ]

    if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.SCREENING):
        console.print("[bold cyan]Stage 2/8:[/bold cyan] Paper Screening [dim](cached)[/dim]")

        # Load cached screening decisions
        cached_decisions = state_manager.load_screening_decisions()
        if cached_decisions:
            decisions = []
            for d in cached_decisions:
                decision = ScreeningDecision(
                    paper_id=d["paper_id"],
                    status=ScreeningStatus(d["status"]),
                    reason=d.get("reason", ""),
                    confidence=d.get("confidence", 0.0),
                    matched_inclusion=d.get("matched_inclusion", []),
                    matched_exclusion=d.get("matched_exclusion", []),
                    is_conflict=d.get("is_conflict", False),
                )
                decisions.append(decision)

            screener = ScreeningAgent()
            summary = screener.summarize_screening(decisions)
            console.print(f"[green]✓ Loaded {len(decisions)} decisions from cache[/green]")
            console.print(
                f"[green]  Included: {summary['included']}, Excluded: {summary['excluded']}, Maybe: {summary['maybe']}[/green]\n"
            )

            workflow_results["stages"]["screening"] = {
                "total_screened": len(decisions),
                "included": summary["included"],
                "excluded": summary["excluded"],
                "maybe": summary["maybe"],
                "conflicts": summary.get("conflicts", 0),
                "file": str(screening_file),
            }
        else:
            console.print("[yellow]Cache file missing, re-running screening...[/yellow]")

    if decisions is None:
        console.print("[bold cyan]Stage 2/8:[/bold cyan] Paper Screening")
        mode_desc = "single-pass" if fast_mode else "dual-review"
        console.print(f"[dim]Screening with {mode_desc} mode...[/dim]\n")

        state_manager.start_stage(WorkflowStage.SCREENING)

        criteria = ScreeningCriteria(
            inclusion=[c.strip() for c in include.split(",")],
            exclusion=[c.strip() for c in exclude.split(",")] if exclude else [],
        )

        screener = ScreeningAgent()

        def display_workflow_screening_progress(current, total, paper, decision):
            """Display real-time screening progress with decision details for workflow."""
            # Truncate title for display
            title_display = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title

            # Status color based on decision
            status_colors = {
                "INCLUDE": "green",
                "EXCLUDE": "red",
                "MAYBE": "yellow",
            }
            status_color = status_colors.get(decision.status.value, "white")

            # Print progress line
            console.print(f"[dim][SCREEN][/dim] Processing paper {current}/{total}: \"{title_display}\"")
            console.print(
                f"[dim][SCREEN][/dim] Decision: [{status_color}]{decision.status.value}[/{status_color}] "
                f"(confidence: {decision.confidence:.2f})"
            )

            # Show matched criteria if any
            matched_criteria = []
            if decision.matched_inclusion:
                matched_criteria.extend(decision.matched_inclusion)
            if matched_criteria:
                console.print(f"[dim][SCREEN][/dim] Matched criteria: {', '.join(matched_criteria)}")

            # Show conflict indicator if dual review had a conflict
            if decision.is_conflict:
                console.print("[dim][SCREEN][/dim] [yellow]⚠ Dual-review conflict detected[/yellow]")

            console.print()  # Empty line between papers

        decisions = _run_async(
            screener.screen_batch(
                papers,
                criteria,
                dual_review=not fast_mode,
                human_review=False,
                progress_callback=display_workflow_screening_progress,
            )
        )

        # Save screening results
        summary = screener.summarize_screening(decisions)

        with open(screening_file, "w") as f:
            json.dump([asdict(d) for d in decisions], f, indent=2, default=str)

        console.print(
            f"[green]✓ Included: {summary['included']}, Excluded: {summary['excluded']}, Maybe: {summary['maybe']}[/green]"
        )
        if not fast_mode:
            console.print(f"[yellow]  Conflicts: {summary['conflicts']}[/yellow]")
        console.print(f"[dim]Saved to {screening_file}[/dim]\n")

        workflow_results["stages"]["screening"] = {
            "total_screened": len(decisions),
            "included": summary["included"],
            "excluded": summary["excluded"],
            "maybe": summary["maybe"],
            "conflicts": summary.get("conflicts", 0),
            "file": str(screening_file),
        }

        # Save checkpoint
        state_manager.complete_stage(
            WorkflowStage.SCREENING,
            output_file=str(screening_file),
            data={
                "total_screened": len(decisions),
                "included": summary["included"],
                "excluded": summary["excluded"],
                "maybe": summary["maybe"],
                "conflicts": summary.get("conflicts", 0),
            },
        )

    if summary["included"] == 0:
        console.print("[yellow]No papers included. Workflow cannot continue.[/yellow]")
        raise typer.Exit(0)

    # Stage 3: PDF Fetch and Text Extraction
    fetch_results = None
    if extract_text:
        if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.PDF_FETCH):
            console.print("[bold cyan]Stage 3/8:[/bold cyan] PDF Fetch and Text Extraction [dim](cached)[/dim]")
            stage_data = state_manager.state.get_stage_data(WorkflowStage.PDF_FETCH)
            console.print(f"[green]✓ Text extracted for {stage_data.get('with_full_text', 0)} papers (from cache)[/green]\n")
            workflow_results["stages"]["fetch"] = stage_data
        else:
            console.print("[bold cyan]Stage 3/8:[/bold cyan] PDF Fetch and Text Extraction")
            console.print("[dim]Downloading and extracting text from included papers...[/dim]\n")

            state_manager.start_stage(WorkflowStage.PDF_FETCH)

            from arakis.retrieval.fetcher import PaperFetcher

            # Get included papers
            included_ids = [d.paper_id for d in decisions if d.status.value == "include"]
            included_papers_to_fetch = [p for p in papers if p.id in included_ids]

            fetcher = PaperFetcher()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Fetching 0/{len(included_papers_to_fetch)}...",
                    total=len(included_papers_to_fetch),
                )

                def update_fetch(current, total, paper):
                    progress.update(task, description=f"Fetching {current}/{total}...")
                    progress.advance(task)

                fetch_results = _run_async(
                    fetcher.fetch_batch(
                        included_papers_to_fetch,
                        download=True,
                        extract_text=True,
                        progress_callback=update_fetch,
                    )
                )

            # Update papers with extracted text
            papers_with_text = sum(1 for r in fetch_results if r.success and r.paper.has_full_text)
            console.print(
                f"[green]✓ Extracted text from {papers_with_text}/{len(included_papers_to_fetch)} papers[/green]"
            )
            console.print(f"[dim]Downloaded to {output_path / 'pdfs'}[/dim]\n")

            workflow_results["stages"]["fetch"] = {
                "total_fetched": len(fetch_results),
                "with_full_text": papers_with_text,
                "success_rate": papers_with_text / len(included_papers_to_fetch)
                if included_papers_to_fetch
                else 0,
            }

            # Save checkpoint
            state_manager.complete_stage(
                WorkflowStage.PDF_FETCH,
                data=workflow_results["stages"]["fetch"],
            )
    else:
        state_manager.skip_stage(WorkflowStage.PDF_FETCH, "extract_text disabled")

    # Stage 4: Extraction
    extraction_result = None
    extraction_file = output_path / "3_extraction_results.json"

    from arakis.agents.extractor import DataExtractionAgent
    from arakis.extraction.schemas import detect_schema, get_schema, list_schemas
    from arakis.models.extraction import ExtractionResult

    # Get included papers
    included_ids = [d.paper_id for d in decisions if d.status.value == "include"]
    included_papers = [p for p in papers if p.id in included_ids]

    if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.EXTRACTION):
        console.print(
            f"[bold cyan]Stage {'4' if extract_text else '3'}/8:[/bold cyan] Data Extraction [dim](cached)[/dim]"
        )

        # Load cached extraction results
        cached_extraction = state_manager.load_extraction_results()
        if cached_extraction:
            extraction_result = ExtractionResult.from_dict(cached_extraction)
            stage_data = state_manager.state.get_stage_data(WorkflowStage.EXTRACTION)
            console.print(f"[green]✓ Loaded {extraction_result.successful_extractions} extractions from cache[/green]\n")

            workflow_results["stages"]["extraction"] = {
                "total_papers": extraction_result.total_papers,
                "successful": extraction_result.successful_extractions,
                "average_quality": extraction_result.average_quality,
                "cost": stage_data.get("cost", 0.0),
                "file": str(extraction_file),
            }
        else:
            console.print("[yellow]Cache file missing, re-running extraction...[/yellow]")

    if extraction_result is None:
        console.print(
            f"[bold cyan]Stage {'4' if extract_text else '3'}/8:[/bold cyan] Data Extraction"
        )
        extraction_mode = "single-pass" if fast_mode else "triple-review"
        text_mode = "full text" if use_full_text else "abstracts"
        console.print(f"[dim]Extracting with {extraction_mode} mode using {text_mode}...[/dim]")

        state_manager.start_stage(WorkflowStage.EXTRACTION)

        # Get extraction schema (auto-detect or explicit)
        detected_schema_name = None
        if schema == "auto":
            # Auto-detect schema from research question and inclusion criteria
            detection_text = f"{research_question} {include}"
            detected_schema_name, confidence = detect_schema(detection_text)
            console.print(
                f"[dim]Schema: {detected_schema_name} (auto-detected, confidence: {confidence:.0%})[/dim]\n"
            )
            extraction_schema = get_schema(detected_schema_name)
        else:
            console.print(f"[dim]Schema: {schema}[/dim]\n")
            try:
                extraction_schema = get_schema(schema)
            except ValueError as e:
                console.print(f"[red]{e}[/red]")
                console.print("\n[bold]Available schemas:[/bold]")
                for s in list_schemas():
                    console.print(f"  • {s}")
                raise typer.Exit(1)
        agent = DataExtractionAgent()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Extracting 0/{len(included_papers)}...", total=len(included_papers)
            )

            def update_extract(current, total):
                progress.update(task, description=f"Extracting {current}/{total}...")
                progress.advance(task)

            extraction_result = _run_async(
                agent.extract_batch(
                    included_papers,
                    extraction_schema,
                    triple_review=not fast_mode,
                    use_full_text=use_full_text,
                    progress_callback=update_extract,
                )
            )

        # Save extraction results
        with open(extraction_file, "w") as f:
            json.dump(extraction_result.to_dict(), f, indent=2, default=str)

        console.print(f"[green]✓ Extracted {extraction_result.successful_extractions} papers[/green]")
        console.print(
            f"[dim]Quality: {extraction_result.average_quality:.2f}, Cost: ${extraction_result.estimated_cost:.2f}[/dim]"
        )
        console.print(f"[dim]Saved to {extraction_file}[/dim]\n")

        workflow_results["stages"]["extraction"] = {
            "total_papers": extraction_result.total_papers,
            "successful": extraction_result.successful_extractions,
            "average_quality": extraction_result.average_quality,
            "cost": extraction_result.estimated_cost,
            "file": str(extraction_file),
        }
        workflow_results["total_cost"] += extraction_result.estimated_cost
        state_manager.add_cost(extraction_result.estimated_cost)

        # Save checkpoint
        state_manager.complete_stage(
            WorkflowStage.EXTRACTION,
            output_file=str(extraction_file),
            data=workflow_results["stages"]["extraction"],
        )

    # Stage 5: Analysis
    analysis_file = output_path / "4_analysis_results.json"
    if not skip_analysis:
        if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.ANALYSIS):
            console.print("[bold cyan]Stage 5/8:[/bold cyan] Statistical Analysis [dim](cached)[/dim]")
            stage_data = state_manager.state.get_stage_data(WorkflowStage.ANALYSIS)
            console.print(f"[green]✓ Analysis loaded from cache[/green]\n")
            workflow_results["stages"]["analysis"] = stage_data
        else:
            console.print("[bold cyan]Stage 5/8:[/bold cyan] Statistical Analysis")
            console.print("[dim]Running analysis...[/dim]\n")

            state_manager.start_stage(WorkflowStage.ANALYSIS)

            from arakis.analysis.meta_analysis import MetaAnalysisEngine
            from arakis.analysis.recommender import AnalysisRecommenderAgent
            from arakis.models.analysis import AnalysisMethod, EffectMeasure, StudyData

            recommender = AnalysisRecommenderAgent()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Analyzing data...", total=None)
                recommendation = _run_async(recommender.recommend_tests(extraction_result, None))

            console.print(
                f"[green]✓ Recommended tests: {len(recommendation.recommended_tests)}[/green]"
            )

            # Try meta-analysis if feasible
            meta_result = None
            if recommendation.data_characteristics.get("meta_analysis_feasible", False):
                console.print("[dim]Performing meta-analysis...[/dim]")

                studies = []
                for paper in extraction_result.extractions:
                    study = StudyData(
                        study_id=paper.paper_id,
                        study_name=paper.paper_id,
                        sample_size=paper.data.get("sample_size_total"),
                        intervention_n=paper.data.get("sample_size_intervention"),
                        control_n=paper.data.get("sample_size_control"),
                        intervention_mean=paper.data.get("intervention_mean"),
                        intervention_sd=paper.data.get("intervention_sd"),
                        control_mean=paper.data.get("control_mean"),
                        control_sd=paper.data.get("control_sd"),
                        intervention_events=paper.data.get("intervention_events"),
                        control_events=paper.data.get("control_events"),
                    )
                    studies.append(study)

                has_continuous = any(s.intervention_mean is not None for s in studies)
                has_binary = any(s.intervention_events is not None for s in studies)

                if has_continuous or has_binary:
                    effect_measure = (
                        EffectMeasure.MEAN_DIFFERENCE if has_continuous else EffectMeasure.ODDS_RATIO
                    )
                    meta_engine = MetaAnalysisEngine()

                    try:
                        meta_result = meta_engine.calculate_pooled_effect(
                            studies=studies,
                            method=AnalysisMethod.RANDOM_EFFECTS,
                            effect_measure=effect_measure,
                        )
                        console.print(
                            f"[green]  ✓ Meta-analysis: Effect={meta_result.pooled_effect:.3f}, p={meta_result.p_value:.4f}[/green]"
                        )
                    except Exception as e:
                        console.print(f"[yellow]  Meta-analysis failed: {e}[/yellow]")

            # Save analysis
            analysis_data = {
                "recommendation": {
                    "recommended_tests": [
                        {
                            "test_name": t.test_name,
                            "test_type": t.test_type.value,
                            "description": t.description,
                            "parameters": t.parameters,
                        }
                        for t in recommendation.recommended_tests
                    ],
                    "rationale": recommendation.rationale,
                    "warnings": recommendation.warnings,
                },
            }

            if meta_result:
                analysis_data["meta_analysis"] = {
                    "outcome_name": meta_result.outcome_name,
                    "studies_included": int(meta_result.studies_included),
                    "total_sample_size": int(meta_result.total_sample_size),
                    "pooled_effect": float(meta_result.pooled_effect),
                    "p_value": float(meta_result.p_value),
                    "is_significant": bool(meta_result.is_significant),
                    "effect_measure": meta_result.effect_measure.value,
                    "heterogeneity": {
                        "i_squared": float(meta_result.heterogeneity.i_squared),
                    },
                }

            with open(analysis_file, "w") as f:
                json.dump(analysis_data, f, indent=2)

            console.print(f"[dim]Saved to {analysis_file}[/dim]\n")

            workflow_results["stages"]["analysis"] = {
                "tests_recommended": len(recommendation.recommended_tests),
                "meta_analysis": meta_result is not None,
                "file": str(analysis_file),
            }

            # Save checkpoint
            state_manager.complete_stage(
                WorkflowStage.ANALYSIS,
                output_file=str(analysis_file),
                data=workflow_results["stages"]["analysis"],
            )
    else:
        state_manager.skip_stage(WorkflowStage.ANALYSIS, "skip_analysis enabled")

    # Stage 6: PRISMA Diagram
    prisma_file = output_path / "5_prisma_diagram.png"
    flow = None

    from arakis.models.visualization import PRISMAFlow
    from arakis.visualization.prisma import PRISMADiagramGenerator

    # Build PRISMA flow data (needed for both cached and fresh runs)
    flow = PRISMAFlow(
        records_identified_total=search_result.prisma_flow.total_identified,
        records_identified_databases={
            k: v for k, v in search_result.prisma_flow.records_identified.items()
        },
        records_removed_duplicates=search_result.prisma_flow.duplicates_removed,
        records_screened=len(decisions),
        records_excluded=summary["excluded"],
        reports_sought=summary["included"],
        reports_assessed=summary["included"],
        studies_included=summary["included"],
        reports_included=summary["included"],
    )

    if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.PRISMA):
        console.print("[bold cyan]Stage 6/8:[/bold cyan] PRISMA Diagram [dim](cached)[/dim]")
        console.print(f"[green]✓ PRISMA diagram loaded from cache[/green]\n")
        workflow_results["stages"]["prisma"] = {"file": str(prisma_file)}
    else:
        console.print("[bold cyan]Stage 6/8:[/bold cyan] PRISMA Diagram")
        console.print("[dim]Generating diagram...[/dim]\n")

        state_manager.start_stage(WorkflowStage.PRISMA)

        generator = PRISMADiagramGenerator(output_dir=str(output_path))
        generator.generate(flow, "5_prisma_diagram.png")

        console.print("[green]✓ PRISMA diagram generated[/green]")
        console.print(f"[dim]Saved to {prisma_file}[/dim]\n")

        workflow_results["stages"]["prisma"] = {"file": str(prisma_file)}

        # Save checkpoint
        state_manager.complete_stage(
            WorkflowStage.PRISMA,
            output_file=str(prisma_file),
            data=workflow_results["stages"]["prisma"],
        )

    # Stage 7: Writing Introduction
    intro_file = output_path / "6_introduction.md"
    if not skip_writing:
        if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.INTRODUCTION):
            console.print("[bold cyan]Stage 7/8:[/bold cyan] Writing Introduction [dim](cached)[/dim]")
            stage_data = state_manager.state.get_stage_data(WorkflowStage.INTRODUCTION)
            console.print(f"[green]✓ Introduction loaded from cache ({stage_data.get('word_count', 0)} words)[/green]\n")
            workflow_results["stages"]["introduction"] = stage_data
        else:
            console.print("[bold cyan]Stage 7/8:[/bold cyan] Writing Introduction")
            console.print("[dim]Generating introduction section...[/dim]\n")

            state_manager.start_stage(WorkflowStage.INTRODUCTION)

            from arakis.agents.intro_writer import IntroductionWriterAgent

            intro_writer = IntroductionWriterAgent()

            # Check if OpenAI web search is configured
            use_web_search = intro_writer.literature_client.is_configured
            if use_web_search:
                console.print("[cyan]Using OpenAI web search for literature research[/cyan]")
            else:
                console.print("[dim]OpenAI API not configured - using provided context[/dim]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Writing introduction...", total=None)
                intro_section, cited_papers = _run_async(
                    intro_writer.write_complete_introduction(
                        research_question=research_question,
                        literature_context=None,
                        retriever=None,
                        use_web_search=use_web_search,
                    )
                )

            with open(intro_file, "w") as f:
                f.write(intro_section.to_markdown())

            # Validate citations
            validation = intro_writer.validate_citations(intro_section)

            # Save references if any papers were cited
            if cited_papers:
                ref_file = output_path / "6_introduction_references.md"
                ref_text = intro_writer.generate_reference_list(intro_section)
                with open(ref_file, "w") as f:
                    f.write("# References\n\n")
                    f.write(ref_text)

                # Report citation validation status
                if validation["valid"]:
                    console.print(f"[green]✓ Introduction: {intro_section.total_word_count} words, {len(cited_papers)} references[/green]")
                    console.print(f"[green]✓ Citation validation: All {validation['unique_citation_count']} citations verified[/green]")
                else:
                    console.print(f"[yellow]⚠ Introduction: {intro_section.total_word_count} words, {len(cited_papers)} references[/yellow]")
                    console.print(f"[yellow]⚠ Citation validation: {len(validation['missing_papers'])} missing references[/yellow]")

                console.print(f"[dim]Saved to {intro_file}[/dim]")
                console.print(f"[dim]References saved to {ref_file}[/dim]\n")
            else:
                console.print(f"[green]✓ Introduction: {intro_section.total_word_count} words[/green]")
                console.print(f"[dim]Saved to {intro_file}[/dim]\n")

            workflow_results["stages"]["introduction"] = {
                "word_count": intro_section.total_word_count,
                "references_count": len(cited_papers) if cited_papers else 0,
                "file": str(intro_file),
            }
            workflow_results["total_cost"] += 1.0  # Estimate
            state_manager.add_cost(1.0)

            # Save checkpoint
            state_manager.complete_stage(
                WorkflowStage.INTRODUCTION,
                output_file=str(intro_file),
                data=workflow_results["stages"]["introduction"],
            )

        # Stage 8: Writing Results
        results_file = output_path / "7_results.md"
        if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.RESULTS):
            console.print("[bold cyan]Stage 8/8:[/bold cyan] Writing Results [dim](cached)[/dim]")
            stage_data = state_manager.state.get_stage_data(WorkflowStage.RESULTS)
            console.print(f"[green]✓ Results loaded from cache ({stage_data.get('word_count', 0)} words)[/green]\n")
            workflow_results["stages"]["results"] = stage_data
        else:
            console.print("[bold cyan]Stage 8/8:[/bold cyan] Writing Results")
            console.print("[dim]Generating results section...[/dim]\n")

            state_manager.start_stage(WorkflowStage.RESULTS)

            from arakis.agents.results_writer import ResultsWriterAgent

            results_writer = ResultsWriterAgent()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Writing results...", total=None)
                results_section = _run_async(
                    results_writer.write_complete_results_section(
                        prisma_flow=flow,
                        included_papers=included_papers,
                        meta_analysis_result=None,
                        outcome_name="primary outcome",
                    )
                )

            with open(results_file, "w") as f:
                f.write(results_section.to_markdown())

            console.print(f"[green]✓ Results: {results_section.total_word_count} words[/green]")
            console.print(f"[dim]Saved to {results_file}[/dim]\n")

            workflow_results["stages"]["results"] = {
                "word_count": results_section.total_word_count,
                "file": str(results_file),
            }
            workflow_results["total_cost"] += 0.7  # Estimate
            state_manager.add_cost(0.7)

            # Save checkpoint
            state_manager.complete_stage(
                WorkflowStage.RESULTS,
                output_file=str(results_file),
                data=workflow_results["stages"]["results"],
            )
    else:
        state_manager.skip_stage(WorkflowStage.INTRODUCTION, "skip_writing enabled")
        state_manager.skip_stage(WorkflowStage.RESULTS, "skip_writing enabled")

    # Stage 9: Manuscript Assembly
    manuscript_path = output_path / "8_manuscript.md"
    if state_manager.state and state_manager.state.is_stage_completed(WorkflowStage.MANUSCRIPT):
        console.print("[bold cyan]Stage 9/9:[/bold cyan] Manuscript Assembly [dim](cached)[/dim]")
        stage_data = state_manager.state.get_stage_data(WorkflowStage.MANUSCRIPT)
        console.print(f"[green]✓ Manuscript loaded from cache ({stage_data.get('word_count', 0)} words)[/green]\n")
        workflow_results["stages"]["manuscript"] = stage_data
    else:
        console.print("[bold cyan]Stage 9/9:[/bold cyan] Manuscript Assembly")
        console.print("[dim]Assembling complete manuscript...[/dim]\n")

        state_manager.start_stage(WorkflowStage.MANUSCRIPT)

        from arakis.manuscript import ManuscriptAssembler

        assembler = ManuscriptAssembler(output_path)

        # Load extraction results
        extraction_data = assembler.load_extraction_results()

        # Load included papers for references
        reference_papers = assembler.load_included_papers()

        # Assemble manuscript
        manuscript, manuscript_path = assembler.assemble(
            research_question=research_question,
            extraction_results=extraction_data,
            included_papers=reference_papers,
            prisma_flow=flow if flow else None,
            keywords=[c.strip() for c in include.split(",")][:5],  # Use inclusion criteria as keywords
        )

        console.print(f"[green]✓ Manuscript assembled: {manuscript.word_count} words[/green]")
        console.print(f"[green]  Tables: {len(manuscript.tables)}, Figures: {len(manuscript.figures)}[/green]")
        console.print(f"[green]  References: {len(manuscript.references)}[/green]")
        console.print(f"[dim]Saved to {manuscript_path}[/dim]\n")

        workflow_results["stages"]["manuscript"] = {
            "word_count": manuscript.word_count,
            "tables": len(manuscript.tables),
            "figures": len(manuscript.figures),
            "references": len(manuscript.references),
            "file": str(manuscript_path),
        }

        # Save checkpoint
        state_manager.complete_stage(
            WorkflowStage.MANUSCRIPT,
            output_file=str(manuscript_path),
            data=workflow_results["stages"]["manuscript"],
        )

    # Mark workflow as completed
    state_manager.mark_completed()

    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    workflow_results["completed_at"] = end_time.isoformat()
    workflow_results["duration_seconds"] = duration

    # Save workflow summary
    summary_file = output_path / "workflow_summary.json"
    with open(summary_file, "w") as f:
        json.dump(workflow_results, f, indent=2, default=str)

    # Display final summary
    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold green]✓ Workflow Complete![/bold green]\n\n"
            f"[cyan]Duration:[/cyan] {duration:.1f}s\n"
            f"[cyan]Total Cost:[/cyan] ${workflow_results['total_cost']:.2f}\n\n"
            f"[cyan]Papers Found:[/cyan] {workflow_results['stages']['search']['papers_found']}\n"
            f"[cyan]Papers Included:[/cyan] {workflow_results['stages']['screening']['included']}\n"
            f"[cyan]Data Extracted:[/cyan] {workflow_results['stages']['extraction']['successful']}\n\n"
            f"[dim]All outputs saved to: {output_dir}[/dim]",
            title="🎉 Success",
        )
    )

    # List output files
    console.print("\n[bold]Output Files:[/bold]")
    for stage_name, stage_data in workflow_results["stages"].items():
        if "file" in stage_data:
            file_path = Path(stage_data["file"])
            if file_path.exists():
                size = file_path.stat().st_size
                console.print(f"  • {file_path.name} ({size:,} bytes)")


@app.command(name="risk-of-bias")
def risk_of_bias(
    extractions: str = typer.Argument(..., help="Path to extraction results JSON file"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for risk of bias results (JSON)"
    ),
    tool: Optional[str] = typer.Option(
        None,
        "--tool",
        "-t",
        help="Assessment tool to use (rob_2, robins_i, quadas_2). Auto-detected if not specified.",
    ),
    figures: Optional[str] = typer.Option(
        None, "--figures", "-f", help="Directory for output figures"
    ),
    format: str = typer.Option(
        "both",
        "--format",
        help="Output format: table, figures, or both",
    ),
):
    """
    Assess risk of bias for extracted studies.

    Uses standardized tools:
    - RoB 2: For randomized controlled trials
    - ROBINS-I: For cohort and case-control studies
    - QUADAS-2: For diagnostic accuracy studies

    Example:
        arakis risk-of-bias extractions.json --output rob_results.json --figures ./figures/
    """
    import json
    from pathlib import Path

    from arakis.analysis import RiskOfBiasAssessor, RiskOfBiasTableGenerator
    from arakis.analysis.visualizer import VisualizationGenerator
    from arakis.models.extraction import ExtractionResult
    from arakis.models.risk_of_bias import RoBTool

    # Load extraction results
    extractions_path = Path(extractions)
    if not extractions_path.exists():
        console.print(f"[red]Error: File not found: {extractions}[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading extraction data...", total=None)

        try:
            with open(extractions_path) as f:
                data = json.load(f)
            extraction_result = ExtractionResult.from_dict(data)
        except Exception as e:
            console.print(f"[red]Error loading extractions: {e}[/red]")
            raise typer.Exit(1)

        # Determine tool
        rob_tool = None
        if tool:
            try:
                rob_tool = RoBTool(tool)
            except ValueError:
                console.print(f"[red]Unknown tool: {tool}. Use rob_2, robins_i, or quadas_2[/red]")
                raise typer.Exit(1)

        progress.update(task, description="Assessing risk of bias...")

        # Run assessment
        assessor = RiskOfBiasAssessor()
        summary = assessor.assess_studies(extraction_result, tool=rob_tool)

        # Generate table
        progress.update(task, description="Generating risk of bias table...")
        table_generator = RiskOfBiasTableGenerator()
        rob_table = table_generator.generate_table(summary)

    # Display results
    console.print("\n[bold green]Risk of Bias Assessment Complete![/bold green]\n")

    # Tool used
    tool_names = {
        "rob_2": "Cochrane RoB 2 (for RCTs)",
        "robins_i": "ROBINS-I (for observational studies)",
        "quadas_2": "QUADAS-2 (for diagnostic studies)",
    }
    console.print(f"[cyan]Tool:[/cyan] {tool_names.get(summary.tool.value, summary.tool.value)}")
    console.print(f"[cyan]Studies assessed:[/cyan] {summary.n_studies}")
    console.print(f"[cyan]Low risk:[/cyan] {summary.percent_low_risk:.0f}%")
    console.print(f"[cyan]High risk:[/cyan] {summary.percent_high_risk:.0f}%")

    # Display table
    if format in ["table", "both"]:
        console.print("\n[bold]Risk of Bias Summary Table:[/bold]")
        display_table = Table(title=rob_table.title)
        for header in rob_table.headers:
            display_table.add_column(header)
        for row in rob_table.rows:
            # Color code the cells
            colored_row = []
            for cell in row:
                if cell == "+":
                    colored_row.append("[green]+[/green]")
                elif cell == "-":
                    colored_row.append("[red]-[/red]")
                elif cell == "?":
                    colored_row.append("[yellow]?[/yellow]")
                else:
                    colored_row.append(cell)
            display_table.add_row(*colored_row)
        console.print(display_table)

        # Footnotes
        for note in rob_table.footnotes:
            console.print(f"[dim]{note}[/dim]")

    # Generate figures
    if format in ["figures", "both"] and figures:
        figures_dir = Path(figures)
        figures_dir.mkdir(parents=True, exist_ok=True)

        visualizer = VisualizationGenerator(output_dir=str(figures_dir))

        # Summary plot
        summary_path = visualizer.create_risk_of_bias_summary(summary, "rob_summary.png")
        console.print(f"\n[green]Created:[/green] {summary_path}")

        # Traffic light plot
        traffic_light_path = visualizer.create_risk_of_bias_traffic_light(
            summary, "rob_traffic_light.png"
        )
        console.print(f"[green]Created:[/green] {traffic_light_path}")

    # Save results
    if output:
        output_path = Path(output)
        output_data = {
            "summary": summary.to_dict(),
            "table": {
                "id": rob_table.id,
                "title": rob_table.title,
                "caption": rob_table.caption,
                "headers": rob_table.headers,
                "rows": rob_table.rows,
                "footnotes": rob_table.footnotes,
                "markdown": rob_table.markdown,
            },
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[green]Results saved to:[/green] {output_path}")


@app.command()
def version():
    """Show version information."""
    from arakis import __version__

    console.print(f"Arakis v{__version__}")


if __name__ == "__main__":
    app()
