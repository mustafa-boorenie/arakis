"""Retrieval sources package."""

from arakis.retrieval.sources.base import BaseRetrievalSource, RetrievalResult
from arakis.retrieval.sources.unpaywall import UnpaywallSource
from arakis.retrieval.sources.pmc import PMCSource
from arakis.retrieval.sources.arxiv import ArxivSource

__all__ = [
    "BaseRetrievalSource",
    "RetrievalResult",
    "UnpaywallSource",
    "PMCSource",
    "ArxivSource",
]
