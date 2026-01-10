"""RAG (Retrieval-Augmented Generation) data models.

Data structures for embedding, vector storage, and retrieval of literature context.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ChunkType(Enum):
    """Type of text chunk."""

    TITLE = "title"
    ABSTRACT = "abstract"
    KEY_FINDINGS = "key_findings"
    FULL_TEXT = "full_text"


@dataclass
class TextChunk:
    """A chunk of text from a paper for embedding."""

    paper_id: str
    chunk_type: ChunkType
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """Unique identifier for this chunk."""
        return f"{self.paper_id}:{self.chunk_type.value}"


@dataclass
class Embedding:
    """Vector embedding of a text chunk."""

    chunk_id: str
    vector: list[float]
    model: str  # e.g., "text-embedding-3-small"
    dimensions: int
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def vector_size(self) -> int:
        """Size of the embedding vector."""
        return len(self.vector)


@dataclass
class EmbeddingCache:
    """Cache metadata for embeddings."""

    chunk_id: str
    embedding_hash: str  # Hash of the text that was embedded
    model: str
    created_at: datetime
    token_count: int


@dataclass
class RetrievalResult:
    """A single retrieved document with relevance score."""

    chunk: TextChunk
    score: float  # Similarity score (higher = more relevant)
    rank: int  # Rank in the result set (1 = most relevant)


@dataclass
class RetrievalQuery:
    """Query for retrieving relevant documents."""

    query_text: str
    top_k: int = 10
    min_score: Optional[float] = None
    chunk_types: Optional[list[ChunkType]] = None  # Filter by chunk type
    exclude_paper_ids: list[str] = field(default_factory=list)  # Exclude specific papers
    diversity_weight: float = 0.0  # 0-1, higher = more diverse results


@dataclass
class RetrievalResponse:
    """Response from a retrieval query."""

    query: RetrievalQuery
    results: list[RetrievalResult]
    total_candidates: int  # Total documents searched
    search_time_ms: int
    model_used: str

    @property
    def paper_ids(self) -> list[str]:
        """Get unique paper IDs from results."""
        return list(dict.fromkeys([r.chunk.paper_id for r in self.results]))

    @property
    def avg_score(self) -> float:
        """Average relevance score of results."""
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


@dataclass
class EmbeddingStats:
    """Statistics about embeddings and cache."""

    total_chunks: int
    total_embeddings: int
    cache_size_bytes: int
    models_used: list[str]
    oldest_embedding: Optional[datetime]
    newest_embedding: Optional[datetime]
    total_tokens_embedded: int

    @property
    def cache_hit_rate(self) -> float:
        """Estimate cache hit rate (if total_chunks > total_embeddings)."""
        if self.total_embeddings == 0:
            return 0.0
        return 1.0 - (self.total_embeddings / max(self.total_chunks, self.total_embeddings))
