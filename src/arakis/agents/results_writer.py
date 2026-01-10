"""Results section writer agent.

LLM-powered agent that writes the results section of a systematic review.
"""

import json
import time
from typing import Any

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.analysis import MetaAnalysisResult
from arakis.models.extraction import ExtractionResult
from arakis.models.paper import Paper
from arakis.models.screening import ScreeningDecision, ScreeningStatus
from arakis.models.visualization import PRISMAFlow, Figure, Table
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

    @retry_with_exponential_backoff(max_retries=8, initial_delay=2.0, max_delay=90.0, use_rate_limiter=True)
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
    ) -> WritingResult:
        """Write the study selection subsection.

        Args:
            prisma_flow: PRISMA flow data
            total_papers_searched: Total records from database searches
            screening_summary: Summary of screening results (optional)

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Prepare context
        context = {
            "total_identified": prisma_flow.records_identified_total,
            "duplicates_removed": prisma_flow.records_removed_duplicates,
            "records_screened": prisma_flow.records_screened,
            "records_excluded": prisma_flow.records_excluded,
            "reports_assessed": prisma_flow.reports_assessed,
            "studies_included": prisma_flow.studies_included,
            "databases": prisma_flow.records_identified_databases,
        }

        if screening_summary:
            context["screening_details"] = screening_summary

        prompt = f"""Write the "Study Selection" subsection for a systematic review results section.

**Data:**
{json.dumps(context, indent=2)}

**Requirements:**
- Start with database search results
- Mention duplicate removal
- Describe screening process (title/abstract, then full-text)
- Report final number of included studies
- Reference "Figure 1" (PRISMA flow diagram) at the end
- Length: 150-200 words
- Use past tense for methods, numbers for results

**Example opening:** "The literature search identified X records from Y databases..."

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

    async def write_complete_results_section(
        self,
        prisma_flow: PRISMAFlow,
        included_papers: list[Paper],
        meta_analysis_result: MetaAnalysisResult | None = None,
        outcome_name: str = "primary outcome",
        extraction_summary: dict[str, Any] | None = None,
    ) -> Section:
        """Write complete results section with all subsections.

        Args:
            prisma_flow: PRISMA flow data
            included_papers: List of included papers
            meta_analysis_result: Meta-analysis results (if available)
            outcome_name: Name of primary outcome
            extraction_summary: Summary of extracted data

        Returns:
            Complete results section
        """
        # Create main results section
        results_section = Section(title="Results", content="")

        # 1. Study Selection
        selection_result = await self.write_study_selection(prisma_flow, prisma_flow.records_identified_total)
        results_section.add_subsection(selection_result.section)

        # 2. Study Characteristics
        characteristics_result = await self.write_study_characteristics(included_papers, extraction_summary)
        results_section.add_subsection(characteristics_result.section)

        # 3. Synthesis of Results (if meta-analysis available)
        if meta_analysis_result:
            synthesis_result = await self.write_synthesis_of_results(meta_analysis_result, outcome_name)
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
