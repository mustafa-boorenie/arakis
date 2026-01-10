from __future__ import annotations
"""OpenAlex search client - free, no API key required."""

import hashlib
import time
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arakis.clients.base import BaseSearchClient, SearchClientError
from arakis.config import get_settings
from arakis.models.paper import Author, Paper, PaperSource, SearchResult


class OpenAlexClient(BaseSearchClient):
    """
    OpenAlex search client.

    Completely free API with no key required.
    Excellent coverage and returns DOIs for deduplication.
    """

    source = PaperSource.OPENALEX

    BASE_URL = "https://api.openalex.org"

    def __init__(self):
        self.settings = get_settings()
        # OpenAlex requests polite email for identification
        self._email = self.settings.unpaywall_email or "research@example.com"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the OpenAlex API."""
        url = f"{self.BASE_URL}/{endpoint}"

        # Add polite pool email
        params["mailto"] = self._email

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def search(self, query: str, max_results: int = 100) -> SearchResult:
        """
        Execute an OpenAlex search.

        Query format:
        - Simple text search: "machine learning healthcare"
        - Filter syntax: concept.id:C12345,publication_year:2020-2024
        """
        start_time = time.time()

        # Determine if this is a filter query or text search
        if ":" in query and any(
            query.startswith(f) for f in ["concept", "author", "institution", "type"]
        ):
            # Filter-based query
            params = {
                "filter": query,
                "per_page": min(max_results, 200),  # OpenAlex max is 200 per page
            }
        else:
            # Text search
            params = {
                "search": query,
                "per_page": min(max_results, 200),
            }

        # Request abstracts
        params["select"] = (
            "id,doi,title,abstract_inverted_index,authorships,"
            "publication_year,primary_location,cited_by_count,type,concepts,open_access"
        )

        try:
            data = await self._request("works", params)
        except httpx.HTTPStatusError as e:
            raise SearchClientError(f"OpenAlex search failed: {e}")

        # Parse results
        papers = []
        for work in data.get("results", []):
            try:
                paper = self.normalize_paper(work)
                papers.append(paper)
            except Exception:
                continue

        total_count = data.get("meta", {}).get("count", len(papers))
        execution_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            query=query,
            source=PaperSource.OPENALEX,
            papers=papers,
            total_available=total_count,
            execution_time_ms=execution_time,
        )

    async def get_paper_by_id(self, paper_id: str) -> Paper | None:
        """Get a paper by OpenAlex ID or DOI."""
        # Normalize ID
        if paper_id.startswith("openalex_"):
            paper_id = paper_id.replace("openalex_", "")
        if not paper_id.startswith("https://"):
            if paper_id.startswith("W"):
                paper_id = f"https://openalex.org/{paper_id}"
            elif paper_id.startswith("10."):
                paper_id = f"https://doi.org/{paper_id}"

        try:
            # URL encode the ID
            encoded_id = quote(paper_id, safe="")
            data = await self._request(f"works/{encoded_id}", {})
            return self.normalize_paper(data)
        except Exception:
            return None

    def _reconstruct_abstract(self, inverted_index: dict[str, list[int]] | None) -> str | None:
        """Reconstruct abstract from OpenAlex's inverted index format."""
        if not inverted_index:
            return None

        # Create list of (position, word) tuples
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))

        # Sort by position and join
        words.sort(key=lambda x: x[0])
        return " ".join(word for _, word in words)

    def normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Convert OpenAlex work to normalized Paper."""
        # Extract OpenAlex ID
        openalex_id = raw_data.get("id", "")
        if openalex_id.startswith("https://openalex.org/"):
            openalex_id = openalex_id.replace("https://openalex.org/", "")

        paper_id = f"openalex_{openalex_id}" if openalex_id else hashlib.md5(
            str(raw_data).encode()
        ).hexdigest()[:12]

        # DOI
        doi = raw_data.get("doi")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        # Abstract
        abstract = self._reconstruct_abstract(raw_data.get("abstract_inverted_index"))

        # Authors
        authors = []
        for authorship in raw_data.get("authorships", []):
            author_info = authorship.get("author", {})
            name = author_info.get("display_name", "")
            if name:
                # Get first affiliation if available
                affiliations = authorship.get("institutions", [])
                affiliation = affiliations[0].get("display_name") if affiliations else None
                authors.append(Author(name=name, affiliation=affiliation))

        # Journal/venue
        primary_location = raw_data.get("primary_location", {}) or {}
        source_info = primary_location.get("source", {}) or {}
        journal = source_info.get("display_name")

        # Open access
        oa_info = raw_data.get("open_access", {}) or {}
        open_access = oa_info.get("is_oa", False)
        pdf_url = oa_info.get("oa_url")

        # Keywords from concepts
        keywords = [
            c.get("display_name", "")
            for c in raw_data.get("concepts", [])[:10]
            if c.get("score", 0) > 0.3
        ]

        return Paper(
            id=paper_id,
            openalex_id=openalex_id,
            doi=doi,
            title=raw_data.get("title", "") or "",
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=raw_data.get("publication_year"),
            source=PaperSource.OPENALEX,
            source_url=raw_data.get("id"),
            pdf_url=pdf_url,
            open_access=open_access,
            keywords=keywords,
            citation_count=raw_data.get("cited_by_count"),
            raw_data=raw_data,
        )

    def get_query_syntax_help(self) -> str:
        """Return OpenAlex query syntax help."""
        return """
OpenAlex supports two query modes:

1. TEXT SEARCH (simple):
   Just provide search terms: "machine learning healthcare"

2. FILTER QUERIES (advanced):
   Use filter syntax for precise control:

FILTERS:
- publication_year:2020-2024 - Year range
- publication_year:2023 - Specific year
- type:journal-article - Document type
- is_oa:true - Open access only
- cited_by_count:>100 - Citation threshold
- concepts.id:C12345 - OpenAlex concept ID
- authorships.author.id:A123 - Author ID
- primary_location.source.id:S123 - Journal/venue

COMBINING FILTERS:
Use comma to AND filters:
publication_year:2020-2024,type:journal-article,is_oa:true

DOCUMENT TYPES:
- journal-article
- book-chapter
- dissertation
- dataset
- preprint

EXAMPLES:
1. Simple: "sepsis aspirin mortality"
2. Filter: publication_year:2020-2024,type:journal-article
3. Combined: Search "sepsis" then filter by year in results
"""

