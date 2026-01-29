"""Clients package."""

from arakis.clients.base import (
    BaseSearchClient,
    NotConfiguredError,
    RateLimitError,
    SearchClientError,
)
from arakis.clients.openai_literature import (
    OpenAILiteratureClient,
    OpenAILiteratureClientError,
    OpenAILiteratureRateLimitError,
    LiteratureResponse,
    WebSearchResult,
)

__all__ = [
    "BaseSearchClient",
    "NotConfiguredError",
    "RateLimitError",
    "SearchClientError",
    "OpenAILiteratureClient",
    "OpenAILiteratureClientError",
    "OpenAILiteratureRateLimitError",
    "LiteratureResponse",
    "WebSearchResult",
]
