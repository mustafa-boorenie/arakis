from __future__ import annotations
"""Base class for all search clients."""

from abc import ABC, abstractmethod
from typing import Any

from arakis.models.paper import Paper, PaperSource, SearchResult


class SearchClientError(Exception):
    """Base exception for search client errors."""

    pass


class RateLimitError(SearchClientError):
    """Raised when rate limit is exceeded."""

    pass


class NotConfiguredError(SearchClientError):
    """Raised when required configuration is missing."""

    pass


class BaseSearchClient(ABC):
    """Abstract base class for database search clients."""

    source: PaperSource

    @abstractmethod
    async def search(self, query: str, max_results: int = 100) -> SearchResult:
        """
        Execute a search query and return results.

        Args:
            query: Search query in the format appropriate for this database
            max_results: Maximum number of results to return

        Returns:
            SearchResult containing papers and metadata
        """
        pass

    @abstractmethod
    async def get_paper_by_id(self, paper_id: str) -> Paper | None:
        """
        Retrieve a specific paper by its database-specific ID.

        Args:
            paper_id: The ID (e.g., PMID, DOI, S2 ID)

        Returns:
            Paper if found, None otherwise
        """
        pass

    @abstractmethod
    def get_query_syntax_help(self) -> str:
        """
        Return help text describing the query syntax for this database.

        Used by the query generation agent to understand how to format queries.
        """
        pass

    @abstractmethod
    def normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """
        Convert raw API response to normalized Paper object.

        Args:
            raw_data: Raw response from the API

        Returns:
            Normalized Paper object
        """
        pass

    async def validate_query(self, query: str) -> tuple[bool, int, str]:
        """
        Validate a query by executing it with minimal results.

        Args:
            query: The query to validate

        Returns:
            Tuple of (is_valid, result_count, error_message)
        """
        try:
            result = await self.search(query, max_results=1)
            return True, result.total_available, ""
        except SearchClientError as e:
            return False, 0, str(e)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.source.value}>"
