"""Methods section writer agent.

LLM-powered agent that writes the methods section of a systematic review.
Follows PRISMA 2020 guidelines for reporting.

Uses o3/o3-pro extended thinking models for high-quality reasoning.
Supports cost mode configuration.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from openai import AsyncOpenAI

from arakis.agents.models import REASONING_MODEL_PRO
from arakis.config import ModeConfig, get_default_mode_config, get_settings
from arakis.models.writing import Section, WritingResult
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


@dataclass
class MethodsContext:
    """Context data for methods section generation."""

    research_question: str
    inclusion_criteria: str
    exclusion_criteria: str
    databases: list[str]
    search_queries: dict[str, str] | None = None  # database -> query
    search_date: str | None = None
    screening_method: str = "dual-review"
    extraction_schema: str | None = None  # e.g., "RCT", "cohort"
    extraction_fields: list[str] | None = None
    analysis_methods: list[str] | None = None
    protocol_registration: str | None = None  # e.g., PROSPERO ID


class MethodsWriterAgent:
    """LLM agent that writes methods section for systematic reviews.

    Uses OpenAI's extended thinking models (o3/o3-pro) for high-quality output.
    Supports cost mode configuration.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 4000,
        use_extended_thinking: bool = True,
        mode_config: ModeConfig | None = None,
    ):
        """Initialize the methods writer agent.

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
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str = "auto",
        temperature: float | None = None,
    ):
        """Call OpenAI API with retry logic."""
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
        """Get system prompt for methods writer."""
        return """You are an expert scientific writer specializing in systematic reviews and meta-analyses. Your task is to write clear, accurate, and well-structured methods sections following PRISMA 2020 guidelines.

**Writing Guidelines:**

1. **Precision**: Be specific about every methodological choice made
2. **Reproducibility**: Write methods clearly enough that another researcher could replicate the review
3. **Transparency**: Report all decisions, including deviations from protocol
4. **Tense**: Use past tense throughout (methods describe what WAS done)
5. **Voice**: Prefer active voice where possible

**PRISMA 2020 Methods Structure:**

1. **Eligibility Criteria**: Study designs, participants, interventions, comparators, outcomes
2. **Information Sources**: Databases, registers, websites, organizations contacted
3. **Search Strategy**: Full search strategy for at least one database
4. **Selection Process**: How studies were selected, number of reviewers
5. **Data Collection Process**: Methods for extracting data, number of reviewers
6. **Data Items**: List of variables extracted
7. **Study Risk of Bias Assessment**: Tools used, how assessments were done
8. **Effect Measures**: Effect measures used (RR, OR, MD, SMD)
9. **Synthesis Methods**: How data were combined, handling of heterogeneity

**Key Points:**
- Report databases searched with date ranges
- State inclusion/exclusion criteria clearly
- Describe screening process (title/abstract vs full-text)
- Mention use of reference management software if applicable
- Describe data extraction forms/tools
- Report statistical methods for meta-analysis
- Mention software used for analysis

**Avoid:**
- Vague statements like "relevant databases were searched"
- Incomplete information about search strategy
- Missing details about reviewer disagreement resolution"""

    async def write_eligibility_criteria(
        self,
        inclusion_criteria: str,
        exclusion_criteria: str,
        study_design: str | None = None,
    ) -> WritingResult:
        """Write the eligibility criteria subsection.

        Args:
            inclusion_criteria: Inclusion criteria from user
            exclusion_criteria: Exclusion criteria from user
            study_design: Target study design (optional)

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        context = {
            "inclusion": inclusion_criteria,
            "exclusion": exclusion_criteria,
            "study_design": study_design,
        }

        prompt = f"""Write the "Eligibility Criteria" subsection for a systematic review methods section.

**User-Provided Criteria:**
{json.dumps(context, indent=2)}

**Requirements:**
- Structure using PICOS framework if applicable (Population, Intervention, Comparator, Outcomes, Study design)
- List inclusion criteria clearly
- List exclusion criteria clearly
- Be specific and unambiguous
- Length: 150-200 words

**Example structure:**
"Studies were eligible for inclusion if they met the following criteria: [criteria].
Studies were excluded if: [exclusion criteria]."

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

        section = Section(title="Eligibility Criteria", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_information_sources(
        self,
        databases: list[str],
        search_date: str | None = None,
    ) -> WritingResult:
        """Write the information sources subsection.

        Args:
            databases: List of databases searched
            search_date: Date of search

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        # Map database IDs to full names
        db_names = {
            "pubmed": "PubMed/MEDLINE",
            "openalex": "OpenAlex",
            "semantic_scholar": "Semantic Scholar",
            "embase": "Embase",
            "cochrane": "Cochrane Library",
            "google_scholar": "Google Scholar",
        }

        full_names = [db_names.get(db, db) for db in databases]

        context = {
            "databases": full_names,
            "search_date": search_date or "the date of this review",
            "num_databases": len(databases),
        }

        prompt = f"""Write the "Information Sources" subsection for a systematic review methods section.

**Search Information:**
{json.dumps(context, indent=2)}

**Requirements:**
- List all databases searched
- Include date of search
- Mention any other sources (reference lists, grey literature) if applicable
- Length: 80-120 words

**Example:** "We searched the following electronic databases from inception to [date]: PubMed/MEDLINE, Embase, and the Cochrane Library. Additionally, we screened reference lists of included studies and relevant systematic reviews."

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

        section = Section(title="Information Sources", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_search_strategy(
        self,
        research_question: str,
        search_queries: dict[str, str] | None = None,
    ) -> WritingResult:
        """Write the search strategy subsection.

        Args:
            research_question: The research question
            search_queries: Database-specific queries (optional)

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        context = {
            "research_question": research_question,
            "queries": search_queries or {},
        }

        prompt = f"""Write the "Search Strategy" subsection for a systematic review methods section.

**Search Information:**
{json.dumps(context, indent=2)}

**Requirements:**
- Describe the search strategy development process
- Mention use of controlled vocabulary (MeSH terms) if applicable
- Note that full search strategies are available in supplementary materials
- If specific queries provided, summarize key terms used
- Length: 100-150 words

**Example:** "Search strategies were developed in consultation with a medical librarian and adapted for each database. We combined terms for [concept 1] AND [concept 2] using a combination of MeSH terms and free-text keywords. The full search strategy for PubMed is provided in Supplementary Material S1."

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

        section = Section(title="Search Strategy", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_selection_process(
        self,
        screening_method: str = "dual-review",
    ) -> WritingResult:
        """Write the selection process subsection.

        Args:
            screening_method: Screening methodology used

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        is_dual_review = "dual" in screening_method.lower()

        context = {
            "method": screening_method,
            "dual_review": is_dual_review,
        }

        prompt = f"""Write the "Selection Process" subsection for a systematic review methods section.

**Screening Information:**
{json.dumps(context, indent=2)}

**Requirements:**
- Describe two-stage screening (title/abstract, then full-text)
- Mention number of reviewers and independence
- Describe how disagreements were resolved
- Mention use of screening software if applicable
- Note: This review used AI-assisted screening with {"dual" if is_dual_review else "single"}-review methodology
- Length: 120-150 words

**Example:** "Two reviewers independently screened titles and abstracts using predefined inclusion criteria. Full texts of potentially eligible studies were retrieved and assessed independently by both reviewers. Disagreements were resolved through discussion or consultation with a third reviewer."

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

        section = Section(title="Selection Process", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_data_collection(
        self,
        extraction_schema: str | None = None,
        extraction_fields: list[str] | None = None,
    ) -> WritingResult:
        """Write the data collection process subsection.

        Args:
            extraction_schema: Type of extraction schema (e.g., "RCT", "cohort")
            extraction_fields: List of extracted variables

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        default_fields = [
            "study design",
            "sample size",
            "population characteristics",
            "intervention details",
            "outcome measures",
            "results",
        ]

        context = {
            "schema_type": extraction_schema or "systematic review",
            "fields": extraction_fields or default_fields,
        }

        prompt = f"""Write the "Data Collection Process" and "Data Items" subsections for a systematic review methods section.

**Extraction Information:**
{json.dumps(context, indent=2)}

**Requirements:**
- Describe data extraction process
- Mention use of standardized extraction forms
- Note: This review used AI-assisted extraction with triple-review methodology for quality assurance
- List key variables extracted
- Mention how missing data was handled
- Length: 150-180 words total (covering both subsections)

**Example:** "Data were extracted using a standardized form developed a priori. Two reviewers independently extracted data, with discrepancies resolved by consensus. The following data were extracted: [list]. Authors were contacted for missing data when necessary."

Write both subsections in sequence, clearly labeled."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Data Collection Process", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_synthesis_methods(
        self,
        analysis_methods: list[str] | None = None,
        has_meta_analysis: bool = True,
    ) -> WritingResult:
        """Write the synthesis methods subsection.

        Args:
            analysis_methods: List of statistical methods used
            has_meta_analysis: Whether meta-analysis was performed

        Returns:
            WritingResult with generated text
        """
        start_time = time.time()

        default_methods = [
            "random-effects meta-analysis (DerSimonian-Laird)",
            "I-squared for heterogeneity",
            "forest plots for visualization",
        ]

        context = {
            "methods": analysis_methods or default_methods,
            "meta_analysis": has_meta_analysis,
        }

        prompt = f"""Write the "Synthesis Methods" subsection for a systematic review methods section.

**Analysis Information:**
{json.dumps(context, indent=2)}

**Requirements:**
- Describe the overall approach to synthesis
- If meta-analysis performed: specify effect measure, model (random/fixed), heterogeneity assessment
- Mention software used (Python statistical libraries)
- Describe sensitivity analyses or subgroup analyses if applicable
- Mention publication bias assessment if meta-analysis performed
- Length: 150-200 words

**Example:** "We performed random-effects meta-analysis using the DerSimonian-Laird method. Heterogeneity was assessed using the I² statistic, with values >50% indicating substantial heterogeneity. Publication bias was assessed using funnel plots and Egger's test when ≥10 studies were available."

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

        section = Section(title="Synthesis Methods", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_complete_methods_section(
        self,
        context: MethodsContext,
        has_meta_analysis: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Section:
        """Write complete methods section with all subsections.

        Args:
            context: MethodsContext with all required information
            has_meta_analysis: Whether meta-analysis was performed
            progress_callback: Optional callback(subsection, word_count, thought_process)
                for tracking writing progress

        Returns:
            Complete methods section
        """
        import asyncio
        import logging
        logger = logging.getLogger(__name__)

        async def emit_progress(subsection: str, word_count: int, thought: Optional[str]) -> None:
            if progress_callback:
                try:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(subsection, word_count, thought)
                    else:
                        progress_callback(subsection, word_count, thought)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        # Create main methods section
        methods_section = Section(title="Methods", content="")
        total_word_count = 0

        # 1. Protocol registration (if available)
        if context.protocol_registration:
            protocol_text = (
                f"This systematic review was registered with PROSPERO "
                f"({context.protocol_registration}) and followed the PRISMA 2020 guidelines."
            )
            methods_section.content = protocol_text + "\n\n"
        else:
            methods_section.content = (
                "This systematic review was conducted following the PRISMA 2020 guidelines "
                "for reporting systematic reviews and meta-analyses.\n\n"
            )
        total_word_count = len(methods_section.content.split())

        # 2. Eligibility Criteria
        await emit_progress("eligibility_criteria", total_word_count, "Writing eligibility criteria...")
        eligibility_result = await self.write_eligibility_criteria(
            context.inclusion_criteria,
            context.exclusion_criteria,
            context.extraction_schema,
        )
        methods_section.add_subsection(eligibility_result.section)
        total_word_count += eligibility_result.section.total_word_count
        await emit_progress("eligibility_criteria", total_word_count, None)

        # 3. Information Sources
        await emit_progress("information_sources", total_word_count, "Documenting information sources...")
        sources_result = await self.write_information_sources(
            context.databases,
            context.search_date,
        )
        methods_section.add_subsection(sources_result.section)
        total_word_count += sources_result.section.total_word_count
        await emit_progress("information_sources", total_word_count, None)

        # 4. Search Strategy
        await emit_progress("search_strategy", total_word_count, "Writing search strategy...")
        strategy_result = await self.write_search_strategy(
            context.research_question,
            context.search_queries,
        )
        methods_section.add_subsection(strategy_result.section)
        total_word_count += strategy_result.section.total_word_count
        await emit_progress("search_strategy", total_word_count, None)

        # 5. Selection Process
        await emit_progress("selection_process", total_word_count, "Describing selection process...")
        selection_result = await self.write_selection_process(
            context.screening_method,
        )
        methods_section.add_subsection(selection_result.section)
        total_word_count += selection_result.section.total_word_count
        await emit_progress("selection_process", total_word_count, None)

        # 6. Data Collection
        await emit_progress("data_collection", total_word_count, "Documenting data collection process...")
        collection_result = await self.write_data_collection(
            context.extraction_schema,
            context.extraction_fields,
        )
        methods_section.add_subsection(collection_result.section)
        total_word_count += collection_result.section.total_word_count
        await emit_progress("data_collection", total_word_count, None)

        # 7. Synthesis Methods
        await emit_progress("synthesis_methods", total_word_count, "Writing synthesis methods...")
        synthesis_result = await self.write_synthesis_methods(
            context.analysis_methods,
            has_meta_analysis,
        )
        methods_section.add_subsection(synthesis_result.section)
        total_word_count += synthesis_result.section.total_word_count
        await emit_progress("synthesis_methods", total_word_count, None)

        return methods_section

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate API cost.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens

        Returns:
            Estimated cost in USD
        """
        # o1 pricing: $15/1M input, $60/1M output (extended thinking model)
        if self.model.startswith("o1"):
            input_cost = (prompt_tokens / 1_000_000) * 15.00
            output_cost = (completion_tokens / 1_000_000) * 60.00
        else:
            # GPT-4o pricing: $2.50/1M input, $10/1M output
            input_cost = (prompt_tokens / 1_000_000) * 2.50
            output_cost = (completion_tokens / 1_000_000) * 10.00
        return input_cost + output_cost
