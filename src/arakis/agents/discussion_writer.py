"""Discussion section writer agent.

LLM-powered agent that writes the discussion section of a systematic review.

Uses o3/o3-pro extended thinking models for high-quality reasoning.
Supports cost mode configuration.
"""

import json
import time
from typing import Any, Optional, Union

from openai import AsyncOpenAI

from arakis.agents.models import REASONING_MODEL_PRO, get_model_pricing
from arakis.config import ModeConfig, get_default_mode_config, get_settings
from arakis.models.analysis import MetaAnalysisResult
from arakis.models.paper import Paper
from arakis.models.writing import Section, WritingResult
from arakis.rag import Retriever
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class DiscussionWriterAgent:
    """LLM agent that writes discussion sections for systematic reviews.

    Uses OpenAI's extended thinking models (o3/o3-pro) for high-quality output.
    Supports cost mode configuration.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.6,
        max_tokens: int = 4000,
        use_extended_thinking: bool = True,
        mode_config: ModeConfig | None = None,
    ):
        """Initialize the discussion writer agent.

        Args:
            model: OpenAI model to use (overrides mode_config if provided)
            temperature: Sampling temperature (ignored for o-series models)
            max_tokens: Maximum tokens in response
            use_extended_thinking: Use o3-pro for more thorough reasoning
            mode_config: Cost mode configuration. If None, uses default (BALANCED).
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Use mode config if no explicit model provided
        self.mode_config = mode_config or get_default_mode_config()

        # Select model: explicit > mode_config > default
        if model:
            self.model = model
        elif use_extended_thinking and self.mode_config.max_reasoning_effort:
            self.model = REASONING_MODEL_PRO
        else:
            self.model = self.mode_config.writing_model

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rate_limiter = get_openai_rate_limiter()

    @retry_with_exponential_backoff(
        max_retries=8, initial_delay=2.0, max_delay=90.0, use_rate_limiter=True
    )
    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Union[dict[str, Any], str] = "auto",
        temperature: Optional[float] = None,
    ):
        """Call OpenAI API with retry logic.

        Args:
            messages: Chat messages
            tools: Tool definitions (optional)
            tool_choice: Tool choice strategy
            temperature: Override default temperature (ignored for o-series)

        Returns:
            OpenAI completion response
        """
        await self.rate_limiter.wait()

        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # o-series models use max_completion_tokens and don't support temperature
        if self.model.startswith("o"):
            kwargs["max_completion_tokens"] = self.max_tokens
        else:
            kwargs["max_tokens"] = self.max_tokens
            kwargs["temperature"] = temperature if temperature is not None else self.temperature

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return await self.client.chat.completions.create(**kwargs)

    def _get_system_prompt(self) -> str:
        """Get system prompt for discussion writer."""
        return """You are an expert scientific writer specializing in systematic review discussions. Your task is to interpret findings, compare with existing literature, acknowledge limitations, and discuss implications.

**Writing Guidelines:**

1. **Interpretation**: Move beyond describing results to interpreting their meaning
2. **Comparison**: Place findings in context of existing literature
3. **Balance**: Present both strengths and limitations objectively
4. **Implications**: Discuss practical and research implications
5. **Tense**: Past tense for this review's findings, present tense for established knowledge
6. **Citations**: Reference relevant literature using [Paper ID] format

**Discussion Structure:**

1. **Summary of Main Findings** (1-2 paragraphs):
   - Briefly restate primary findings without repeating Results
   - Interpret the meaning and significance of findings
   - Mention unexpected findings if any

2. **Comparison with Existing Literature** (2-3 paragraphs):
   - Compare findings with previous reviews and studies
   - Explain agreements and disagreements
   - Discuss why differences might exist (methods, populations, etc.)
   - Cite relevant papers from context

3. **Limitations** (1-2 paragraphs):
   - Acknowledge methodological limitations honestly
   - Discuss heterogeneity, risk of bias, publication bias
   - Mention limitations of included studies
   - Don't be defensive - be objective

4. **Implications** (1-2 paragraphs):
   - **Clinical/practical implications**: What do findings mean for practice?
   - **Research implications**: What future research is needed?
   - Be specific but avoid over-reaching conclusions

**Key Points:**
- Total length: 600-800 words
- Be objective in interpretation
- Acknowledge uncertainty appropriately
- Avoid claiming causation unless justified
- Don't introduce new results
- Use active voice where appropriate

**Avoid:**
- Simply restating results
- Speculation beyond data
- Overconfident claims
- Ignoring contradictory evidence
- Defensive tone about limitations"""

    async def write_key_findings(
        self,
        meta_analysis_result: MetaAnalysisResult,
        outcome_name: str,
        user_interpretation: Optional[str] = None,
    ) -> WritingResult:
        """Write the summary of key findings subsection.

        Args:
            meta_analysis_result: Meta-analysis results to summarize
            outcome_name: Name of the outcome
            user_interpretation: Optional user-provided interpretation

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        context = {
            "outcome": outcome_name,
            "pooled_effect": round(meta_analysis_result.pooled_effect, 3),
            "ci_lower": round(meta_analysis_result.confidence_interval.lower, 3),
            "ci_upper": round(meta_analysis_result.confidence_interval.upper, 3),
            "p_value": meta_analysis_result.p_value,
            "is_significant": meta_analysis_result.is_significant,
            "i_squared": round(meta_analysis_result.heterogeneity.i_squared, 1),
            "studies_included": meta_analysis_result.studies_included,
            "user_interpretation": user_interpretation,
        }

        prompt = f"""Write the "Summary of Main Findings" subsection for a systematic review discussion.

**Meta-Analysis Results:**
{json.dumps(context, indent=2)}

**Requirements:**
- Briefly summarize the main finding (don't repeat Results verbatim)
- Interpret what the finding means clinically/practically
- Address the significance and magnitude of the effect
- Mention heterogeneity if substantial
- Length: 150-200 words
- 1-2 paragraphs
- Use past tense for this review's findings

{f"**User's Interpretation Notes:** {user_interpretation}" if user_interpretation else ""}

Write only the summary text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Summary of Main Findings", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_comparison_to_literature(
        self,
        meta_analysis_result: MetaAnalysisResult,
        outcome_name: str,
        retriever: Optional[Retriever] = None,
        literature_context: Optional[list[Paper]] = None,
        user_notes: Optional[str] = None,
    ) -> WritingResult:
        """Write the comparison with existing literature subsection.

        Args:
            meta_analysis_result: Meta-analysis results
            outcome_name: Name of the outcome
            retriever: RAG retriever for fetching similar studies (optional)
            literature_context: Relevant comparison papers (optional)
            user_notes: Optional user notes on comparisons

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Retrieve similar studies if retriever provided
        comparison_papers = []
        if retriever:
            query = f"systematic review meta-analysis {outcome_name}"
            results = await retriever.retrieve_simple(query, top_k=8, diversity=True)
            for result in results[:5]:
                comparison_papers.append(
                    {
                        "id": result.chunk.paper_id,
                        "text": result.chunk.text,
                        "score": round(result.score, 3),
                    }
                )
        elif literature_context:
            comparison_papers = [
                {
                    "id": p.best_identifier,
                    "title": p.title,
                    "year": p.year,
                    "abstract": p.abstract[:200] + "..."
                    if p.abstract and len(p.abstract) > 200
                    else p.abstract,
                }
                for p in literature_context[:5]
            ]

        context = {
            "our_finding": {
                "outcome": outcome_name,
                "effect": round(meta_analysis_result.pooled_effect, 3),
                "significant": meta_analysis_result.is_significant,
            },
            "comparison_papers": comparison_papers,
            "user_notes": user_notes,
        }

        prompt = f"""Write the "Comparison with Existing Literature" subsection for a systematic review discussion.

**Our Findings:**
{json.dumps(context["our_finding"], indent=2)}

**Relevant Previous Studies:**
{json.dumps(comparison_papers, indent=2) if comparison_papers else "No comparison studies provided."}

{f"**User Notes:** {user_notes}" if user_notes else ""}

**Requirements:**
- Compare our findings with previous reviews/studies
- Explain agreements and disagreements
- Discuss potential reasons for differences (methods, populations, etc.)
- Cite papers using [Paper ID] format
- Length: 250-300 words
- 2-3 paragraphs
- Be balanced and objective

Write only the comparison text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Comparison with Existing Literature", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_limitations(
        self,
        meta_analysis_result: MetaAnalysisResult,
        study_limitations: Optional[list[str]] = None,
        user_notes: Optional[str] = None,
    ) -> WritingResult:
        """Write the limitations subsection.

        Args:
            meta_analysis_result: Meta-analysis results
            study_limitations: Known limitations of included studies (optional)
            user_notes: Optional user notes on limitations

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        context = {
            "heterogeneity": {
                "i_squared": round(meta_analysis_result.heterogeneity.i_squared, 1),
                "has_high_heterogeneity": meta_analysis_result.heterogeneity.i_squared > 50,
            },
            "n_studies": meta_analysis_result.studies_included,
            "study_limitations": study_limitations or [],
            "user_notes": user_notes,
        }

        prompt = f"""Write the "Limitations" subsection for a systematic review discussion.

**Review Context:**
{json.dumps(context, indent=2)}

{f"**User Notes:** {user_notes}" if user_notes else ""}

**Requirements:**
- Acknowledge methodological limitations honestly
- Discuss heterogeneity if substantial (I² > 50%)
- Mention limitations of included studies
- Discuss potential biases (publication bias, language bias, etc.)
- Be objective, not defensive
- Length: 150-200 words
- 1-2 paragraphs

**Common limitations to consider:**
- Small number of studies
- High heterogeneity
- Risk of bias in included studies
- Limited geographic diversity
- Publication bias concerns
- Missing data or outcomes

Write only the limitations text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Limitations", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_implications(
        self,
        meta_analysis_result: MetaAnalysisResult,
        outcome_name: str,
        user_implications: Optional[str] = None,
    ) -> WritingResult:
        """Write the implications subsection.

        Args:
            meta_analysis_result: Meta-analysis results
            outcome_name: Name of the outcome
            user_implications: Optional user notes on implications

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        context = {
            "finding": {
                "outcome": outcome_name,
                "significant": meta_analysis_result.is_significant,
                "effect_size": round(meta_analysis_result.pooled_effect, 3),
            },
            "user_implications": user_implications,
        }

        prompt = f"""Write the "Implications" subsection for a systematic review discussion.

**Findings:**
{json.dumps(context["finding"], indent=2)}

{f"**User's Implications Notes:** {user_implications}" if user_implications else ""}

**Requirements:**
- Discuss practical/clinical implications (what does this mean for practice?)
- Discuss research implications (what future research is needed?)
- Be specific but avoid overconfident claims
- Consider both positive and negative findings
- Length: 150-200 words
- 1-2 paragraphs

**Structure:**
- First paragraph: Clinical/practical implications
- Second paragraph: Research implications

Write only the implications text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Implications", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_complete_discussion(
        self,
        meta_analysis_result: MetaAnalysisResult,
        outcome_name: str,
        retriever: Optional[Retriever] = None,
        literature_context: Optional[list[Paper]] = None,
        study_limitations: Optional[list[str]] = None,
        user_interpretation: Optional[str] = None,
        user_comparison_notes: Optional[str] = None,
        user_limitation_notes: Optional[str] = None,
        user_implications: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Section:
        """Write complete discussion section with all subsections.

        Args:
            meta_analysis_result: Meta-analysis results
            outcome_name: Name of the outcome
            retriever: RAG retriever for literature comparison (optional)
            literature_context: Relevant comparison papers (optional)
            study_limitations: Known study limitations (optional)
            user_interpretation: User notes for interpretation (optional)
            user_comparison_notes: User notes for comparison (optional)
            user_limitation_notes: User notes for limitations (optional)
            user_implications: User notes for implications (optional)
            progress_callback: Optional callback(subsection, word_count, thought_process)
                for tracking writing progress

        Returns:
            Complete discussion section
        """
        import asyncio
        import logging
        logger = logging.getLogger(__name__)

        # Create main discussion section
        discussion_section = Section(title="Discussion", content="")
        total_word_count = 0

        async def emit_progress(subsection: str, word_count: int, thought: Optional[str]) -> None:
            if progress_callback:
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(subsection, word_count, thought)
                    else:
                        progress_callback(subsection, word_count, thought)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        # 1. Summary of Main Findings
        await emit_progress("key_findings", 0, "Summarizing main findings from meta-analysis...")
        findings_result = await self.write_key_findings(
            meta_analysis_result, outcome_name, user_interpretation
        )
        discussion_section.add_subsection(findings_result.section)
        total_word_count += findings_result.section.total_word_count
        await emit_progress("key_findings", total_word_count, None)

        # 2. Comparison with Existing Literature
        await emit_progress("comparison_to_literature", total_word_count, "Comparing with existing literature...")
        comparison_result = await self.write_comparison_to_literature(
            meta_analysis_result, outcome_name, retriever, literature_context, user_comparison_notes
        )
        discussion_section.add_subsection(comparison_result.section)
        total_word_count += comparison_result.section.total_word_count
        await emit_progress("comparison_to_literature", total_word_count, None)

        # 3. Limitations
        await emit_progress("limitations", total_word_count, "Analyzing study limitations...")
        limitations_result = await self.write_limitations(
            meta_analysis_result, study_limitations, user_limitation_notes
        )
        discussion_section.add_subsection(limitations_result.section)
        total_word_count += limitations_result.section.total_word_count
        await emit_progress("limitations", total_word_count, None)

        # 4. Implications
        await emit_progress("implications", total_word_count, "Discussing clinical and research implications...")
        implications_result = await self.write_implications(
            meta_analysis_result, outcome_name, user_implications
        )
        discussion_section.add_subsection(implications_result.section)
        total_word_count += implications_result.section.total_word_count
        await emit_progress("implications", total_word_count, None)

        return discussion_section

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate API cost.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = get_model_pricing(self.model)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
