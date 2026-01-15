"""Retrieval sources package."""

from arakis.retrieval.sources.arxiv import ArxivSource
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.retrieval.sources.biorxiv import BiorxivSource
from arakis.retrieval.sources.core import CORESource
from arakis.retrieval.sources.crossref import CrossrefSource
from arakis.retrieval.sources.europe_pmc import EuropePMCSource
from arakis.retrieval.sources.pmc import PMCSource
from arakis.retrieval.sources.semantic_scholar import SemanticScholarSource
from arakis.retrieval.sources.unpaywall import UnpaywallSource

__all__ = [
    "BaseRetrievalSource",
    "ContentType",
    "RetrievalResult",
    "ArxivSource",
    "BiorxivSource",
    "CORESource",
    "CrossrefSource",
    "EuropePMCSource",
    "PMCSource",
    "SemanticScholarSource",
    "UnpaywallSource",
]
