"""Results section writer agent.

LLM-powered agent that writes the results section of a systematic review.
"""

import json
import time
from typing import Any

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.analysis import MetaAnalysisResult, NarrativeSynthesisResult
from arakis.models.paper import Paper
from arakis.models.screening import ScreeningDecision
from arakis.models.visualization import PRISMAFlow
from arakis.models.writing import Section, WritingResult
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class ResultsWriterAgent:
    """LLM agent that writes results section for systematic reviews."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.5, max_tokens: int = 4000):
        """Initialize the results writer agent.

        Args:
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rate_limiter = get_openai_rate_limiter()

    @retry_with_exponential_backoff(
        max_retries=8, initial_delay=2.0, max_delay=90.0, use_rate_limiter=True
    )
    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str = "auto",
        temperature: float | None = None,
    ):
        """Call OpenAI API with retry logic.

        Args:
            messages: Chat messages
            tools: Tool definitions (optional)
            tool_choice: Tool choice strategy
            temperature: Override default temperature

        Returns:
            OpenAI completion response
        """
        await self.rate_limiter.wait()

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return await self.client.chat.completions.create(**kwargs)

    def _get_system_prompt(self) -> str:
        """Get system prompt for results writer."""
        return """You are an expert scientific writer specializing in systematic reviews and meta-analyses. Your task is to write clear, accurate, and well-structured results sections following academic standards (e.g., PRISMA guidelines).

**Writing Guidelines:**

1. **Objectivity**: Report findings objectively without interpretation or speculation
2. **Clarity**: Use clear, concise language appropriate for medical/scientific journals
3. **Structure**: Organize logically with clear subsections
4. **Numbers**: Report all key statistics with appropriate precision (e.g., p-values to 4 decimals, effects to 2-3 decimals)
5. **Tense**: Use past tense for describing what was done, present tense for findings
6. **Figures**: Reference figures and tables appropriately (e.g., "See Figure 1")

**Results Section Structure:**

1. **Study Selection**: Describe search results, screening process, and final inclusions (with PRISMA flow)
2. **Study Characteristics**: Summarize included studies (populations, interventions, outcomes)
3. **Risk of Bias**: Report quality assessment findings (if available)
4. **Synthesis of Results**: Present main findings, effect estimates, heterogeneity, subgroup analyses

**Key Points:**
- Start with study selection narrative that references PRISMA diagram
- Describe included studies systematically (design, sample size, population, intervention)
- Report meta-analysis results with pooled effects, confidence intervals, p-values, and I²
- Mention heterogeneity and how it was addressed
- Reference figures explicitly (e.g., "forest plot showed..." → "Forest plot (Figure 1) showed...")
- Keep sentences focused and avoid redundancy
- Do not include citations to specific papers (those go in discussion)

**Avoid:**
- Interpretation of results (save for discussion)
- Speculation about causality or mechanisms
- Recommendations or clinical implications
- Personal opinions or value judgments"""

    async def write_study_selection(
        self,
        prisma_flow: PRISMAFlow,
        total_papers_searched: int,
        screening_summary: dict[str, int] | None = None,
        screening_decisions: list[ScreeningDecision] | None = None,
    ) -> WritingResult:
        """Write the study selection subsection with PRISMA-compliant narrative.

        Args:
            prisma_flow: PRISMA flow data
            total_papers_searched: Total records from database searches
            screening_summary: Summary of screening results (optional)
            screening_decisions: List of screening decisions with exclusion reasons (optional)

        Returns:
            WritingResult with generated text including detailed exclusion reasons
        """
        start_time = time.time()

        # Prepare context with exact numbers at each stage
        context = {
            "total_identified": prisma_flow.records_identified_total,
            "duplicates_removed": prisma_flow.records_removed_duplicates,
            "records_after_deduplication": prisma_flow.records_after_deduplication,
            "records_screened": prisma_flow.records_screened,
            "records_excluded": prisma_flow.records_excluded,
            "reports_sought": prisma_flow.reports_sought,
            "reports_not_retrieved": prisma_flow.reports_not_retrieved,
            "reports_assessed": prisma_flow.reports_assessed,
            "reports_excluded": prisma_flow.reports_excluded,
            "studies_included": prisma_flow.studies_included,
            "databases": prisma_flow.records_identified_databases,
        }

        # Add exclusion reasons from PRISMA flow if available
        if prisma_flow.exclusion_reasons:
            context["title_abstract_exclusion_reasons"] = prisma_flow.exclusion_reasons
        if prisma_flow.reports_exclusion_reasons:
            context["fulltext_exclusion_reasons"] = prisma_flow.reports_exclusion_reasons

        # Extract and aggregate exclusion reasons from screening decisions
        if screening_decisions:
            exclusion_reasons_summary = self._aggregate_exclusion_reasons(screening_decisions)
            context["exclusion_reasons_detail"] = exclusion_reasons_summary

        if screening_summary:
            context["screening_details"] = screening_summary

        prompt = f"""Write the "Study Selection" subsection for a systematic review results section.

**PRISMA Flow Data:**
{json.dumps(context, indent=2)}

**Requirements (PRISMA 2020 Compliant):**
1. **Identification Stage**: Report exact number of records identified from each database
2. **Duplicate Removal**: State exact number of duplicates removed
3. **Title/Abstract Screening**: Report records screened and excluded with specific reasons
4. **Full-Text Assessment**: Report articles assessed, not retrieved, and excluded with reasons
5. **Final Inclusion**: Report final number of studies included in the review

**Structure:**
- Start with total records identified across databases
- Describe duplicate removal process
- Detail title/abstract screening with reasons for exclusion (grouped by reason)
- Detail full-text review with reasons for exclusion (grouped by reason)
- End with final inclusion count
- Reference "Figure 1" (PRISMA flow diagram) at the end

**Length:** 200-300 words

**Precision Requirements:**
- Use exact numbers (not approximations)
- List top 3-5 exclusion reasons with counts
- Use past tense for completed actions

**Example structure:**
"The literature search identified X records (PubMed: n=A, OpenAlex: n=B, ...). After removing Y duplicates, Z records remained for title and abstract screening. Of these, N records were excluded: [reason 1] (n=X), [reason 2] (n=Y), ... Full-text articles were sought for M records; P could not be retrieved. After full-text assessment, Q articles were excluded: [reason 1] (n=X), [reason 2] (n=Y), ... A total of R studies met the inclusion criteria and were included in the review (Figure 1)."

Write only the paragraph text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Study Selection", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    def _aggregate_exclusion_reasons(self, decisions: list[ScreeningDecision]) -> dict[str, Any]:
        """Aggregate exclusion reasons from screening decisions.

        Args:
            decisions: List of screening decisions

        Returns:
            Dictionary with aggregated exclusion reasons and counts
        """
        from collections import Counter

        exclusion_reasons: Counter[str] = Counter()
        matched_exclusion_criteria: Counter[str] = Counter()

        for decision in decisions:
            if decision.status.value == "exclude":
                # Count the primary reason
                if decision.reason:
                    # Normalize and truncate long reasons
                    reason = decision.reason.strip()
                    if len(reason) > 100:
                        reason = reason[:97] + "..."
                    exclusion_reasons[reason] += 1

                # Count matched exclusion criteria
                for criterion in decision.matched_exclusion:
                    matched_exclusion_criteria[criterion] += 1

        return {
            "total_excluded": sum(exclusion_reasons.values()),
            "reasons_with_counts": dict(exclusion_reasons.most_common(10)),
            "exclusion_criteria_matched": dict(matched_exclusion_criteria.most_common(10)),
        }

    async def write_study_characteristics(
        self,
        included_papers: list[Paper],
        extraction_summary: dict[str, Any] | None = None,
    ) -> WritingResult:
        """Write the study characteristics subsection.

        Args:
            included_papers: List of included papers
            extraction_summary: Summary of extracted characteristics

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Prepare paper summaries
        paper_summaries = []
        for paper in included_papers[:10]:  # Limit to first 10 for context
            summary = {
                "title": paper.title[:100] + "..." if len(paper.title) > 100 else paper.title,
                "year": paper.year,
                "journal": paper.journal,
            }
            paper_summaries.append(summary)

        context = {
            "total_studies": len(included_papers),
            "sample_papers": paper_summaries,
            "extraction_summary": extraction_summary or {},
        }

        prompt = f"""Write the "Study Characteristics" subsection for a systematic review results section.

**Data:**
{json.dumps(context, indent=2)}

**Requirements:**
- Summarize the characteristics of included studies
- Mention: study designs, publication years, sample sizes, populations, interventions
- Use Table 1 reference for detailed characteristics
- Length: 100-150 words
- Be concise and descriptive

**Example:** "The {len(included_papers)} included studies were published between YEAR and YEAR. Studies examined..."

Write only the paragraph text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Study Characteristics", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_synthesis_of_results(
        self, meta_analysis_result: MetaAnalysisResult, outcome_name: str
    ) -> WritingResult:
        """Write the synthesis of results subsection.

        Args:
            meta_analysis_result: Meta-analysis results
            outcome_name: Name of the outcome analyzed

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Prepare analysis summary
        context = {
            "outcome": outcome_name,
            "studies_included": meta_analysis_result.studies_included,
            "total_sample_size": meta_analysis_result.total_sample_size,
            "pooled_effect": round(meta_analysis_result.pooled_effect, 3),
            "ci_lower": round(meta_analysis_result.confidence_interval.lower, 3),
            "ci_upper": round(meta_analysis_result.confidence_interval.upper, 3),
            "p_value": meta_analysis_result.p_value,
            "effect_measure": meta_analysis_result.effect_measure.value,
            "is_significant": meta_analysis_result.is_significant,
            "i_squared": round(meta_analysis_result.heterogeneity.i_squared, 1),
            "q_p_value": meta_analysis_result.heterogeneity.q_p_value,
            "analysis_method": meta_analysis_result.analysis_method.value,
        }

        prompt = f"""Write the "Synthesis of Results" subsection for a systematic review results section.

**Meta-Analysis Results:**
{json.dumps(context, indent=2)}

**Requirements:**
- Report the meta-analysis findings for the primary outcome
- Include: number of studies, sample size, pooled effect with CI, p-value
- Mention heterogeneity (I² statistic) and analysis method used
- Reference "Figure 2" (forest plot) when describing effect estimates
- Use appropriate statistical terminology
- Length: 150-200 words

**Example opening:** "Meta-analysis of {meta_analysis_result.studies_included} studies (n={meta_analysis_result.total_sample_size}) showed..."

Write only the paragraph text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Synthesis of Results", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_narrative_synthesis_results(
        self, narrative_result: NarrativeSynthesisResult
    ) -> WritingResult:
        """Write the synthesis of results subsection for narrative synthesis.

        Used when meta-analysis is not feasible. Generates PRISMA-compliant
        narrative description of findings across studies.

        Args:
            narrative_result: Narrative synthesis results

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Prepare context from narrative synthesis
        vote_count_data: dict[str, Any] = {}
        if narrative_result.vote_count:
            vote_count_data = {
                "positive": narrative_result.vote_count.positive,
                "negative": narrative_result.vote_count.negative,
                "null": narrative_result.vote_count.null,
                "mixed": narrative_result.vote_count.mixed,
                "predominant_direction": narrative_result.vote_count.predominant_direction,
                "consistency": narrative_result.vote_count.consistency,
            }

        context: dict[str, Any] = {
            "outcome": narrative_result.outcome_name,
            "studies_included": narrative_result.studies_included,
            "total_sample_size": narrative_result.total_sample_size,
            "vote_count": vote_count_data,
            "summary_of_findings": narrative_result.summary_of_findings,
            "patterns_identified": narrative_result.patterns_identified[:3],  # Top 3
            "inconsistencies": narrative_result.inconsistencies[:3],  # Top 3
            "heterogeneity_explanation": narrative_result.heterogeneity_explanation,
            "confidence_in_evidence": narrative_result.confidence_in_evidence,
            "meta_analysis_barriers": narrative_result.meta_analysis_barriers,
        }

        prompt = f"""Write the "Synthesis of Results" subsection for a systematic review results section.

**IMPORTANT:** Meta-analysis was NOT feasible for this review. Write a narrative synthesis instead.

**Narrative Synthesis Data:**
{json.dumps(context, indent=2)}

**Requirements (PRISMA 2020 Compliant Narrative Synthesis):**
1. State why meta-analysis was not conducted (barriers listed above)
2. Describe the vote counting results (how many studies showed positive/negative/null effects)
3. Report the predominant direction of effect and consistency across studies
4. Mention key patterns identified across studies
5. Note any inconsistencies or conflicting findings
6. Report the confidence in the evidence
7. Reference the effect direction chart (Figure 2) if applicable

**Structure:**
- Opening: Why meta-analysis was not feasible
- Vote counting: Summarize effect directions across studies
- Patterns: Notable findings across study characteristics
- Heterogeneity: Explain sources of variation
- Conclusion: Overall confidence and interpretation

**Length:** 200-300 words

**Example opening:** "Due to [heterogeneity/insufficient data/variation in outcomes], quantitative synthesis (meta-analysis) was not feasible. Therefore, findings were synthesized narratively..."

Write only the paragraph text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Synthesis of Results", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_complete_results_section(
        self,
        prisma_flow: PRISMAFlow,
        included_papers: list[Paper],
        meta_analysis_result: MetaAnalysisResult | None = None,
        narrative_synthesis_result: NarrativeSynthesisResult | None = None,
        outcome_name: str = "primary outcome",
        extraction_summary: dict[str, Any] | None = None,
        screening_decisions: list[ScreeningDecision] | None = None,
    ) -> Section:
        """Write complete results section with all subsections.

        Args:
            prisma_flow: PRISMA flow data
            included_papers: List of included papers
            meta_analysis_result: Meta-analysis results (if available)
            narrative_synthesis_result: Narrative synthesis results (if meta-analysis not feasible)
            outcome_name: Name of primary outcome
            extraction_summary: Summary of extracted data
            screening_decisions: List of screening decisions with exclusion reasons

        Returns:
            Complete results section with PRISMA-compliant narrative description
        """
        # Create main results section
        results_section = Section(title="Results", content="")

        # 1. Study Selection (with detailed exclusion reasons)
        selection_result = await self.write_study_selection(
            prisma_flow,
            prisma_flow.records_identified_total,
            screening_decisions=screening_decisions,
        )
        results_section.add_subsection(selection_result.section)

        # 2. Study Characteristics
        characteristics_result = await self.write_study_characteristics(
            included_papers, extraction_summary
        )
        results_section.add_subsection(characteristics_result.section)

        # 3. Synthesis of Results
        # Prefer meta-analysis if available, otherwise use narrative synthesis
        if meta_analysis_result:
            synthesis_result = await self.write_synthesis_of_results(
                meta_analysis_result, outcome_name
            )
            results_section.add_subsection(synthesis_result.section)
        elif narrative_synthesis_result:
            synthesis_result = await self.write_narrative_synthesis_results(
                narrative_synthesis_result
            )
            results_section.add_subsection(synthesis_result.section)

        return results_section

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate API cost.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens

        Returns:
            Estimated cost in USD
        """
        # GPT-4o pricing: $2.50/1M input, $10/1M output
        input_cost = (prompt_tokens / 1_000_000) * 2.50
        output_cost = (completion_tokens / 1_000_000) * 10.00
        return input_cost + output_cost
