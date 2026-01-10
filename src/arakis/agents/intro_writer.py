"""Introduction section writer agent.

LLM-powered agent that writes the introduction section of a systematic review.
"""

import json
import time
from typing import Any, Optional, Union

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.models.writing import Section, WritingResult
from arakis.rag import Retriever
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class IntroductionWriterAgent:
    """LLM agent that writes introduction sections for systematic reviews."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.6, max_tokens: int = 4000):
        """Initialize the introduction writer agent.

        Args:
            model: OpenAI model to use
            temperature: Sampling temperature (higher = more creative)
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
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Union[dict[str, Any], str] = "auto",
        temperature: Optional[float] = None,
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
        """Get system prompt for introduction writer."""
        return """You are an expert scientific writer specializing in systematic review introductions. Your task is to write clear, compelling, and well-structured introductions that establish context and justify the review.

**Writing Guidelines:**

1. **Clarity**: Use clear, accessible language appropriate for medical/scientific journals
2. **Structure**: Funnel approach - broad context → specific problem → review objectives
3. **Citations**: Reference relevant literature (provided in context) using [Paper ID] format
4. **Tense**: Present tense for established facts, past tense for previous research
5. **Objectivity**: Be objective but compelling; establish the importance of the topic
6. **Flow**: Smooth transitions between paragraphs

**Introduction Structure:**

1. **Background** (2-3 paragraphs):
   - Start with broad context (disease burden, clinical significance)
   - Narrow to specific problem or intervention
   - Mention key previous findings (cite relevant papers)

2. **Rationale** (1-2 paragraphs):
   - Identify gaps or controversies in existing literature
   - Explain why a systematic review is needed
   - Justify the importance of answering the research question

3. **Objectives** (1 paragraph):
   - State clear, specific objectives of the review
   - Mention population, intervention, comparator, outcomes if applicable
   - Keep focused and concise

**Key Points:**
- Total length: 400-600 words
- Use active voice where possible
- Avoid over-citing (2-3 key papers per claim)
- Don't describe methods (that's in Methods section)
- Don't present results (that's in Results section)

**Avoid:**
- Speculation beyond what literature supports
- Excessive jargon or abbreviations
- Starting sentences with "This review..."
- Describing what the review "will do" (use present tense for objectives)"""

    async def write_background(
        self,
        topic: str,
        literature_context: Optional[list[Paper]] = None,
        retriever: Optional[Retriever] = None,
    ) -> WritingResult:
        """Write the background subsection.

        Args:
            topic: Main topic or research question
            literature_context: Relevant papers for context (optional)
            retriever: RAG retriever for fetching relevant literature (optional)

        Returns:
            WritingResult with generated background
        """
        start_time = time.time()

        # Retrieve relevant literature if retriever provided
        relevant_papers = []
        if retriever:
            results = await retriever.retrieve_simple(topic, top_k=10, diversity=True)
            paper_ids = list(dict.fromkeys([r.chunk.paper_id for r in results]))
            # Get paper details from chunks
            for paper_id in paper_ids[:5]:  # Limit to top 5 papers
                chunk = results[0].chunk  # Use first result as example
                relevant_papers.append({
                    "id": paper_id,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                })
        elif literature_context:
            relevant_papers = [
                {
                    "id": p.best_identifier,
                    "title": p.title,
                    "abstract": p.abstract[:200] + "..." if p.abstract and len(p.abstract) > 200 else p.abstract,
                    "year": p.year,
                }
                for p in literature_context[:5]
            ]

        context = {
            "topic": topic,
            "relevant_literature": relevant_papers,
        }

        prompt = f"""Write the "Background" subsection for a systematic review introduction.

**Topic:** {topic}

**Relevant Literature:**
{json.dumps(relevant_papers, indent=2) if relevant_papers else "No literature context provided."}

**Requirements:**
- Start broad (disease burden, clinical importance)
- Narrow to the specific topic
- Cite relevant papers using [Paper ID] format
- Length: 200-250 words
- 2-3 paragraphs
- Present tense for established facts

Write only the background text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Background", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_rationale(
        self,
        research_question: str,
        existing_reviews: Optional[list[Paper]] = None,
        retriever: Optional[Retriever] = None,
    ) -> WritingResult:
        """Write the rationale subsection.

        Args:
            research_question: The research question for the review
            existing_reviews: Previous systematic reviews on topic (optional)
            retriever: RAG retriever for fetching context (optional)

        Returns:
            WritingResult with generated rationale
        """
        start_time = time.time()

        # Retrieve relevant reviews if retriever provided
        review_context = []
        if retriever:
            query = f"systematic review meta-analysis {research_question}"
            results = await retriever.retrieve_simple(query, top_k=5, diversity=True)
            for result in results:
                review_context.append({
                    "id": result.chunk.paper_id,
                    "text": result.chunk.text,
                    "score": result.score,
                })
        elif existing_reviews:
            review_context = [
                {
                    "id": r.best_identifier,
                    "title": r.title,
                    "year": r.year,
                }
                for r in existing_reviews[:3]
            ]

        prompt = f"""Write the "Rationale" subsection for a systematic review introduction.

**Research Question:** {research_question}

**Existing Reviews:**
{json.dumps(review_context, indent=2) if review_context else "No previous reviews identified."}

**Requirements:**
- Identify gaps in existing literature
- Explain why a new/updated review is needed
- Justify the importance of answering this question
- Length: 100-150 words
- 1-2 paragraphs
- Be compelling but objective

Write only the rationale text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Rationale", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_objectives(
        self,
        research_question: str,
        inclusion_criteria: Optional[list[str]] = None,
        primary_outcome: Optional[str] = None,
    ) -> WritingResult:
        """Write the objectives subsection.

        Args:
            research_question: The research question
            inclusion_criteria: Study inclusion criteria (optional)
            primary_outcome: Primary outcome of interest (optional)

        Returns:
            WritingResult with generated objectives
        """
        start_time = time.time()

        context = {
            "research_question": research_question,
            "inclusion_criteria": inclusion_criteria or [],
            "primary_outcome": primary_outcome,
        }

        prompt = f"""Write the "Objectives" subsection for a systematic review introduction.

**Research Question:** {research_question}

**Context:**
{json.dumps(context, indent=2)}

**Requirements:**
- State clear, specific objectives
- Mention PICO elements if applicable (population, intervention, comparator, outcomes)
- Use present tense
- Length: 80-120 words
- 1 paragraph
- Be precise and focused

**Example opening:** "This systematic review aims to..."

Write only the objectives text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        elapsed_ms = int((time.time() - start_time) * 1000)
        tokens_used = response.usage.total_tokens if response.usage else 0
        cost = self._estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens)

        section = Section(title="Objectives", content=content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=tokens_used,
            cost_usd=cost,
            success=True,
        )

    async def write_complete_introduction(
        self,
        research_question: str,
        inclusion_criteria: Optional[list[str]] = None,
        primary_outcome: Optional[str] = None,
        literature_context: Optional[list[Paper]] = None,
        retriever: Optional[Retriever] = None,
    ) -> Section:
        """Write complete introduction section with all subsections.

        Args:
            research_question: The research question for the review
            inclusion_criteria: Study inclusion criteria (optional)
            primary_outcome: Primary outcome of interest (optional)
            literature_context: Relevant papers for context (optional)
            retriever: RAG retriever for fetching literature (optional)

        Returns:
            Complete introduction section
        """
        # Create main introduction section
        intro_section = Section(title="Introduction", content="")

        # 1. Background
        background_result = await self.write_background(
            research_question, literature_context, retriever
        )
        intro_section.add_subsection(background_result.section)

        # 2. Rationale
        rationale_result = await self.write_rationale(
            research_question, literature_context, retriever
        )
        intro_section.add_subsection(rationale_result.section)

        # 3. Objectives
        objectives_result = await self.write_objectives(
            research_question, inclusion_criteria, primary_outcome
        )
        intro_section.add_subsection(objectives_result.section)

        return intro_section

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
