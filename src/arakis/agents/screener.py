"""LLM-powered paper screening agent."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.audit import AuditEventType
from arakis.models.paper import Paper
from arakis.models.screening import ScreeningCriteria, ScreeningDecision, ScreeningStatus
from arakis.utils import BatchProcessor, retry_with_exponential_backoff

SCREENING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "screen_paper",
            "description": "Make a screening decision for a paper",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["INCLUDE", "EXCLUDE", "MAYBE"],
                        "description": "The screening decision",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence in the decision (0-1)",
                    },
                    "reason": {"type": "string", "description": "Detailed reason for the decision"},
                    "matched_inclusion": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which inclusion criteria the paper meets",
                    },
                    "matched_exclusion": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which exclusion criteria the paper meets",
                    },
                },
                "required": ["decision", "confidence", "reason"],
            },
        },
    }
]


class ScreeningAgent:
    """
    LLM-powered agent for screening papers against criteria.

    Default mode: Dual reviewer (two independent passes with conflict detection)
    for higher reliability and systematic review quality assurance.

    Features:
    - Dual reviewer mode (default): Two passes with different temperatures
    - Automatic conflict detection and flagging
    - Single review mode: Available for faster processing
    - Batch processing with progress tracking
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model

    @retry_with_exponential_backoff(max_retries=8, initial_delay=2.0, max_delay=90.0)
    async def _call_openai(
        self,
        messages: list[dict],
        tools: list | None = None,
        tool_choice: dict | str = "auto",
        temperature: float = 0.3,
    ):
        """
        Call OpenAI API with retry logic for rate limits.

        Args:
            messages: List of message dicts
            tools: Optional list of tool definitions
            tool_choice: Tool choice strategy or specific function
            temperature: Temperature for generation

        Returns:
            OpenAI completion response
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return await self.client.chat.completions.create(**kwargs)

    def _get_system_prompt(self, criteria: ScreeningCriteria) -> str:
        """Generate system prompt for screening."""
        return f"""You are an expert systematic reviewer screening papers for inclusion.

Your task is to evaluate each paper against the following criteria:

{criteria.to_prompt()}

SCREENING RULES:
1. INCLUDE: Paper clearly meets all inclusion criteria and none of the exclusion criteria
2. EXCLUDE: Paper clearly meets any exclusion criteria OR fails to meet key inclusion criteria
3. MAYBE: Paper is unclear - insufficient information in title/abstract to decide

DECISION GUIDELINES:
- Be conservative: when in doubt, mark as MAYBE for human review
- Base decisions ONLY on the provided title and abstract
- Do not assume information not explicitly stated
- Consider study design, population, intervention, and outcomes

For each paper, call the screen_paper function with your decision."""

    def _prompt_human_review(
        self, paper: Paper, ai_decision: ScreeningDecision, criteria: ScreeningCriteria
    ) -> tuple[ScreeningStatus, str | None]:
        """
        Prompt human for review of AI decision.

        Args:
            paper: Paper being reviewed
            ai_decision: AI's screening decision
            criteria: Screening criteria

        Returns:
            Tuple of (human_decision, human_reason)
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Confirm, Prompt

        console = Console()

        # Display paper info
        console.print("\n" + "=" * 80)
        console.print(
            Panel.fit(
                f"[bold cyan]Human Review Required[/bold cyan]\n\nPaper ID: {paper.id}",
                title="Screening Review",
            )
        )

        console.print("\n[bold]Title:[/bold]")
        console.print(f"  {paper.title}")

        console.print("\n[bold]Abstract:[/bold]")
        abstract_preview = (
            paper.abstract[:500] + "..."
            if paper.abstract and len(paper.abstract) > 500
            else paper.abstract or "No abstract available"
        )
        console.print(f"  {abstract_preview}")

        console.print("\n[bold]Metadata:[/bold]")
        console.print(f"  Year: {paper.year or 'Unknown'}")
        console.print(f"  Authors: {paper.authors_string[:100] if paper.authors else 'Unknown'}")
        console.print(f"  Journal: {paper.journal or 'Unknown'}")

        # Display AI decision
        status_color = (
            "green"
            if ai_decision.status == ScreeningStatus.INCLUDE
            else "red"
            if ai_decision.status == ScreeningStatus.EXCLUDE
            else "yellow"
        )
        console.print(
            f"\n[bold]AI Decision:[/bold] [{status_color}]{ai_decision.status.value.upper()}[/{status_color}]"
        )
        console.print(f"[bold]Confidence:[/bold] {ai_decision.confidence:.2f}")
        console.print(f"[bold]Reason:[/bold] {ai_decision.reason}")

        if ai_decision.matched_inclusion:
            console.print("\n[bold]Matched Inclusion Criteria:[/bold]")
            for criterion in ai_decision.matched_inclusion:
                console.print(f"  • {criterion}")

        if ai_decision.matched_exclusion:
            console.print("\n[bold]Matched Exclusion Criteria:[/bold]")
            for criterion in ai_decision.matched_exclusion:
                console.print(f"  • {criterion}")

        # Prompt for human decision
        console.print("\n" + "-" * 80)
        console.print("[bold yellow]Your Review:[/bold yellow]")

        # Ask if human agrees with AI
        agrees = Confirm.ask("Do you agree with the AI decision?", default=True)

        if agrees:
            return ai_decision.status, None

        # Human disagrees - get override decision
        console.print("\n[bold]Override Decision:[/bold]")
        console.print("  1. INCLUDE - Paper should be included")
        console.print("  2. EXCLUDE - Paper should be excluded")
        console.print("  3. MAYBE - Uncertain, needs further review")

        choice = Prompt.ask("Select decision", choices=["1", "2", "3"], default="3")

        status_map = {
            "1": ScreeningStatus.INCLUDE,
            "2": ScreeningStatus.EXCLUDE,
            "3": ScreeningStatus.MAYBE,
        }
        human_status = status_map[choice]

        # Get reason for override
        human_reason = Prompt.ask("Reason for override (optional)", default="")

        return human_status, human_reason or None

    async def screen_paper(
        self,
        paper: Paper,
        criteria: ScreeningCriteria,
        dual_review: bool = True,
        human_review: bool = False,
    ) -> ScreeningDecision:
        """
        Screen a single paper against criteria.

        Args:
            paper: Paper to screen
            criteria: Inclusion/exclusion criteria
            dual_review: If True (default), make two independent passes and flag conflicts.
                        Set to False for single-pass screening (faster but less reliable).
            human_review: If True and dual_review=False, prompt human to review AI decision.
                         Allows human override of AI decisions for quality control.

        Returns:
            ScreeningDecision with status, reason, and confidence
        """
        # Ensure paper has audit trail
        trail = paper.ensure_audit_trail()

        # Record screening started
        trail.add_event(
            event_type=AuditEventType.SCREENING_STARTED,
            description="Screening process started",
            actor="ScreeningAgent",
            details={
                "dual_review": dual_review,
                "human_review": human_review,
                "model": self.model,
            },
            stage="screening",
        )

        # Dual-review mode (default) - human_review is ignored in this mode
        if dual_review:
            # First pass
            decision1 = await self._single_screen(paper, criteria)
            trail.add_event(
                event_type=AuditEventType.SCREENING_PASS_1,
                description=f"First pass: {decision1.status.value}",
                actor="ScreeningAgent",
                details={
                    "decision": decision1.status.value,
                    "confidence": decision1.confidence,
                    "reason": decision1.reason,
                    "matched_inclusion": decision1.matched_inclusion,
                    "matched_exclusion": decision1.matched_exclusion,
                },
                stage="screening",
                model_used=self.model,
                temperature=0.3,
            )

            # Second pass with different temperature
            decision2 = await self._single_screen(paper, criteria, temperature=0.7)
            trail.add_event(
                event_type=AuditEventType.SCREENING_PASS_2,
                description=f"Second pass: {decision2.status.value}",
                actor="ScreeningAgent",
                details={
                    "decision": decision2.status.value,
                    "confidence": decision2.confidence,
                    "reason": decision2.reason,
                    "matched_inclusion": decision2.matched_inclusion,
                    "matched_exclusion": decision2.matched_exclusion,
                },
                stage="screening",
                model_used=self.model,
                temperature=0.7,
            )

            # Check for conflict
            if decision1.status != decision2.status:
                decision1.is_conflict = True
                decision1.second_opinion = decision2

                trail.add_event(
                    event_type=AuditEventType.SCREENING_CONFLICT,
                    description=f"Conflict detected: {decision1.status.value} vs {decision2.status.value}",
                    actor="ScreeningAgent",
                    details={
                        "pass_1_decision": decision1.status.value,
                        "pass_2_decision": decision2.status.value,
                    },
                    stage="screening",
                )

                # When in conflict, default to MAYBE
                original_status = decision1.status
                if decision1.status != ScreeningStatus.MAYBE:
                    decision1.status = ScreeningStatus.MAYBE
                    decision1.reason = (
                        f"CONFLICT: First pass: {original_status.value}, "
                        f"Second pass: {decision2.status.value}. "
                        f"Original reason: {decision1.reason}"
                    )
                    decision1.confidence = min(decision1.confidence, decision2.confidence) * 0.5

                trail.add_event(
                    event_type=AuditEventType.SCREENING_RESOLVED,
                    description=f"Conflict resolved to {decision1.status.value}",
                    actor="ScreeningAgent",
                    details={
                        "resolution": "defaulted_to_maybe",
                        "final_decision": decision1.status.value,
                        "final_confidence": decision1.confidence,
                    },
                    stage="screening",
                )

            # Record final screening decision
            trail.add_event(
                event_type=AuditEventType.SCREENING_COMPLETED,
                description=f"Screening completed: {decision1.status.value}",
                actor="ScreeningAgent",
                details={
                    "final_decision": decision1.status.value,
                    "final_confidence": decision1.confidence,
                    "had_conflict": decision1.is_conflict,
                },
                stage="screening",
            )

            return decision1

        # Single-review mode (dual_review=False)
        decision = await self._single_screen(paper, criteria)

        trail.add_event(
            event_type=AuditEventType.SCREENING_PASS_1,
            description=f"Single-pass screening: {decision.status.value}",
            actor="ScreeningAgent",
            details={
                "decision": decision.status.value,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "matched_inclusion": decision.matched_inclusion,
                "matched_exclusion": decision.matched_exclusion,
            },
            stage="screening",
            model_used=self.model,
            temperature=0.3,
        )

        # Human-in-the-loop review (only in single-review mode)
        if human_review:
            # Store original AI decision
            decision.ai_decision = decision.status
            decision.ai_reason = decision.reason

            # Prompt human for review
            human_status, human_reason = self._prompt_human_review(paper, decision, criteria)

            trail.add_event(
                event_type=AuditEventType.SCREENING_HUMAN_REVIEW,
                description="Human review completed",
                actor="human",
                details={
                    "ai_decision": decision.ai_decision.value,
                    "human_decision": human_status.value,
                    "agrees_with_ai": human_status == decision.ai_decision,
                },
                stage="screening",
            )

            # Check if human overrode AI decision
            if human_status != decision.status:
                decision.overridden = True
                decision.human_decision = human_status
                decision.human_reason = human_reason
                decision.status = human_status
                decision.screener = f"{decision.screener} (overridden by human)"

                trail.add_event(
                    event_type=AuditEventType.SCREENING_HUMAN_OVERRIDE,
                    description=f"Human overrode AI decision: {decision.ai_decision.value} → {human_status.value}",
                    actor="human",
                    details={
                        "original_decision": decision.ai_decision.value,
                        "new_decision": human_status.value,
                        "human_reason": human_reason,
                    },
                    stage="screening",
                )

                # Update reason to include both AI and human reasoning
                if human_reason:
                    decision.reason = (
                        f"Human override: {human_reason}. Original AI reasoning: {decision.reason}"
                    )
                else:
                    decision.reason = f"Human overrode AI decision from {decision.ai_decision.value} to {human_status.value}. Original AI reasoning: {decision.reason}"

            decision.human_reviewed = True

        # Record final screening decision
        trail.add_event(
            event_type=AuditEventType.SCREENING_COMPLETED,
            description=f"Screening completed: {decision.status.value}",
            actor="ScreeningAgent",
            details={
                "final_decision": decision.status.value,
                "final_confidence": decision.confidence,
                "human_reviewed": decision.human_reviewed,
                "overridden": decision.overridden,
            },
            stage="screening",
        )

        return decision

    async def _single_screen(
        self, paper: Paper, criteria: ScreeningCriteria, temperature: float = 0.3
    ) -> ScreeningDecision:
        """Execute a single screening pass."""
        # Prepare paper info
        paper_text = f"""Title: {paper.title}

Abstract: {paper.abstract or "No abstract available"}

Year: {paper.year or "Unknown"}
Journal: {paper.journal or "Unknown"}
Publication Types: {", ".join(paper.publication_types) or "Unknown"}"""

        user_prompt = f"""Screen the following paper:

{paper_text}

Use the screen_paper function to make your decision."""

        response = await self._call_openai(
            messages=[
                {"role": "system", "content": self._get_system_prompt(criteria)},
                {"role": "user", "content": user_prompt},
            ],
            tools=SCREENING_TOOLS,
            tool_choice={"type": "function", "function": {"name": "screen_paper"}},
            temperature=temperature,
        )

        # Parse response
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            try:
                args = json.loads(tool_call.function.arguments)
                return self._parse_decision(paper.id, args)
            except json.JSONDecodeError:
                pass

        # Default to MAYBE if parsing fails
        return ScreeningDecision(
            paper_id=paper.id,
            status=ScreeningStatus.MAYBE,
            reason="Failed to parse screening decision",
            confidence=0.0,
            screener=self.model,
        )

    def _parse_decision(self, paper_id: str, args: dict[str, Any]) -> ScreeningDecision:
        """Parse tool call arguments into ScreeningDecision."""
        status_str = args.get("decision", "MAYBE").upper()
        status_map = {
            "INCLUDE": ScreeningStatus.INCLUDE,
            "EXCLUDE": ScreeningStatus.EXCLUDE,
            "MAYBE": ScreeningStatus.MAYBE,
        }
        status = status_map.get(status_str, ScreeningStatus.MAYBE)

        return ScreeningDecision(
            paper_id=paper_id,
            status=status,
            reason=args.get("reason", ""),
            confidence=args.get("confidence", 0.5),
            matched_inclusion=args.get("matched_inclusion", []),
            matched_exclusion=args.get("matched_exclusion", []),
            screener=self.model,
        )

    async def screen_batch(
        self,
        papers: list[Paper],
        criteria: ScreeningCriteria,
        dual_review: bool = True,
        human_review: bool = False,
        progress_callback: callable = None,
        batch_size: int | None = None,
    ) -> list[ScreeningDecision]:
        """
        Screen multiple papers with configurable concurrent batch processing.

        Papers are processed concurrently within each batch to improve throughput
        while respecting API rate limits. Rate limiting is handled by the
        @retry_with_exponential_backoff decorator on individual API calls.

        Args:
            papers: List of papers to screen
            criteria: Screening criteria
            dual_review: Enable dual reviewer mode (default: True).
                        Set to False for faster single-pass screening.
            human_review: If True and dual_review=False, prompt human to review each AI decision.
                         Ignored when dual_review=True. Forces sequential processing.
            progress_callback: Optional callback for progress updates.
                Signature: callback(current, total, paper, decision)
                - current: Current paper index (1-indexed)
                - total: Total number of papers
                - paper: The Paper object being processed
                - decision: The ScreeningDecision made for the paper
            batch_size: Override the default batch size from settings.
                       If None, uses settings.batch_size_screening (default: 5).

        Returns:
            List of ScreeningDecisions in same order as input papers
        """
        # Human review requires sequential processing (interactive prompts)
        if human_review and not dual_review:
            results = []
            for i, paper in enumerate(papers):
                decision = await self.screen_paper(paper, criteria, dual_review, human_review)
                results.append(decision)
                if progress_callback:
                    progress_callback(i + 1, len(papers), paper, decision)
            return results

        # Use concurrent batch processing
        processor = BatchProcessor(
            batch_size=batch_size,
            batch_size_key="batch_size_screening",
        )

        async def process_paper(paper: Paper) -> ScreeningDecision:
            return await self.screen_paper(paper, criteria, dual_review, human_review)

        return await processor.process(papers, process_paper, progress_callback)

    def summarize_screening(self, decisions: list[ScreeningDecision]) -> dict[str, Any]:
        """
        Summarize screening results.

        Returns:
            Dict with counts, conflict rate, and human review statistics
        """
        total = len(decisions)
        included = sum(1 for d in decisions if d.status == ScreeningStatus.INCLUDE)
        excluded = sum(1 for d in decisions if d.status == ScreeningStatus.EXCLUDE)
        maybe = sum(1 for d in decisions if d.status == ScreeningStatus.MAYBE)
        conflicts = sum(1 for d in decisions if d.is_conflict)

        # Human review statistics
        human_reviewed = sum(1 for d in decisions if d.human_reviewed)
        overridden = sum(1 for d in decisions if d.overridden)

        avg_confidence = sum(d.confidence for d in decisions) / total if total > 0 else 0

        summary = {
            "total": total,
            "included": included,
            "excluded": excluded,
            "maybe": maybe,
            "conflicts": conflicts,
            "conflict_rate": conflicts / total if total > 0 else 0,
            "average_confidence": avg_confidence,
            "human_reviewed": human_reviewed,
            "human_overrides": overridden,
            "override_rate": overridden / human_reviewed if human_reviewed > 0 else 0,
        }

        return summary
