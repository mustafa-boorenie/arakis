"""OpenAI-based literature search client using Responses API with web search.

This module provides literature search capabilities using OpenAI's Responses API
with built-in web search tool, replacing the Perplexity integration.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.paper import Author, Paper, PaperSource
from arakis.utils import get_openai_rate_limiter

logger = logging.getLogger(__name__)


class OpenAILiteratureClientError(Exception):
    """Base exception for OpenAI literature client errors."""

    pass


class OpenAILiteratureRateLimitError(OpenAILiteratureClientError):
    """Rate limit exceeded."""

    pass


@dataclass
class WebSearchResult:
    """A single web search result.

    Attributes:
        title: Title of the result
        url: URL of the source
        snippet: Text snippet from the result
        date: Publication date if available
    """

    title: str
    url: str
    snippet: str
    date: Optional[str] = None


@dataclass
class LiteratureResponse:
    """Response from literature research.

    Attributes:
        content: The generated research summary
        citations: URLs cited in the response
        search_results: Detailed search results
        model: Model used for generation
        usage: Token usage statistics
    """

    content: str
    citations: list[str]
    search_results: list[WebSearchResult]
    model: str
    usage: dict[str, int] = field(default_factory=dict)


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting from text."""
    if not text:
        return text

    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _clean_paper_title(title: str) -> str:
    """Clean a paper title by removing common artifacts."""
    if not title:
        return title

    title = _strip_markdown(title)
    title = re.sub(
        r"\s*-\s*(?:PubMed|JAMA\s*Network|ScienceDirect|Frontiers|Wiley|Springer|"
        r"Nature|BMJ|Lancet|NEJM|Cochrane|Google\s*Scholar|NIH|NCBI|PMC|"
        r"ResearchGate|Academia|Oxford\s*Academic|Cambridge).*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"^Title:\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\.{3,}$", "", title)
    title = re.sub(r"\s*…$", "", title)
    title = title.strip("\"'")

    return title.strip()


class OpenAILiteratureClient:
    """OpenAI-based literature search client using Responses API with web search.

    Uses OpenAI's Responses API with built-in web search tool for finding
    academic literature. This replaces the Perplexity integration.

    Example usage:
        client = OpenAILiteratureClient()

        # Research a topic
        response = await client.research_topic(
            "Effect of metformin on mortality in type 2 diabetes"
        )
        print(response.content)
        print(f"Found {len(response.citations)} citations")

        # Search for papers
        papers = await client.search_for_papers(
            "metformin mortality diabetes",
            max_results=5
        )
        for paper in papers:
            print(f"- {paper.title}")
    """

    def __init__(
        self,
        model: str = "o3",
        writing_model: str = "o3",
    ):
        """Initialize the OpenAI literature client.

        Args:
            model: Model to use for web search (default: o3 for reasoning)
            writing_model: Model to use for writing tasks (default: o3)
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.writing_model = writing_model
        self.rate_limiter = get_openai_rate_limiter()
        self._last_request_time = 0.0
        self._lock: Optional[asyncio.Lock] = None

    @property
    def is_configured(self) -> bool:
        """Check if the client is configured with an API key."""
        settings = get_settings()
        return bool(settings.openai_api_key)

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the async lock."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def _rate_limit(self) -> None:
        """Enforce rate limiting (1 request per second)."""
        async with self._get_lock():
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < 1.0:
                await asyncio.sleep(1.0 - time_since_last)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request_with_web_search(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """Make a request using Responses API with web search tool.

        Args:
            query: User query
            system_prompt: Optional system prompt
            max_tokens: Maximum output tokens

        Returns:
            Response data with content and citations
        """
        await self._rate_limit()
        await self.rate_limiter.wait()

        # Build the request using Responses API with web search
        # The Responses API uses a different structure
        try:
            response = await self.client.responses.create(
                model=self.model,
                input=query,
                tools=[{"type": "web_search"}],
                instructions=system_prompt,
                max_output_tokens=max_tokens,
            )

            # Extract content and citations from response
            content = ""
            citations = []
            search_results = []

            # Parse response output
            for output in response.output:
                if output.type == "message":
                    for content_block in output.content:
                        if content_block.type == "output_text":
                            content = content_block.text
                            # Extract citations from annotations
                            if hasattr(content_block, "annotations"):
                                for annotation in content_block.annotations:
                                    if annotation.type == "url_citation":
                                        citations.append(annotation.url)
                                        search_results.append(
                                            WebSearchResult(
                                                title=annotation.title or "",
                                                url=annotation.url,
                                                snippet="",
                                            )
                                        )

            return {
                "content": content,
                "citations": citations,
                "search_results": search_results,
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens if response.usage else 0,
                    "output_tokens": response.usage.output_tokens if response.usage else 0,
                },
            }

        except Exception as e:
            # Fallback to Chat Completions API if Responses API not available
            logger.warning(f"Responses API failed, falling back to Chat Completions: {e}")
            return await self._request_with_chat_completions(query, system_prompt, max_tokens)

    async def _request_with_chat_completions(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """Fallback to Chat Completions API without web search.

        Args:
            query: User query
            system_prompt: Optional system prompt
            max_tokens: Maximum output tokens

        Returns:
            Response data
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})

        # Use reasoning model parameters
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # o3/o1 models use max_completion_tokens, not max_tokens
        if self.model.startswith("o"):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = 0.7

        response = await self.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""

        return {
            "content": content,
            "citations": [],
            "search_results": [],
            "model": self.model,
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        }

    async def research_topic(
        self,
        topic: str,
        context: Optional[str] = None,
    ) -> LiteratureResponse:
        """Research a topic and return structured findings with citations.

        Args:
            topic: Research topic or question
            context: Additional context for the research

        Returns:
            LiteratureResponse with content, citations, and search results
        """
        system_prompt = """You are a research assistant finding relevant academic literature
for a systematic review introduction. Focus on:
1. Key foundational studies in the field
2. Recent important findings and developments
3. Meta-analyses and systematic reviews on the topic
4. Epidemiological data and clinical significance
5. Current guidelines and recommendations

For each key finding, cite the source. Provide a comprehensive summary
of the current state of knowledge on the topic.

Format your response with clear sections:
- Background and significance
- Key studies and their findings
- Current gaps or controversies
- Summary of evidence strength"""

        query = f"Find relevant background literature for: {topic}"
        if context:
            query += f"\n\nAdditional context: {context}"

        data = await self._request_with_web_search(query, system_prompt)

        return LiteratureResponse(
            content=data["content"],
            citations=data["citations"],
            search_results=[
                WebSearchResult(
                    title=sr.title if isinstance(sr, WebSearchResult) else sr.get("title", ""),
                    url=sr.url if isinstance(sr, WebSearchResult) else sr.get("url", ""),
                    snippet=sr.snippet
                    if isinstance(sr, WebSearchResult)
                    else sr.get("snippet", ""),
                    date=sr.date if isinstance(sr, WebSearchResult) else sr.get("date"),
                )
                for sr in data["search_results"]
            ],
            model=data["model"],
            usage=data["usage"],
        )

    async def search_for_papers(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[Paper]:
        """Search for academic papers on a topic.

        Args:
            query: Research query
            max_results: Maximum papers to return

        Returns:
            List of Paper objects
        """
        system_prompt = f"""You are a research librarian searching for academic papers.
Find relevant peer-reviewed academic papers for the given query.

For EACH paper, provide in a structured format:
- Title: [exact paper title]
- Authors: [comma-separated list of authors]
- Journal: [journal name]
- Year: [publication year]
- DOI: [DOI if available, or "N/A"]
- Key findings: [1-2 sentence summary]

Focus on:
- Peer-reviewed journal articles
- Systematic reviews and meta-analyses
- High-impact studies in the field
- Recent publications (within last 10 years when relevant)

Return {max_results} relevant papers."""

        user_query = f"Find academic papers about: {query}"

        data = await self._request_with_web_search(user_query, system_prompt)

        papers = []

        # Parse papers from content
        extracted = self._parse_papers_from_content(data["content"])
        papers.extend(extracted[:max_results])

        # Also convert citations to papers if available
        for citation in data["citations"][:max_results]:
            if len(papers) >= max_results:
                break
            # Create paper from citation URL
            paper = self._paper_from_url(citation)
            if paper and not any(p.title == paper.title for p in papers):
                papers.append(paper)

        return papers[:max_results]

    async def get_literature_context(
        self,
        research_question: str,
        max_papers: int = 5,
    ) -> tuple[str, list[Paper]]:
        """Get literature context for a research question.

        Combines research_topic and search_for_papers to provide
        both a summary and a list of papers.

        Args:
            research_question: The research question
            max_papers: Maximum papers to return

        Returns:
            Tuple of (summary_text, list_of_papers)
        """
        # Get research summary
        response = await self.research_topic(research_question)

        # Get papers
        papers = await self.search_for_papers(research_question, max_papers)

        return response.content, papers

    def _parse_papers_from_content(self, content: str) -> list[Paper]:
        """Parse paper information from response content."""
        papers = []

        entries = re.split(r"\n(?=\d+\.|Title:|•|\*)", content)

        for entry in entries:
            paper = self._extract_paper_from_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _extract_paper_from_entry(self, entry: str) -> Optional[Paper]:
        """Extract a Paper object from a text entry."""
        if not entry or len(entry) < 20:
            return None

        # Extract title
        title_match = re.search(
            r"Title:\s*([^\n]+?)(?:\n|Authors:|Journal:|Year:|DOI:|$)",
            entry,
            re.IGNORECASE,
        )
        if not title_match:
            title_match = re.search(
                r"^[\s\d.*-]*([A-Z][^.\n]{15,}?)(?:\n|Authors:|Journal:|Year:|DOI:|$)",
                entry,
                re.MULTILINE,
            )
        if not title_match:
            return None

        title = title_match.group(1).strip()
        title = _clean_paper_title(title)

        if len(title) < 10:
            return None

        # Skip headers
        skip_patterns = [r"^#", r"^\*\*Key Finding", r"^Academic Papers", r"^Recent", r"^Summary"]
        for pattern in skip_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return None

        # Extract authors
        authors_match = re.search(
            r"Authors?:?\s*([^\n]+?)(?:\n|Journal:|Year:|DOI:|$)",
            entry,
            re.IGNORECASE,
        )
        authors = []
        if authors_match:
            author_str = _strip_markdown(authors_match.group(1).strip())
            author_names = re.split(r",\s*(?:and\s+)?|\s+and\s+", author_str)
            for name in author_names:
                name = name.strip().strip(".")
                if name and len(name) > 2:
                    authors.append(Author(name=name))

        # Extract journal
        journal_match = re.search(
            r"Journal:?\s*([^\n]+?)(?:\n|Year:|DOI:|$)",
            entry,
            re.IGNORECASE,
        )
        journal = None
        if journal_match:
            journal = _strip_markdown(journal_match.group(1).strip())

        # Extract year
        year_match = re.search(r"(?:Year:?\s*)?(\d{4})", entry)
        year = int(year_match.group(1)) if year_match else None

        # Extract DOI
        doi_match = re.search(
            r"(?:DOI:?\s*)?(10\.\d{4,}/[^\s\n\[\]]+)",
            entry,
            re.IGNORECASE,
        )
        doi = None
        if doi_match:
            doi = doi_match.group(1).strip()
            doi = re.sub(r"[\[\]\(\)]+$", "", doi)
            doi = doi.rstrip(".,;:")

        # Generate unique ID
        paper_id = f"openai_{hashlib.md5(title.encode()).hexdigest()[:12]}"

        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi,
            source=PaperSource.OPENALEX,
            retrieved_at=datetime.now(timezone.utc),
        )

    def _paper_from_url(self, url: str) -> Optional[Paper]:
        """Create a basic Paper object from a URL."""
        # Extract DOI if present
        doi = None
        if "doi.org/" in url:
            doi = url.split("doi.org/")[-1].split("?")[0].rstrip("/.,;:")

        # Generate ID from URL
        paper_id = f"openai_{hashlib.md5(url.encode()).hexdigest()[:12]}"

        return Paper(
            id=paper_id,
            title=url,  # Will be cleaned up later
            doi=doi,
            source=PaperSource.OPENALEX,
            source_url=url,
            retrieved_at=datetime.now(timezone.utc),
        )
