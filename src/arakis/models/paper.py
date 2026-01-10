from __future__ import annotations
"""Data models for papers and authors."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PaperSource(str, Enum):
    """Source database for a paper."""

    PUBMED = "pubmed"
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    GOOGLE_SCHOLAR = "google_scholar"
    EMBASE = "embase"


@dataclass
class Author:
    """Author information."""

    name: str
    affiliation: str | None = None
    orcid: str | None = None

    def __str__(self) -> str:
        return self.name


@dataclass
class Paper:
    """Normalized paper representation from any database."""

    # Identifiers
    id: str  # Internal unique ID
    doi: str | None = None
    pmid: str | None = None  # PubMed ID
    pmcid: str | None = None  # PubMed Central ID
    arxiv_id: str | None = None
    s2_id: str | None = None  # Semantic Scholar ID
    openalex_id: str | None = None

    # Core metadata
    title: str = ""
    abstract: str | None = None
    authors: list[Author] = field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    publication_date: datetime | None = None

    # Source tracking
    source: PaperSource = PaperSource.PUBMED
    source_url: str | None = None

    # Full text access
    pdf_url: str | None = None
    open_access: bool = False

    # Full text extraction
    full_text: str | None = None
    full_text_extracted_at: datetime | None = None
    text_extraction_method: str | None = None  # "pymupdf", "pdfplumber", "none"
    text_quality_score: float | None = None  # 0-1 quality score

    # Additional metadata
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)  # PubMed MeSH
    publication_types: list[str] = field(default_factory=list)
    citation_count: int | None = None

    # Raw API response for debugging
    raw_data: dict[str, Any] = field(default_factory=dict)

    # Processing metadata
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    duplicate_of: str | None = None  # ID of primary if this is a duplicate

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Paper):
            return False
        return self.id == other.id

    @property
    def authors_string(self) -> str:
        """Return authors as comma-separated string."""
        return ", ".join(str(a) for a in self.authors)

    @property
    def has_abstract(self) -> bool:
        """Check if paper has a non-empty abstract."""
        return bool(self.abstract and self.abstract.strip())

    @property
    def best_identifier(self) -> str:
        """Return the best available identifier for deduplication."""
        return self.doi or self.pmid or self.s2_id or self.openalex_id or self.id

    @property
    def has_full_text(self) -> bool:
        """Check if paper has extracted full text."""
        return bool(self.full_text and len(self.full_text.strip()) > 100)

    @property
    def text_length(self) -> int:
        """Return character count of full text."""
        return len(self.full_text) if self.full_text else 0


@dataclass
class SearchResult:
    """Result from a single database search."""

    query: str
    source: PaperSource
    papers: list[Paper]
    total_available: int  # Total papers available (may be more than returned)
    execution_time_ms: int = 0

    @property
    def count(self) -> int:
        return len(self.papers)


@dataclass
class PRISMAFlow:
    """PRISMA flow statistics for systematic review reporting."""

    # Identification
    records_identified: dict[str, int] = field(default_factory=dict)  # Per database
    duplicates_removed: int = 0

    # Screening
    records_screened: int = 0
    records_excluded: int = 0

    # Eligibility
    full_text_assessed: int = 0
    full_text_excluded: int = 0
    exclusion_reasons: dict[str, int] = field(default_factory=dict)

    # Included
    studies_included: int = 0

    @property
    def total_identified(self) -> int:
        return sum(self.records_identified.values())

    @property
    def after_dedup(self) -> int:
        return self.total_identified - self.duplicates_removed
