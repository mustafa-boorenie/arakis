from __future__ import annotations
"""Google Scholar client using the scholarly library with rate limiting."""

import asyncio
import hashlib
import random
import time
from typing import Any

from arakis.clients.base import BaseSearchClient, RateLimitError, SearchClientError
from arakis.config import get_settings
from arakis.models.paper import Author, Paper, PaperSource, SearchResult


class GoogleScholarClient(BaseSearchClient):
    """
    Google Scholar search client using the scholarly library.

    Uses aggressive rate limiting and random delays to avoid blocking.
    Falls back gracefully when blocked.
    """

    source = PaperSource.GOOGLE_SCHOLAR

    def __init__(self):
        self.settings = get_settings()
        self._last_request_time = 0.0
        self._consecutive_errors = 0
        self._is_blocked = False
        self._scholarly = None

    def _get_scholarly(self):
        """Lazy load scholarly to avoid import overhead."""
        if self._scholarly is None:
            try:
                import scholarly as sch

                self._scholarly = sch
            except ImportError:
                raise SearchClientError(
                    "scholarly library not installed. Run: pip install scholarly"
                )
        return self._scholarly

    async def _rate_limit(self):
        """Apply aggressive rate limiting with random jitter."""
        if self._is_blocked:
            # If previously blocked, wait longer
            await asyncio.sleep(60)
            self._is_blocked = False

        elapsed = time.time() - self._last_request_time
        min_delay = self.settings.scholarly_min_delay
        max_delay = self.settings.scholarly_max_delay

        # Random delay between min and max
        delay = random.uniform(min_delay, max_delay)

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request_time = time.time()

    async def search(self, query: str, max_results: int = 100) -> SearchResult:
        """
        Execute a Google Scholar search.

        Note: Due to aggressive rate limiting, this may be slow.
        Consider using for supplementary searches only.
        """
        start_time = time.time()
        scholarly = self._get_scholarly()

        await self._rate_limit()

        papers = []
        total_count = 0

        try:
            # Run the blocking scholarly call in a thread pool
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None, lambda: list(scholarly.search_pubs(query))
            )

            # Limit results
            search_results = search_results[:max_results]
            total_count = len(search_results)

            for result in search_results:
                try:
                    # Convert to dict for normalization
                    raw_data = self._result_to_dict(result)
                    paper = self.normalize_paper(raw_data)
                    papers.append(paper)
                except Exception:
                    continue

            self._consecutive_errors = 0

        except Exception as e:
            self._consecutive_errors += 1
            error_msg = str(e).lower()

            if "blocked" in error_msg or "captcha" in error_msg or "429" in error_msg:
                self._is_blocked = True
                raise RateLimitError(
                    "Google Scholar has blocked requests. "
                    "Try again later or use a different IP/proxy."
                )

            if self._consecutive_errors >= 3:
                raise SearchClientError(
                    f"Google Scholar search failed repeatedly: {e}"
                )

            raise SearchClientError(f"Google Scholar search failed: {e}")

        execution_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            query=query,
            source=PaperSource.GOOGLE_SCHOLAR,
            papers=papers,
            total_available=total_count,
            execution_time_ms=execution_time,
        )

    def _result_to_dict(self, result) -> dict[str, Any]:
        """Convert scholarly result object to dictionary."""
        bib = getattr(result, "bib", {}) or {}

        return {
            "title": bib.get("title", ""),
            "abstract": bib.get("abstract", ""),
            "authors": bib.get("author", []),
            "year": bib.get("year"),
            "venue": bib.get("venue", ""),
            "url": getattr(result, "pub_url", None),
            "citedby": getattr(result, "citedby", 0),
            "eprint_url": getattr(result, "eprint_url", None),
        }

    async def get_paper_by_id(self, paper_id: str) -> Paper | None:
        """
        Get paper by title search (Google Scholar doesn't use stable IDs).

        This is a best-effort lookup that may not always find the exact paper.
        """
        if paper_id.startswith("gscholar_"):
            # Try to extract title from ID if it was hashed from title
            return None

        # Search by the ID as a title
        results = await self.search(paper_id, max_results=1)
        return results.papers[0] if results.papers else None

    def normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Convert Google Scholar result to normalized Paper."""
        title = raw_data.get("title", "")
        paper_id = f"gscholar_{hashlib.md5(title.encode()).hexdigest()[:10]}"

        # Parse authors (may be a string or list)
        author_data = raw_data.get("authors", [])
        if isinstance(author_data, str):
            author_names = [a.strip() for a in author_data.split(",")]
        else:
            author_names = author_data

        authors = [Author(name=name) for name in author_names if name]

        # Year
        year_str = raw_data.get("year")
        year = int(year_str) if year_str and str(year_str).isdigit() else None

        # PDF URL from eprint
        pdf_url = raw_data.get("eprint_url")

        return Paper(
            id=paper_id,
            title=title,
            abstract=raw_data.get("abstract"),
            authors=authors,
            journal=raw_data.get("venue"),
            year=year,
            source=PaperSource.GOOGLE_SCHOLAR,
            source_url=raw_data.get("url"),
            pdf_url=pdf_url,
            open_access=pdf_url is not None,
            citation_count=raw_data.get("citedby"),
            raw_data=raw_data,
        )

    def get_query_syntax_help(self) -> str:
        """Return Google Scholar query syntax help."""
        return """
Google Scholar uses a simple but powerful search syntax:

BASIC OPERATORS:
- Quotes for exact phrases: "machine learning"
- OR for alternatives: cancer OR tumor
- - to exclude: diabetes -type2
- site: to limit to domain: site:nature.com

FIELD SEARCH:
- author:smith - Author name
- intitle:cancer - Words in title
- source:nature - Publication source

EXAMPLES:
1. "aspirin" "sepsis" mortality
2. intitle:CRISPR author:doudna
3. "machine learning" healthcare -review
4. "clinical trial" diabetes site:nih.gov

TIPS:
- Be specific - Google Scholar has billions of papers
- Use quotes for multi-word concepts
- Include key terms from your PICO

NOTE: Rate limits are aggressive. Use for supplementary searches.
"""

