#!/usr/bin/env python3
"""
Demo script showing human-in-the-loop review in action.

NOTE: This script includes interactive prompts - run it to see the full experience!
"""

import asyncio
from rich.console import Console
from rich.panel import Panel

from arakis.agents.screener import ScreeningAgent
from arakis.models.screening import ScreeningCriteria
from arakis.models.paper import Paper, Author, PaperSource


def create_demo_papers():
    """Create realistic demo papers for human review."""

    return [
        Paper(
            id="demo_1",
            title="Aspirin for prevention of sepsis in critically ill adult patients: a multicenter randomized controlled trial",
            abstract="Background: Sepsis remains a major cause of mortality in intensive care units. This study evaluates the efficacy of low-dose aspirin in preventing sepsis. Methods: We conducted a double-blind, placebo-controlled RCT across 15 ICUs in 5 countries. 800 adult patients (≥18 years) at high risk of sepsis were randomized to aspirin (81mg daily) or placebo for 14 days. Primary outcome was new-onset sepsis within 30 days. Results: Aspirin group had 23% incidence of sepsis vs 31% in placebo group (RR 0.74, 95% CI 0.61-0.91, p=0.004). Secondary outcomes included 28-day mortality (15% vs 19%, p=0.03) and organ failure scores. No increase in bleeding events was observed. Conclusion: Low-dose aspirin significantly reduces sepsis incidence and mortality in high-risk ICU patients.",
            year=2024,
            authors=[
                Author(name="Smith J"),
                Author(name="Johnson K"),
                Author(name="Williams R"),
                Author(name="Brown T")
            ],
            source=PaperSource.PUBMED,
            journal="Critical Care Medicine",
            publication_types=["Randomized Controlled Trial", "Multicenter Study"]
        ),
        Paper(
            id="demo_2",
            title="Retrospective analysis of aspirin use in pediatric septic shock: a single-center study",
            abstract="We examined the association between aspirin use and outcomes in 150 children (ages 2-12) with septic shock admitted to our pediatric ICU between 2018-2022. Aspirin use was documented in 45 patients (30%). Primary outcome was PICU mortality. Results showed no significant difference in mortality between aspirin users (22%) and non-users (24%, p=0.78). Secondary outcomes including length of stay and ventilator days were also similar. This retrospective analysis suggests limited benefit of aspirin in pediatric septic shock, though prospective trials are needed.",
            year=2023,
            authors=[
                Author(name="Garcia M"),
                Author(name="Martinez J")
            ],
            source=PaperSource.OPENALEX,
            journal="Pediatric Critical Care",
            publication_types=["Retrospective Study"]
        ),
        Paper(
            id="demo_3",
            title="Aspirin and cardiovascular biomarkers in septic patients: an observational cohort",
            abstract="This prospective observational study enrolled 200 adult patients with sepsis to examine the relationship between aspirin use and cardiovascular biomarkers. Patients were followed for 90 days. We measured troponin, BNP, and inflammatory markers at baseline and days 3, 7, and 14. Aspirin users (n=85) showed lower troponin levels and reduced incidence of myocardial injury compared to non-users. However, the study was not powered to detect mortality differences. Further research with larger samples is warranted.",
            year=2023,
            authors=[
                Author(name="Chen L"),
                Author(name="Zhang Y"),
                Author(name="Liu W")
            ],
            source=PaperSource.PUBMED,
            journal="Journal of Critical Care",
            publication_types=["Observational Study", "Cohort Study"]
        )
    ]


async def main():
    console = Console()

    # Display introduction
    console.print("\n" + "="*80)
    console.print(Panel.fit(
        "[bold cyan]Human-in-the-Loop Review Demo[/bold cyan]\n\n"
        "This demo shows how human review works in Arakis.\n"
        "You'll review AI screening decisions for 3 papers.",
        title="Interactive Demo"
    ))
    console.print("="*80 + "\n")

    console.print("[bold]Screening Criteria:[/bold]")
    console.print("  [green]Include:[/green]")
    console.print("    • Adult patients (≥18 years)")
    console.print("    • Sepsis or septic shock as primary condition")
    console.print("    • Aspirin as intervention")
    console.print("    • Mortality or clinical outcomes reported")
    console.print("  [red]Exclude:[/red]")
    console.print("    • Pediatric patients (<18 years)")
    console.print("    • Animal or in vitro studies")
    console.print("    • Review articles without original data")
    console.print()

    input("Press Enter to begin screening...")

    # Create criteria and agent
    criteria = ScreeningCriteria(
        inclusion=[
            "Adult patients (≥18 years)",
            "Sepsis or septic shock as primary condition",
            "Aspirin as intervention",
            "Mortality or clinical outcomes reported"
        ],
        exclusion=[
            "Pediatric patients (<18 years)",
            "Animal or in vitro studies",
            "Review articles without original data"
        ]
    )

    agent = ScreeningAgent()
    papers = create_demo_papers()

    # Screen papers with human review
    console.print(f"\n[bold cyan]Screening {len(papers)} papers with human-in-the-loop review...[/bold cyan]\n")

    decisions = await agent.screen_batch(
        papers,
        criteria,
        dual_review=False,     # Single-pass AI
        human_review=True      # Enable human review
    )

    # Display summary
    console.print("\n" + "="*80)
    console.print("[bold]Screening Complete![/bold]")
    console.print("="*80 + "\n")

    summary = agent.summarize_screening(decisions)

    console.print("[bold]Summary Statistics:[/bold]")
    console.print(f"  Total papers: {summary['total']}")
    console.print(f"  Included: [green]{summary['included']}[/green]")
    console.print(f"  Excluded: [red]{summary['excluded']}[/red]")
    console.print(f"  Maybe: [yellow]{summary['maybe']}[/yellow]")
    console.print(f"  Human reviewed: {summary['human_reviewed']}")
    console.print(f"  Human overrides: {summary['human_overrides']}")
    console.print(f"  Override rate: {summary['override_rate']:.1%}")

    # Display decisions
    console.print("\n[bold]Decision Details:[/bold]\n")

    for i, decision in enumerate(decisions, 1):
        paper = papers[i-1]
        console.print(f"[cyan]Paper {i}:[/cyan] {paper.title[:60]}...")

        status_color = "green" if decision.status.value == "include" else "red" if decision.status.value == "exclude" else "yellow"
        console.print(f"  Final decision: [{status_color}]{decision.status.value.upper()}[/{status_color}]")

        if decision.overridden:
            console.print(f"  [yellow]→ Human overrode AI:[/yellow]")
            console.print(f"    AI decided: {decision.ai_decision.value.upper()}")
            console.print(f"    Human decided: {decision.human_decision.value.upper()}")
            if decision.human_reason:
                console.print(f"    Reason: {decision.human_reason}")
        else:
            console.print(f"  [green]→ Human agreed with AI[/green]")

        console.print()

    # Explanation
    console.print("\n" + "="*80)
    console.print("[bold]What Just Happened?[/bold]")
    console.print("="*80 + "\n")

    console.print("1. [cyan]AI Screening:[/cyan] Each paper was screened by GPT-4o")
    console.print("2. [cyan]Human Review:[/cyan] You reviewed each AI decision")
    console.print("3. [cyan]Override Tracking:[/cyan] System recorded agreements and overrides")
    console.print("4. [cyan]Quality Metrics:[/cyan] Override rate shows AI-human agreement")
    console.print()

    console.print("[bold]Key Benefits:[/bold]")
    console.print("  • [green]Quality Control:[/green] Human oversight of AI decisions")
    console.print("  • [green]Transparency:[/green] Full audit trail (AI + human reasoning)")
    console.print("  • [green]Flexibility:[/green] Override when AI is wrong")
    console.print("  • [green]Metrics:[/green] Override rate as quality indicator")
    console.print()

    console.print("[bold]When to Use:[/bold]")
    console.print("  • Small batches (<50 papers)")
    console.print("  • Need human verification")
    console.print("  • Building confidence in AI")
    console.print("  • Review of conflicts/uncertain cases")
    console.print()

    console.print("[dim]For large batches, use dual-review mode (default) instead.[/dim]\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
