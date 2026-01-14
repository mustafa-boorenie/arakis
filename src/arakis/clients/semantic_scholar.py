from __future__ import annotations

"""Semantic Scholar search client - free API with generous limits."""

import hashlib
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arakis.clients.base import BaseSearchClient, RateLimitError, SearchClientError
from arakis.models.paper import Author, Paper, PaperSource, SearchResult


class SemanticScholarClient(BaseSearchClient):
    """
    Semantic Scholar search client.

    Free API with 100 requests/5 minutes for unauthenticated users.
    Provides citation context and influential citations.
    """

    source = PaperSource.SEMANTIC_SCHOLAR

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Fields to request
    PAPER_FIELDS = (
        "paperId,externalIds,title,abstract,year,authors,"
        "venue,publicationTypes,openAccessPdf,citationCount,fieldsOfStudy"
    )

    def __init__(self):
        self._last_request_time = 0.0
        # Conservative rate limit: 100 requests per 5 minutes = ~0.33/sec
        # We'll use 1 per 5 seconds to be very conservative
        self._min_interval = 5.0
        self._lock = None
        self._loop = None

    def _get_lock(self):
        """Get or create lock for current event loop."""
        import asyncio

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # Create new lock if we don't have one or we're in a different event loop
        if self._lock is None or self._loop != current_loop:
            self._lock = asyncio.Lock()
            self._loop = current_loop
        return self._lock

    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        import asyncio

        async with self._get_lock():
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
    async def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the Semantic Scholar API."""
        await self._rate_limit()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 429:
                raise RateLimitError("Semantic Scholar rate limit exceeded")
            if response.status_code == 400:
                error_data = response.json()
                raise SearchClientError(f"Invalid query: {error_data.get('message', '')}")

            response.raise_for_status()
            return response.json()

    async def search(self, query: str, max_results: int = 100) -> SearchResult:
        """Execute a Semantic Scholar search."""
        start_time = time.time()

        params = {
            "query": query,
            "limit": min(max_results, 100),  # S2 max is 100 per request
            "fields": self.PAPER_FIELDS,
        }

        try:
            data = await self._request(self.SEARCH_URL, params)
        except httpx.HTTPStatusError as e:
            raise SearchClientError(f"Semantic Scholar search failed: {e}")

        papers = []
        for item in data.get("data", []):
            try:
                paper = self.normalize_paper(item)
                papers.append(paper)
            except Exception:
                continue

        total_count = data.get("total", len(papers))
        execution_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            query=query,
            source=PaperSource.SEMANTIC_SCHOLAR,
            papers=papers,
            total_available=total_count,
            execution_time_ms=execution_time,
        )

    async def get_paper_by_id(self, paper_id: str) -> Paper | None:
        """Get a paper by S2 ID, DOI, or other identifier."""
        # Normalize ID format
        if paper_id.startswith("s2_"):
            paper_id = paper_id.replace("s2_", "")
        elif paper_id.startswith("10."):
            paper_id = f"DOI:{paper_id}"
        elif paper_id.isdigit():
            paper_id = f"PMID:{paper_id}"

        url = f"{self.BASE_URL}/paper/{paper_id}"
        params = {"fields": self.PAPER_FIELDS}

        try:
            data = await self._request(url, params)
            return self.normalize_paper(data)
        except Exception:
            return None

    def normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Convert Semantic Scholar paper to normalized Paper."""
        s2_id = raw_data.get("paperId", "")
        paper_id = f"s2_{s2_id}" if s2_id else hashlib.md5(str(raw_data).encode()).hexdigest()[:12]

        # External IDs
        external_ids = raw_data.get("externalIds", {}) or {}
        doi = external_ids.get("DOI")
        pmid = external_ids.get("PubMed")
        arxiv_id = external_ids.get("ArXiv")

        # Authors
        authors = []
        for author in raw_data.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(Author(name=name))

        # Open Access PDF
        oa_info = raw_data.get("openAccessPdf", {}) or {}
        pdf_url = oa_info.get("url")
        open_access = pdf_url is not None

        # Publication types as keywords
        pub_types = raw_data.get("publicationTypes", []) or []
        fields = raw_data.get("fieldsOfStudy", []) or []

        return Paper(
            id=paper_id,
            s2_id=s2_id,
            doi=doi,
            pmid=pmid,
            arxiv_id=arxiv_id,
            title=raw_data.get("title", "") or "",
            abstract=raw_data.get("abstract"),
            authors=authors,
            journal=raw_data.get("venue"),
            year=raw_data.get("year"),
            source=PaperSource.SEMANTIC_SCHOLAR,
            source_url=f"https://www.semanticscholar.org/paper/{s2_id}" if s2_id else None,
            pdf_url=pdf_url,
            open_access=open_access,
            keywords=fields,
            publication_types=pub_types,
            citation_count=raw_data.get("citationCount"),
            raw_data=raw_data,
        )

    def get_query_syntax_help(self) -> str:
        """Return Semantic Scholar query syntax help."""
        return """
Semantic Scholar uses simple text search:

BASIC SEARCH:
- Enter keywords: "machine learning healthcare"
- Phrases are supported: "deep learning"
- Boolean operators work implicitly (AND)

TIPS:
- Keep queries focused and specific
- Use key terms from your research question
- Medical/scientific terminology works well
- The API is best for broad topic searches

EXAMPLES:
1. "aspirin sepsis mortality"
2. "machine learning cardiovascular disease prediction"
3. "CRISPR gene therapy clinical trials"

NOTE: Semantic Scholar excels at:
- Finding highly cited papers
- Identifying influential citations
- Covering computer science and biomedicine
"""
