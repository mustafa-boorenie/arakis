"""Perplexity API client for deep research literature retrieval.

This client uses the Perplexity API to search for academic literature
for use in systematic review introductions. It returns Paper objects
that can be registered with the ReferenceManager.

Note: This is NOT used for the systematic review search itself - it's
specifically for gathering background literature for the introduction
section, which should come from general academic sources rather than
the specific search results of the review.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arakis.config import get_settings
from arakis.models.paper import Author, Paper, PaperSource


class PerplexityClientError(Exception):
    """Base exception for Perplexity client errors."""

    pass


class PerplexityRateLimitError(PerplexityClientError):
    """Raised when rate limit is exceeded."""

    pass


class PerplexityNotConfiguredError(PerplexityClientError):
    """Raised when API key is not configured."""

    pass


@dataclass
class PerplexitySearchResult:
    """A single search result from Perplexity.

    Attributes:
        title: Title of the result
        url: URL to the source
        snippet: Text snippet/summary
        date: Publication date if available
    """

    title: str
    url: str
    snippet: str
    date: str | None = None


@dataclass
class PerplexityResponse:
    """Response from Perplexity API.

    Attributes:
        content: The generated answer text
        citations: URLs cited in the response
        search_results: Detailed search results
        model: Model used for generation
        usage: Token usage statistics
    """

    content: str
    citations: list[str]
    search_results: list[PerplexitySearchResult]
    model: str
    usage: dict[str, int] = field(default_factory=dict)


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting from text.

    Args:
        text: Text potentially containing markdown

    Returns:
        Clean text with markdown removed
    """
    if not text:
        return text

    # Remove bold/italic markers (paired)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"__([^_]+)__", r"\1", text)  # __bold__
    # Handle paired single markers after removing double
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)  # *italic* (not part of **)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", text)  # _italic_ (not part of __)

    # Remove orphaned/unpaired bold/italic markers (leftover ** or * at start/end)
    text = re.sub(r"^\*{1,2}\s*", "", text)  # Leading * or **
    text = re.sub(r"\s*\*{1,2}$", "", text)  # Trailing * or **
    text = re.sub(r"^_{1,2}\s*", "", text)  # Leading _ or __
    text = re.sub(r"\s*_{1,2}$", "", text)  # Trailing _ or __

    # Remove leading bullets, dashes, and list markers (including * as bullet)
    text = re.sub(r"^[\s]*[-•]\s*", "", text)  # - bullet, • bullet
    text = re.sub(r"^[\s]*\*\s+", "", text)  # * bullet (asterisk followed by space)
    text = re.sub(r"^[\s]*\d+\.\s*", "", text)  # 1. numbered list

    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s*", "", text)  # # headers

    # Remove markdown links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [text](url)

    # Remove backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _clean_paper_title(title: str) -> str:
    """Clean a paper title by removing common artifacts.

    Args:
        title: Raw paper title

    Returns:
        Cleaned title
    """
    if not title:
        return title

    # Strip markdown first
    title = _strip_markdown(title)

    # Remove source suffixes like "- PubMed", "- JAMA Network", "- ScienceDirect", "- NIH"
    title = re.sub(r"\s*-\s*(?:PubMed|JAMA\s*Network|ScienceDirect|Frontiers|Wiley|Springer|Nature|BMJ|Lancet|NEJM|Cochrane|Google\s*Scholar|NIH|NCBI|PMC|ResearchGate|Academia|Oxford\s*Academic|Cambridge).*$", "", title, flags=re.IGNORECASE)

    # Remove "Title:" prefix if present
    title = re.sub(r"^Title:\s*", "", title, flags=re.IGNORECASE)

    # Remove trailing ellipsis or incomplete markers
    title = re.sub(r"\s*\.{3,}$", "", title)
    title = re.sub(r"\s*…$", "", title)

    # Clean up quotes
    title = title.strip('"\'')

    return title.strip()


class PerplexityClient:
    """Perplexity API client for literature research.

    Uses Perplexity's Sonar model for web-grounded research with citations.
    This client is specifically designed for retrieving background literature
    for systematic review introductions.

    Example usage:
        client = PerplexityClient()

        # Research a topic
        response = await client.research_topic(
            "Effect of aspirin on cardiovascular disease"
        )
        print(response.content)

        # Get papers from search results
        papers = await client.search_for_papers(
            "aspirin cardiovascular meta-analysis",
            max_results=5
        )
        for paper in papers:
            print(f"{paper.title} ({paper.year})")
    """

    BASE_URL = "https://api.perplexity.ai"

    def __init__(self, model: str = "sonar"):
        """Initialize Perplexity client.

        Args:
            model: Model to use. Options:
                - "sonar": Standard research model (default)
                - "sonar-pro": More thorough research (higher cost)
        """
        self.settings = get_settings()
        self.api_key = self.settings.perplexity_api_key
        self.model = model
        self._last_request_time = 0.0
        self._min_interval = 1.0  # 1 request per second to be safe
        self._lock: asyncio.Lock | None = None

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def _get_lock(self) -> asyncio.Lock:
        """Get or create lock for rate limiting."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def _rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        async with self._get_lock():
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
    async def _request(
        self, messages: list[dict[str, str]], system_prompt: str | None = None
    ) -> dict[str, Any]:
        """Make a request to the Perplexity API.

        Args:
            messages: Chat messages
            system_prompt: Optional system prompt

        Returns:
            API response as dictionary

        Raises:
            PerplexityNotConfiguredError: If API key not set
            PerplexityRateLimitError: If rate limited
            PerplexityClientError: For other errors
        """
        await self._rate_limit()

        if not self.api_key:
            raise PerplexityNotConfiguredError(
                "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your environment."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build messages with optional system prompt
        full_messages = messages.copy()
        if system_prompt:
            full_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": full_messages,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 429:
                    raise PerplexityRateLimitError("Perplexity rate limit exceeded")

                if response.status_code == 401:
                    raise PerplexityClientError("Invalid Perplexity API key")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                raise PerplexityClientError(f"Perplexity API error: {e}")
            except httpx.TimeoutException:
                raise PerplexityClientError("Perplexity API request timed out")

    async def research_topic(self, topic: str, context: str | None = None) -> PerplexityResponse:
        """Research a topic and get grounded literature references.

        This method performs deep research on a topic, returning an AI-generated
        summary with citations to academic sources.

        Args:
            topic: Research topic or question
            context: Additional context to guide the search

        Returns:
            PerplexityResponse with content and citations
        """
        system_prompt = """You are a research assistant helping to find relevant
academic literature for a systematic review introduction. Focus on:

1. Key foundational studies in the field
2. Recent important findings and developments
3. Meta-analyses and systematic reviews on the topic
4. Epidemiological data and clinical significance
5. Current guidelines and recommendations

Provide specific citations with author names and years where possible.
Focus on peer-reviewed academic sources from reputable journals.
Mention the DOI when available."""

        user_message = f"Find relevant background literature for: {topic}"
        if context:
            user_message += f"\n\nAdditional context: {context}"

        messages = [{"role": "user", "content": user_message}]

        data = await self._request(messages, system_prompt)

        # Parse response
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Extract citations from response
        citations = data.get("citations", [])

        # Parse search results if available
        search_results = []
        for sr in data.get("search_results", []):
            search_results.append(
                PerplexitySearchResult(
                    title=sr.get("title", ""),
                    url=sr.get("url", ""),
                    snippet=sr.get("snippet", ""),
                    date=sr.get("date"),
                )
            )

        return PerplexityResponse(
            content=content,
            citations=citations,
            search_results=search_results,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
        )

    async def search_for_papers(self, query: str, max_results: int = 10) -> list[Paper]:
        """Search for academic papers on a topic.

        Converts Perplexity search results into Paper objects that can be
        used with the ReferenceManager.

        Args:
            query: Research query
            max_results: Maximum papers to return

        Returns:
            List of Paper objects from search results
        """
        system_prompt = """You are a research librarian searching for academic papers.
For the given query, find relevant peer-reviewed academic papers.

For EACH paper, provide the following in a structured format:
- Title: [exact paper title]
- Authors: [comma-separated list of authors]
- Journal: [journal name]
- Year: [publication year]
- DOI: [DOI if available, or "N/A"]

Focus on:
- Peer-reviewed journal articles
- Systematic reviews and meta-analyses
- High-impact studies in the field
- Recent publications (within last 10 years when relevant)

Return at least 5-10 relevant papers."""

        messages = [{"role": "user", "content": f"Find academic papers about: {query}"}]

        response_data = await self._request(messages, system_prompt)

        papers = []

        # Parse the response content to extract paper information
        choice = response_data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")

        # Extract papers from the structured response
        extracted_papers = self._parse_papers_from_content(content)
        papers.extend(extracted_papers[:max_results])

        # Also try to create papers from search results
        for sr in response_data.get("search_results", []):
            if len(papers) >= max_results:
                break
            paper = self._convert_search_result_to_paper(sr)
            if paper and not any(p.title == paper.title for p in papers):
                papers.append(paper)

        return papers[:max_results]

    def _parse_papers_from_content(self, content: str) -> list[Paper]:
        """Parse paper information from Perplexity response content.

        Args:
            content: Response content containing paper details

        Returns:
            List of extracted Paper objects
        """
        papers = []

        # Split content into potential paper entries
        # Look for patterns like "Title:" or numbered lists
        entries = re.split(r"\n(?=\d+\.|Title:|•|\*)", content)

        for entry in entries:
            paper = self._extract_paper_from_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _extract_paper_from_entry(self, entry: str) -> Paper | None:
        """Extract a Paper object from a text entry.

        Args:
            entry: Text containing paper information

        Returns:
            Paper if extraction successful, None otherwise
        """
        if not entry or len(entry) < 20:
            return None

        # Extract title - look for explicit "Title:" field first
        title_match = re.search(
            r"Title:\s*([^\n]+?)(?:\n|Authors:|Journal:|Year:|DOI:|$)",
            entry,
            re.IGNORECASE,
        )
        if not title_match:
            # Fall back to first substantial text that looks like a title
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

        # Skip entries that look like headers or descriptions rather than paper titles
        skip_patterns = [
            r"^#",  # Markdown headers
            r"^\*\*Key Finding",  # Bold key findings
            r"^Academic Papers",  # Section headers
            r"^Recent",  # Section headers
            r"^Summary",  # Section headers
        ]
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
            # Parse comma-separated or "and" separated authors
            author_names = re.split(r",\s*(?:and\s+)?|\s+and\s+", author_str)
            for name in author_names:
                name = name.strip().strip(".")
                # Skip empty or too short names
                if name and len(name) > 2:
                    authors.append(Author(name=name))

        # Extract journal
        journal_match = re.search(r"Journal:?\s*([^\n]+?)(?:\n|Year:|DOI:|$)", entry, re.IGNORECASE)
        journal = None
        if journal_match:
            journal = _strip_markdown(journal_match.group(1).strip())

        # Extract year
        year_match = re.search(r"(?:Year:?\s*)?(\d{4})", entry)
        year = int(year_match.group(1)) if year_match else None

        # Extract DOI - be careful to exclude trailing citation markers like [1], [2]
        doi_match = re.search(r"(?:DOI:?\s*)?(10\.\d{4,}/[^\s\n\[\]]+)", entry, re.IGNORECASE)
        doi = None
        if doi_match:
            doi = doi_match.group(1).strip()
            # Remove trailing punctuation and citation markers
            doi = re.sub(r"[\[\]\(\)]+$", "", doi)
            doi = doi.rstrip(".,;:")

        # Generate unique ID from cleaned title
        paper_id = f"perplexity_{hashlib.md5(title.encode()).hexdigest()[:12]}"

        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi,
            source=PaperSource.OPENALEX,  # Use as placeholder
            retrieved_at=datetime.now(timezone.utc),
        )

    def _convert_search_result_to_paper(self, search_result: dict[str, Any]) -> Paper | None:
        """Convert a Perplexity search result to a Paper object.

        Args:
            search_result: Search result dictionary

        Returns:
            Paper if conversion successful, None otherwise
        """
        title = search_result.get("title", "")
        url = search_result.get("url", "")
        snippet = search_result.get("snippet", "")

        if not title or len(title) < 10:
            return None

        # Clean the title
        title = _clean_paper_title(title)

        if len(title) < 10:
            return None

        # Generate unique ID from cleaned title (not URL, for consistency)
        paper_id = f"perplexity_{hashlib.md5(title.encode()).hexdigest()[:12]}"

        # Try to extract DOI from URL
        doi = None
        if "doi.org/" in url:
            doi = url.split("doi.org/")[-1].split("?")[0]
            # Clean up DOI
            doi = doi.rstrip("/.,;:")

        # Try to extract year from date or snippet
        year = None
        date_str = search_result.get("date", "")
        if date_str:
            year_match = re.search(r"(\d{4})", date_str)
            if year_match:
                year = int(year_match.group(1))

        # If no year from date, try to get it from snippet
        if not year and snippet:
            year_match = re.search(r"\b(19|20)\d{2}\b", snippet)
            if year_match:
                year = int(year_match.group(0))

        return Paper(
            id=paper_id,
            title=title,
            abstract=snippet,
            doi=doi,
            year=year,
            source=PaperSource.OPENALEX,
            source_url=url,
            raw_data=search_result,
            retrieved_at=datetime.now(timezone.utc),
        )

    async def get_literature_context(
        self, research_question: str, max_papers: int = 5
    ) -> tuple[str, list[Paper]]:
        """Get literature context for writing an introduction.

        This is the main method to use when writing introduction sections.
        It returns both a summary and structured paper references.

        Args:
            research_question: The systematic review research question
            max_papers: Maximum number of papers to return

        Returns:
            Tuple of (summary_text, list_of_papers)
        """
        # First, get a research summary
        response = await self.research_topic(research_question)

        # Then, search for specific papers
        papers = await self.search_for_papers(research_question, max_papers)

        return response.content, papers
