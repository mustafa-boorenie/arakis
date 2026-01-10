from __future__ import annotations
"""Base class for paper retrieval sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from arakis.models.paper import Paper


class ContentType(str, Enum):
    """Type of content retrieved."""

    PDF = "pdf"
    HTML = "html"
    XML = "xml"
    TEXT = "text"


@dataclass
class RetrievalResult:
    """Result of a paper retrieval attempt."""

    success: bool
    paper_id: str
    source_name: str

    # Content info
    content_url: str | None = None
    content_type: ContentType | None = None
    content: bytes | None = None  # Actual content if downloaded

    # Metadata
    license: str | None = None
    version: str | None = None  # e.g., "published", "preprint", "accepted"

    # Error info
    error: str | None = None


class BaseRetrievalSource(ABC):
    """Abstract base for paper retrieval sources."""

    name: str

    @abstractmethod
    async def can_retrieve(self, paper: Paper) -> bool:
        """Check if this source can potentially retrieve the paper."""
        pass

    @abstractmethod
    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """
        Attempt to retrieve the paper.

        Args:
            paper: Paper to retrieve
            download: If True, download the actual content

        Returns:
            RetrievalResult with URL or content
        """
        pass
