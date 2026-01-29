"""Abstract writer agent.

LLM-powered agent that writes abstracts for systematic reviews.

Uses o3/o3-pro extended thinking models for high-quality reasoning.
"""

import json
import time
from typing import Any, Optional, Union

from openai import AsyncOpenAI

from arakis.agents.models import REASONING_MODEL, REASONING_MODEL_PRO
from arakis.config import get_settings
from arakis.models.writing import Manuscript, Section, WritingResult
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class AbstractWriterAgent:
    """LLM agent that writes abstracts for systematic reviews.

    Uses OpenAI's extended thinking models (o3/o3-pro) for high-quality output.
    """

    def __init__(
        self,
        model: str = REASONING_MODEL,
        temperature: float = 0.4,
        max_tokens: int = 1000,
        use_extended_thinking: bool = True,
    ):
        """Initialize the abstract writer agent.

        Args:
            model: OpenAI model to use (default: o3)
            temperature: Sampling temperature (ignored for o-series models)
            max_tokens: Maximum tokens in response
            use_extended_thinking: Use o3-pro for more thorough reasoning
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Select model based on extended thinking preference
        if use_extended_thinking:
            self.model = REASONING_MODEL_PRO
        else:
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

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for OpenAI API call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # o1 pricing: $15/1M input, $60/1M output (extended thinking model)
        if self.model.startswith("o1"):
            input_cost = (input_tokens / 1_000_000) * 15.00
            output_cost = (output_tokens / 1_000_000) * 60.00
        else:
            # GPT-4o pricing: $2.50/1M input, $10/1M output
            input_cost = (input_tokens / 1_000_000) * 2.50
            output_cost = (output_tokens / 1_000_000) * 10.00
        return input_cost + output_cost

    def _get_system_prompt(self, structured: bool = False) -> str:
        """Get system prompt for abstract writer.

        Args:
            structured: Whether to use structured (IMRAD) format

        Returns:
            System prompt string
        """
        if structured:
            return """You are an expert scientific writer specializing in systematic review abstracts. Your task is to write clear, concise abstracts in structured (IMRAD) format.

**Structured Abstract Format:**

**Background/Objective:** (1-2 sentences)
- Brief context and study objective
- State the research question clearly

**Methods:** (2-3 sentences)
- Databases searched and search strategy
- Inclusion/exclusion criteria
- Number of studies included
- Analysis methods (e.g., meta-analysis, random-effects model)

**Results:** (2-3 sentences)
- Number of participants/studies
- Primary outcome results with statistics (effect size, CI, p-value)
- Key secondary findings
- Heterogeneity assessment (I²)

**Conclusions:** (1-2 sentences)
- Main takeaway message
- Implications for practice or research

**Writing Guidelines:**
1. **Conciseness**: Target 250-300 words total
2. **Clarity**: Use clear, direct language
3. **Precision**: Include specific numbers and statistics
4. **Objectivity**: State findings without interpretation or speculation
5. **Tense**: Past tense for methods and results, present for conclusions
6. **Abbreviations**: Define on first use if commonly understood

**Avoid:**
- Vague statements like "studies were reviewed"
- Over-interpretation of findings
- Citations (abstracts typically don't cite)
- Excessive technical jargon
- Redundancy"""
        else:
            return """You are an expert scientific writer specializing in systematic review abstracts. Your task is to write clear, concise abstracts in unstructured (single paragraph) format.

**Unstructured Abstract Structure:**

Write a single, flowing paragraph that covers:
1. **Context & Objective** (1-2 sentences): Brief background and research question
2. **Methods** (2-3 sentences): Search strategy, inclusion criteria, number of studies, analysis approach
3. **Results** (2-3 sentences): Main findings with statistics (effect size, CI, p-value, I²)
4. **Conclusions** (1-2 sentences): Key takeaway and implications

**Writing Guidelines:**
1. **Conciseness**: Target 250-300 words
2. **Flow**: Smooth transitions between components
3. **Clarity**: Use clear, direct language
4. **Precision**: Include specific numbers and statistics
5. **Objectivity**: State findings without over-interpretation
6. **Tense**: Past tense for methods/results, present for conclusions

**Avoid:**
- Section labels or headings (it's a single paragraph)
- Vague statements like "various studies"
- Over-interpretation of findings
- Citations (abstracts typically don't cite)
- Excessive jargon"""

    def _get_extraction_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for extracting abstract components.

        Returns:
            List of tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "extract_objective",
                    "description": "Extract the research objective/question from the manuscript",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "objective": {
                                "type": "string",
                                "description": "Clear statement of the research objective (1-2 sentences)",
                            },
                            "background_context": {
                                "type": "string",
                                "description": "Brief background context (1 sentence)",
                            },
                        },
                        "required": ["objective"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_methods",
                    "description": "Extract key methodological details from the manuscript",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "databases": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Databases searched (e.g., PubMed, Embase)",
                            },
                            "search_period": {
                                "type": "string",
                                "description": "Time period searched (e.g., 'inception to January 2024')",
                            },
                            "inclusion_criteria": {
                                "type": "string",
                                "description": "Brief description of inclusion criteria",
                            },
                            "n_studies": {
                                "type": "integer",
                                "description": "Number of studies included in the review",
                            },
                            "analysis_method": {
                                "type": "string",
                                "description": "Statistical analysis approach (e.g., 'random-effects meta-analysis')",
                            },
                        },
                        "required": ["n_studies", "analysis_method"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_results",
                    "description": "Extract key results and statistics from the manuscript",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "total_participants": {
                                "type": "integer",
                                "description": "Total number of participants across all studies",
                            },
                            "primary_outcome": {
                                "type": "string",
                                "description": "Primary outcome measured",
                            },
                            "effect_size": {
                                "type": "number",
                                "description": "Pooled effect size or main result statistic",
                            },
                            "confidence_interval": {
                                "type": "string",
                                "description": "95% confidence interval (e.g., '0.28-0.56')",
                            },
                            "p_value": {
                                "type": "string",
                                "description": "P-value (e.g., 'p<0.001', 'p=0.04')",
                            },
                            "heterogeneity": {
                                "type": "string",
                                "description": "I² value indicating heterogeneity (e.g., 'I²=43%')",
                            },
                            "secondary_findings": {
                                "type": "string",
                                "description": "Brief summary of key secondary findings (optional)",
                            },
                        },
                        "required": ["primary_outcome", "effect_size"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_conclusions",
                    "description": "Extract main conclusions and implications from the manuscript",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "main_conclusion": {
                                "type": "string",
                                "description": "Primary conclusion of the review (1 sentence)",
                            },
                            "implications": {
                                "type": "string",
                                "description": "Key implications for practice or research (1 sentence, optional)",
                            },
                        },
                        "required": ["main_conclusion"],
                    },
                },
            },
        ]

    async def extract_components(
        self,
        manuscript: Manuscript,
    ) -> dict[str, Any]:
        """Extract key components from manuscript for abstract generation.

        Args:
            manuscript: Complete manuscript to extract from

        Returns:
            Dictionary with extracted components
        """
        # Prepare manuscript content for extraction
        content_parts = []

        if manuscript.introduction:
            content_parts.append(f"## Introduction\n{manuscript.introduction.content[:500]}")

        if manuscript.methods:
            content_parts.append(f"## Methods\n{manuscript.methods.content[:800]}")

        if manuscript.results:
            content_parts.append(f"## Results\n{manuscript.results.content[:1000]}")

        if manuscript.discussion:
            content_parts.append(f"## Discussion\n{manuscript.discussion.content[:500]}")

        manuscript_text = "\n\n".join(content_parts)

        extraction_prompt = f"""Extract key information from this systematic review manuscript for abstract generation.

**Manuscript Sections:**
{manuscript_text}

Use the provided tools to extract:
1. Objective and background context
2. Methods (databases, criteria, n studies, analysis)
3. Results (statistics, effect sizes, heterogeneity)
4. Conclusions and implications

Extract precise information from the text. For statistics, use exact values mentioned."""

        messages = [
            {
                "role": "system",
                "content": "You are a systematic review expert extracting key information for abstract writing.",
            },
            {"role": "user", "content": extraction_prompt},
        ]

        tools = self._get_extraction_tools()

        # Call OpenAI with tools
        response = await self._call_openai(
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        # Parse tool calls
        components = {}
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                if function_name == "extract_objective":
                    components["objective"] = arguments.get("objective", "")
                    components["background"] = arguments.get("background_context", "")
                elif function_name == "extract_methods":
                    components["methods"] = arguments
                elif function_name == "extract_results":
                    components["results"] = arguments
                elif function_name == "extract_conclusions":
                    components["conclusions"] = arguments

        return components

    async def write_abstract(
        self,
        manuscript: Manuscript,
        structured: bool = True,
        word_limit: int = 300,
    ) -> WritingResult:
        """Write an abstract from a complete manuscript.

        Args:
            manuscript: Complete manuscript to generate abstract from
            structured: Whether to use structured (IMRAD) format
            word_limit: Maximum word count (default 300)

        Returns:
            WritingResult with generated abstract
        """
        start_time = time.time()

        # Extract components first
        components = await self.extract_components(manuscript)

        # Compose abstract
        composition_prompt = f"""Write a {("structured (IMRAD)" if structured else "unstructured")} abstract for this systematic review.

**Extracted Information:**
{json.dumps(components, indent=2)}

**Requirements:**
- Target length: {word_limit} words (absolute maximum)
- Format: {"Structured with clear section labels (Background/Objective, Methods, Results, Conclusions)" if structured else "Single flowing paragraph"}
- Include specific statistics: effect sizes, confidence intervals, p-values, I²
- Past tense for methods/results, present tense for conclusions
- Clear, concise, objective

Write the complete abstract now."""

        messages = [
            {"role": "system", "content": self._get_system_prompt(structured=structured)},
            {"role": "user", "content": composition_prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(
            response.usage.prompt_tokens if response.usage else 0,
            response.usage.completion_tokens if response.usage else 0,
        )

        section = Section(title="Abstract", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_abstract_from_sections(
        self,
        title: str,
        introduction_text: Optional[str] = None,
        methods_text: Optional[str] = None,
        results_text: Optional[str] = None,
        discussion_text: Optional[str] = None,
        structured: bool = True,
        word_limit: int = 300,
    ) -> WritingResult:
        """Write abstract from individual section texts.

        Useful when you have section text but not a full Manuscript object.

        Args:
            title: Manuscript title
            introduction_text: Introduction section text
            methods_text: Methods section text
            results_text: Results section text
            discussion_text: Discussion section text
            structured: Whether to use structured (IMRAD) format
            word_limit: Maximum word count

        Returns:
            WritingResult with generated abstract
        """
        # Create a temporary manuscript object
        manuscript = Manuscript(title=title)

        if introduction_text:
            manuscript.introduction = Section(title="Introduction", content=introduction_text)
        if methods_text:
            manuscript.methods = Section(title="Methods", content=methods_text)
        if results_text:
            manuscript.results = Section(title="Results", content=results_text)
        if discussion_text:
            manuscript.discussion = Section(title="Discussion", content=discussion_text)

        return await self.write_abstract(manuscript, structured=structured, word_limit=word_limit)
