"""Introduction section writer agent.

LLM-powered agent that writes the introduction section of a systematic review.

This module uses the Perplexity API to fetch background literature for the
introduction, which is separate from the systematic review search results.
This ensures the introduction references general academic literature rather
than the specific papers being reviewed.
"""

import json
import time
from typing import Any, Optional, Union

from openai import AsyncOpenAI

from arakis.clients.perplexity import PerplexityClient
from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.models.writing import Section, WritingResult
from arakis.rag import Retriever
from arakis.references import CitationExtractor, ReferenceManager
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class IntroductionWriterAgent:
    """LLM agent that writes introduction sections for systematic reviews.

    This agent uses the Perplexity API (when configured) to fetch background
    literature for the introduction. This is intentionally separate from the
    systematic review search results to ensure proper separation between
    background context and reviewed papers.

    The agent tracks all citations made in the introduction and provides them
    for inclusion in the reference section.

    Example usage:
        agent = IntroductionWriterAgent()

        # Write complete introduction with Perplexity research
        intro, papers = await agent.write_complete_introduction(
            research_question="Effect of aspirin on cardiovascular mortality",
            use_perplexity=True
        )

        # Get papers for reference section
        for paper in papers:
            print(f"- {paper.title}")
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.6,
        max_tokens: int = 4000,
        perplexity_client: Optional[PerplexityClient] = None,
    ):
        """Initialize the introduction writer agent.

        Args:
            model: OpenAI model to use for writing
            temperature: Sampling temperature (higher = more creative)
            max_tokens: Maximum tokens in response
            perplexity_client: Optional pre-configured Perplexity client
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rate_limiter = get_openai_rate_limiter()

        # Initialize Perplexity client for literature research
        self.perplexity = perplexity_client or PerplexityClient()

        # Initialize reference management
        self.reference_manager = ReferenceManager()
        self._citation_extractor = CitationExtractor()

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
3. **Tense**: Present tense for established facts, past tense for previous research
4. **Objectivity**: Be objective but compelling; establish the importance of the topic
5. **Flow**: Smooth transitions between paragraphs

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

**CRITICAL CITATION FORMAT:**
- Use ONLY numeric citations: [1], [2], [3], etc.
- ONLY use citation numbers from the provided paper list
- Do NOT use DOIs, PMIDs, or any other citation format
- Do NOT invent citation numbers beyond what is provided
- If only papers [1], [2], [3] are provided, you may ONLY cite [1], [2], or [3]
- Do NOT cite [4], [5], etc. if they don't exist in the list
- If you need to make a claim but have no matching paper, state it WITHOUT a citation
- NEVER use citations from your training data

**Avoid:**
- Speculation beyond what literature supports
- Excessive jargon or abbreviations
- Starting sentences with "This review..."
- Describing what the review "will do" (use present tense for objectives)
- Using any citation format other than [1], [2], [3]"""

    async def write_background(
        self,
        topic: str,
        literature_context: Optional[list[Paper]] = None,
        retriever: Optional[Retriever] = None,
        use_perplexity: bool = True,
    ) -> WritingResult:
        """Write the background subsection.

        Args:
            topic: Main topic or research question
            literature_context: Relevant papers for context (optional, ignored if use_perplexity=True)
            retriever: RAG retriever (optional, ignored if use_perplexity=True)
            use_perplexity: Use Perplexity API for literature (default: True)

        Returns:
            WritingResult with generated background
        """
        start_time = time.time()

        papers: list[Paper] = []
        perplexity_summary = ""

        # Priority: Perplexity > RAG > provided literature
        if use_perplexity and self.perplexity.is_configured:
            # Use Perplexity for deep research
            try:
                summary, fetched_papers = await self.perplexity.get_literature_context(
                    topic, max_papers=5
                )
                perplexity_summary = summary
                papers = fetched_papers

                # Register papers with reference manager
                for paper in papers:
                    self.reference_manager.register_paper(paper)
            except Exception:
                # Fall back to other methods if Perplexity fails
                pass

        if not papers and literature_context:
            # Use provided papers
            papers = literature_context[:5]
            for p in papers:
                self.reference_manager.register_paper(p)

        # Format papers with numeric IDs for the prompt
        papers_formatted = self._format_papers_for_prompt(papers)
        max_citation = len(papers)
        valid_range = (
            f"[1] to [{max_citation}]" if max_citation > 0 else "none available"
        )

        prompt = f"""Write the "Background" subsection for a systematic review introduction.

**Topic:** {topic}

**Research Summary:**
{perplexity_summary if perplexity_summary else "No additional research summary available."}

**Available Papers to Cite (use ONLY these numeric citations):**
{papers_formatted}

**IMPORTANT CITATION RULES:**
- You may ONLY cite using numbers: {valid_range}
- Do NOT use any other citation format (no DOIs, no author names in brackets)
- Do NOT invent citations beyond [{max_citation}]
- If you cannot support a claim with the provided papers, state it without a citation

**Requirements:**
- Start broad (disease burden, clinical importance)
- Narrow to the specific topic
- Length: 200-250 words
- 2-3 paragraphs
- Present tense for established facts

Write only the background text, no headings."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        # Generate with validation, retry, and cleanup
        content, used_citations = await self._generate_with_validation(
            messages, papers, max_retries=1
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Create section and extract citations (now using paper IDs)
        section = Section(title="Background", content=content)
        section.citations = self._citation_extractor.extract_unique_paper_ids(content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=0,  # Can't track across retries easily
            cost_usd=0.0,
            success=True,
        )

    async def write_rationale(
        self,
        research_question: str,
        existing_reviews: Optional[list[Paper]] = None,
        retriever: Optional[Retriever] = None,
        use_perplexity: bool = True,
    ) -> WritingResult:
        """Write the rationale subsection.

        Args:
            research_question: The research question for the review
            existing_reviews: Previous systematic reviews on topic (optional)
            retriever: RAG retriever for fetching context (optional)
            use_perplexity: Use Perplexity API for literature (default: True)

        Returns:
            WritingResult with generated rationale
        """
        start_time = time.time()

        papers: list[Paper] = []
        perplexity_summary = ""

        # Priority: Perplexity > RAG > provided literature
        if use_perplexity and self.perplexity.is_configured:
            try:
                query = f"systematic review meta-analysis {research_question}"
                summary, fetched_papers = await self.perplexity.get_literature_context(
                    query, max_papers=3
                )
                perplexity_summary = summary
                papers = fetched_papers

                for paper in papers:
                    self.reference_manager.register_paper(paper)
            except Exception:
                pass

        if not papers and existing_reviews:
            papers = existing_reviews[:3]
            for r in papers:
                self.reference_manager.register_paper(r)

        # Format papers with numeric IDs for the prompt
        papers_formatted = self._format_papers_for_prompt(papers)
        max_citation = len(papers)
        valid_range = (
            f"[1] to [{max_citation}]" if max_citation > 0 else "none available"
        )

        prompt = f"""Write the "Rationale" subsection for a systematic review introduction.

**Research Question:** {research_question}

**Research Summary:**
{perplexity_summary if perplexity_summary else "No additional research summary available."}

**Available Papers to Cite (use ONLY these numeric citations):**
{papers_formatted}

**IMPORTANT CITATION RULES:**
- You may ONLY cite using numbers: {valid_range}
- Do NOT use any other citation format (no DOIs, no author names in brackets)
- Do NOT invent citations beyond [{max_citation}]
- If you cannot support a claim with the provided papers, state it without a citation

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

        # Generate with validation, retry, and cleanup
        content, used_citations = await self._generate_with_validation(
            messages, papers, max_retries=1
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Create section and extract citations (now using paper IDs)
        section = Section(title="Rationale", content=content)
        section.citations = self._citation_extractor.extract_unique_paper_ids(content)

        return WritingResult(
            section=section,
            generation_time_ms=elapsed_ms,
            tokens_used=0,  # Can't track across retries easily
            cost_usd=0.0,
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

        # Normalize paragraph breaks for consistent formatting
        content = self._normalize_paragraph_breaks(content)

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
        use_perplexity: bool = True,
    ) -> tuple[Section, list[Paper]]:
        """Write complete introduction section with all subsections.

        This method writes the full introduction and returns both the section
        and the papers that were cited, which should be added to the reference
        section.

        Args:
            research_question: The research question for the review
            inclusion_criteria: Study inclusion criteria (optional)
            primary_outcome: Primary outcome of interest (optional)
            literature_context: Relevant papers for context (optional)
            retriever: RAG retriever for fetching literature (optional)
            use_perplexity: Use Perplexity API for literature (default: True)

        Returns:
            Tuple of (introduction_section, list_of_cited_papers)
        """
        # Clear reference manager for fresh start
        self.reference_manager.clear()

        # Create main introduction section
        intro_section = Section(title="Introduction", content="")

        # 1. Background
        background_result = await self.write_background(
            research_question, literature_context, retriever, use_perplexity
        )
        intro_section.add_subsection(background_result.section)

        # 2. Rationale
        rationale_result = await self.write_rationale(
            research_question, literature_context, retriever, use_perplexity
        )
        intro_section.add_subsection(rationale_result.section)

        # 3. Objectives
        objectives_result = await self.write_objectives(
            research_question, inclusion_criteria, primary_outcome
        )
        intro_section.add_subsection(objectives_result.section)

        # Update the main section's citations from all subsections
        self.reference_manager.update_section_citations(intro_section)

        # Get all papers cited in the introduction
        cited_papers = self.reference_manager.get_papers_for_section(intro_section)

        return intro_section, cited_papers

    def get_collected_papers(self) -> list[Paper]:
        """Get all papers collected during writing.

        Returns:
            List of all registered papers
        """
        return self.reference_manager.all_papers

    def validate_citations(self, section: Section) -> dict[str, Any]:
        """Validate that all citations in a section have registered papers.

        Args:
            section: Section to validate

        Returns:
            Validation result dictionary
        """
        result = self.reference_manager.validate_citations(section)
        return {
            "valid": result.valid,
            "missing_papers": result.missing_papers,
            "unused_papers": result.unused_papers,
            "citation_count": result.citation_count,
            "unique_citation_count": result.unique_citation_count,
        }

    def generate_reference_list(self, section: Section) -> str:
        """Generate formatted reference list for a section.

        Args:
            section: Section to generate references for

        Returns:
            Formatted reference list as string
        """
        return self.reference_manager.generate_reference_section_text(section)

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

    # ==================== Numeric Citation Helper Methods ====================

    def _create_numeric_paper_mapping(
        self, papers: list[Paper]
    ) -> dict[int, Paper]:
        """Create mapping from numeric IDs to papers.

        Args:
            papers: List of papers

        Returns:
            Dict mapping 1, 2, 3... to papers
        """
        return {i + 1: paper for i, paper in enumerate(papers)}

    def _format_papers_for_prompt(self, papers: list[Paper]) -> str:
        """Format papers with numeric IDs for LLM prompt.

        Args:
            papers: List of papers to format

        Returns:
            Formatted string listing papers with numeric IDs
        """
        if not papers:
            return "No papers available to cite."

        lines = []
        for i, paper in enumerate(papers, 1):
            # Build author string
            if paper.authors:
                if len(paper.authors) == 1:
                    author_str = paper.authors[0]
                elif len(paper.authors) == 2:
                    author_str = f"{paper.authors[0]} & {paper.authors[1]}"
                else:
                    author_str = f"{paper.authors[0]} et al."
            else:
                author_str = "Unknown"

            # Build year string
            year_str = f"({paper.year})" if paper.year else "(n.d.)"

            # Build abstract snippet
            abstract_snippet = ""
            if paper.abstract:
                abstract_snippet = (
                    paper.abstract[:150] + "..."
                    if len(paper.abstract) > 150
                    else paper.abstract
                )

            lines.append(
                f"[{i}] {author_str} {year_str}. {paper.title}"
                + (f"\n    Abstract: {abstract_snippet}" if abstract_snippet else "")
            )

        return "\n".join(lines)

    def _get_numeric_id_mapping(self, papers: list[Paper]) -> dict[int, str]:
        """Get mapping from numeric IDs to paper best_identifier.

        Args:
            papers: List of papers

        Returns:
            Dict mapping 1, 2, 3... to paper IDs
        """
        return {i + 1: paper.best_identifier for i, paper in enumerate(papers)}

    async def _generate_with_validation(
        self,
        messages: list[dict[str, str]],
        papers: list[Paper],
        max_retries: int = 1,
    ) -> tuple[str, list[int]]:
        """Generate text with citation validation, retry, and cleanup.

        Args:
            messages: Chat messages for OpenAI
            papers: Available papers (defines valid citation range)
            max_retries: Maximum retry attempts if invalid citations found

        Returns:
            Tuple of (validated_content, used_citation_numbers)
        """
        import re

        max_valid = len(papers)
        num_to_id = self._get_numeric_id_mapping(papers)

        # First attempt
        response = await self._call_openai(messages)
        content = response.choices[0].message.content

        # Validate citations
        valid_citations, invalid_citations = (
            self._citation_extractor.validate_numeric_citations(content, max_valid)
        )

        # If invalid citations found and retries available, retry once
        if invalid_citations and max_retries > 0:
            # Build retry message
            valid_range = ", ".join(f"[{i}]" for i in range(1, max_valid + 1))
            retry_prompt = (
                f"Your previous response contained invalid citations: "
                f"{', '.join(f'[{n}]' for n in invalid_citations)}\n\n"
                f"Only these citations are available: {valid_range}\n\n"
                f"Please rewrite your response using ONLY valid citation numbers. "
                f"If a claim cannot be supported by the available papers, "
                f"state it without a citation."
            )

            messages_with_retry = messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": retry_prompt},
            ]

            response = await self._call_openai(messages_with_retry)
            content = response.choices[0].message.content

            # Re-validate
            valid_citations, invalid_citations = (
                self._citation_extractor.validate_numeric_citations(content, max_valid)
            )

        # Final cleanup: remove any remaining invalid numeric citations
        if invalid_citations:
            content, removed = (
                self._citation_extractor.remove_invalid_numeric_citations(
                    content, max_valid
                )
            )

        # Convert numeric citations to paper IDs
        content = self._citation_extractor.convert_numeric_to_paper_ids(
            content, num_to_id
        )

        # Final cleanup: remove any DOI-style citations that shouldn't be there
        # These can come from Perplexity's response content being included
        # Pattern matches: [10.1234/...], [doi:10.1234/...], DOI with nested brackets
        doi_patterns = [
            re.compile(r"\[10\.\d{4,}/[^\]]*\]"),  # [10.1234/...]
            re.compile(r"\[doi:10\.\d{4,}/[^\]]*\]", re.IGNORECASE),  # [doi:10.1234/...]
            re.compile(r"10\.\d{4,}/[^\s\[\]]+\[\d+\]"),  # DOI with trailing [1]
            re.compile(r"10\.\d{4,}/[^\s\[\]]+"),  # Bare DOI without brackets
        ]
        for pattern in doi_patterns:
            content = pattern.sub("", content)

        # Clean up orphaned brackets (left behind after removing citations)
        content = re.sub(r"\[\s*\]", "", content)  # Empty brackets []
        content = re.sub(r"\s+\]", "", content)  # Space before closing bracket
        content = re.sub(r"\[\s+", "", content)  # Opening bracket with only space

        # Clean up any double spaces or spaces before punctuation
        content = re.sub(r"  +", " ", content)
        content = re.sub(r" ([.,;:])", r"\1", content)
        content = re.sub(r"\s+\n", "\n", content)  # Trailing spaces before newlines

        # Normalize paragraph breaks for proper markdown formatting
        # Single newlines between paragraphs should become double newlines
        content = self._normalize_paragraph_breaks(content)

        # Return the valid citation numbers that were used
        used_numbers = [n for n in valid_citations if n in range(1, max_valid + 1)]

        return content, used_numbers

    def _normalize_paragraph_breaks(self, content: str) -> str:
        """Normalize paragraph breaks for markdown formatting.

        Converts single newlines between paragraphs to double newlines,
        which is required for proper paragraph separation in markdown.

        Args:
            content: Text content that may have single newlines between paragraphs

        Returns:
            Content with proper paragraph breaks (double newlines)
        """
        import re

        # First, normalize any existing multiple newlines to exactly two
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Split into lines
        lines = content.split("\n")
        result_lines = []

        for i, line in enumerate(lines):
            result_lines.append(line)

            # If this line ends a paragraph (non-empty, ends with sentence-ending punctuation)
            # and the next line starts a new paragraph (non-empty, starts with capital letter)
            # then we need a blank line between them
            if i < len(lines) - 1:
                current_line = line.strip()
                next_line = lines[i + 1].strip()

                # Check if we're between two paragraphs
                if (
                    current_line
                    and next_line
                    and current_line[-1] in ".!?])"
                    and next_line[0].isupper()
                ):
                    # Add blank line if not already present
                    if result_lines and result_lines[-1] != "":
                        result_lines.append("")

        return "\n".join(result_lines)
