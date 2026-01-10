#!/usr/bin/env python3
"""
Arakis Demo: Aspirin for Sepsis Systematic Review

This demo shows the complete workflow:
1. Generate optimized queries for multiple databases
2. Execute searches across PubMed, OpenAlex, and Semantic Scholar
3. Deduplicate results
4. Screen papers against inclusion/exclusion criteria
5. Attempt to fetch open access full texts

Run with: python -m arakis.examples.aspirin_sepsis_demo
"""

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def main():
    """Run the systematic review demo."""
    from arakis.orchestrator import SearchOrchestrator
    from arakis.agents.screener import ScreeningAgent
    from arakis.models.screening import ScreeningCriteria
    from arakis.retrieval.fetcher import PaperFetcher

    # Configuration
    RESEARCH_QUESTION = "Effect of aspirin on sepsis mortality in adult patients"
    DATABASES = ["pubmed", "openalex", "semantic_scholar"]
    MAX_RESULTS_PER_QUERY = 50  # Keep small for demo

    INCLUSION_CRITERIA = ScreeningCriteria(
        population="Adult patients with sepsis",
        intervention="Aspirin or acetylsalicylic acid",
        outcome="Mortality or survival",
        inclusion=[
            "Randomized controlled trial or cohort study",
            "Human subjects",
            "Adult patients (≥18 years)",
            "Sepsis, severe sepsis, or septic shock",
        ],
        exclusion=[
            "Animal studies",
            "In vitro studies",
            "Reviews, meta-analyses, or editorials",
            "Pediatric population only",
            "Case reports or case series",
        ],
        study_types=["RCT", "cohort", "observational"],
    )

    console.print(Panel.fit(
        f"[bold blue]Research Question:[/bold blue]\n{RESEARCH_QUESTION}\n\n"
        f"[bold]Databases:[/bold] {', '.join(DATABASES)}\n"
        f"[bold]Max results per query:[/bold] {MAX_RESULTS_PER_QUERY}",
        title="🔬 Arakis Systematic Review Demo"
    ))

    # Step 1: Comprehensive Search
    console.print("\n[bold cyan]Step 1: Generating Queries & Searching[/bold cyan]")

    orchestrator = SearchOrchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting...", total=None)

        def update(stage, detail):
            progress.update(task, description=f"{stage}: {detail}")

        search_result = await orchestrator.comprehensive_search(
            research_question=RESEARCH_QUESTION,
            databases=DATABASES,
            max_results_per_query=MAX_RESULTS_PER_QUERY,
            progress_callback=update,
        )

    # Display search results
    console.print(f"\n✅ [green]Search complete![/green]")

    flow_table = Table(title="PRISMA Flow - Identification")
    flow_table.add_column("Source", style="cyan")
    flow_table.add_column("Records", style="magenta")

    for db, count in search_result.prisma_flow.records_identified.items():
        flow_table.add_row(db, str(count))
    flow_table.add_row("─" * 15, "─" * 8)
    flow_table.add_row("Total Identified", str(search_result.prisma_flow.total_identified))
    flow_table.add_row("Duplicates Removed", str(search_result.prisma_flow.duplicates_removed))
    flow_table.add_row("[bold]Unique Papers[/bold]", f"[bold]{len(search_result.papers)}[/bold]")

    console.print(flow_table)

    # Show sample papers
    if search_result.papers:
        console.print("\n[dim]Sample papers found:[/dim]")
        for i, paper in enumerate(search_result.papers[:5], 1):
            console.print(f"  {i}. {paper.title[:70]}{'...' if len(paper.title) > 70 else ''}")
            console.print(f"     [dim]Year: {paper.year or 'N/A'} | Source: {paper.source.value}[/dim]")

    # Step 2: Screening
    console.print("\n[bold cyan]Step 2: Screening Papers[/bold cyan]")
    console.print(f"[dim]Criteria: {INCLUSION_CRITERIA.to_prompt()[:200]}...[/dim]\n")

    papers_to_screen = search_result.papers[:10]  # Screen first 10 for demo

    screener = ScreeningAgent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Screening 0/{len(papers_to_screen)}...", total=len(papers_to_screen))

        def screen_update(current, total):
            progress.update(task, description=f"Screening {current}/{total}...")
            progress.advance(task)

        decisions = await screener.screen_batch(
            papers_to_screen,
            INCLUSION_CRITERIA,
            dual_review=False,
            progress_callback=screen_update,
        )

    # Display screening results
    console.print(f"\n✅ [green]Screening complete![/green]")

    summary = screener.summarize_screening(decisions)

    screen_table = Table(title="Screening Results")
    screen_table.add_column("Status", style="cyan")
    screen_table.add_column("Count", style="magenta")

    screen_table.add_row("Included", str(summary["included"]))
    screen_table.add_row("Excluded", str(summary["excluded"]))
    screen_table.add_row("Maybe (needs review)", str(summary["maybe"]))
    screen_table.add_row("Avg Confidence", f"{summary['average_confidence']:.2f}")

    console.print(screen_table)

    # Show decisions
    console.print("\n[dim]Sample decisions:[/dim]")
    for decision in decisions[:5]:
        paper = next((p for p in papers_to_screen if p.id == decision.paper_id), None)
        if paper:
            status_color = {
                "include": "green",
                "exclude": "red",
                "maybe": "yellow"
            }.get(decision.status.value, "white")
            console.print(f"  [{status_color}]{decision.status.value.upper()}[/{status_color}] {paper.title[:50]}...")
            console.print(f"     [dim]{decision.reason[:80]}...[/dim]")

    # Step 3: Fetch full texts
    console.print("\n[bold cyan]Step 3: Fetching Full Texts[/bold cyan]")

    included_papers = [
        p for p, d in zip(papers_to_screen, decisions)
        if d.status.value == "include"
    ]

    if included_papers:
        fetcher = PaperFetcher()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching...", total=len(included_papers))

            def fetch_update(current, total, paper):
                progress.update(task, description=f"Fetching {current}/{total}...")
                progress.advance(task)

            fetch_results = await fetcher.fetch_batch(
                included_papers,
                download=False,
                progress_callback=fetch_update,
            )

        fetch_summary = fetcher.summarize_batch(fetch_results)

        console.print(f"\n✅ [green]Fetch complete![/green]")

        fetch_table = Table(title="Fetch Results")
        fetch_table.add_column("Metric", style="cyan")
        fetch_table.add_column("Value", style="magenta")

        fetch_table.add_row("Papers Attempted", str(fetch_summary["total"]))
        fetch_table.add_row("Successfully Retrieved", str(fetch_summary["successful"]))
        fetch_table.add_row("Success Rate", f"{fetch_summary['success_rate']:.1%}")

        console.print(fetch_table)

        # Show URLs
        console.print("\n[dim]Retrieved URLs:[/dim]")
        for result in fetch_results:
            if result.success:
                console.print(f"  📄 {result.paper.title[:40]}...")
                console.print(f"     [link]{result.pdf_url}[/link]")
    else:
        console.print("[yellow]No papers were included after screening[/yellow]")

    # Final summary
    console.print("\n" + "=" * 60)
    console.print(Panel.fit(
        f"[bold]Summary:[/bold]\n"
        f"• Searched {len(DATABASES)} databases\n"
        f"• Found {search_result.prisma_flow.total_identified} records\n"
        f"• After deduplication: {len(search_result.papers)} unique papers\n"
        f"• Screened: {len(papers_to_screen)} papers\n"
        f"• Included: {summary['included']} papers\n"
        f"• Retrieved: {fetch_summary.get('successful', 0) if included_papers else 0} full texts",
        title="🎉 Demo Complete"
    ))


if __name__ == "__main__":
    asyncio.run(main())
