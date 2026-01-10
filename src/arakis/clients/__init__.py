"""Clients package."""

from arakis.clients.base import (
    BaseSearchClient,
    NotConfiguredError,
    RateLimitError,
    SearchClientError,
)

__all__ = [
    "BaseSearchClient",
    "NotConfiguredError",
    "RateLimitError",
    "SearchClientError",
]
