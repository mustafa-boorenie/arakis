"""Document retriever for RAG system.

High-level interface for retrieving relevant literature context.
"""

import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

from arakis.models.paper import Paper
from arakis.models.rag import (
    ChunkType,
    RetrievalQuery,
    RetrievalResponse,
    RetrievalResult,
    TextChunk,
)
from arakis.rag.embedder import Embedder
from arakis.rag.vector_store import VectorStore


class Retriever:
    """Retrieves relevant documents using semantic similarity search."""

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        vector_store: Optional[VectorStore] = None,
        cache_dir: str = ".arakis_cache",
    ):
        """Initialize the retriever.

        Args:
            embedder: Embedder instance (creates default if None)
            vector_store: Vector store instance (creates default if None)
            cache_dir: Directory for caching
        """
        self.embedder = embedder or Embedder(cache_dir=cache_dir)
        self.vector_store = vector_store or VectorStore(dimension=1536)
        self.cache_dir = Path(cache_dir)

    async def index_papers(self, papers: list[Paper], show_progress: bool = False) -> int:
        """Index papers for retrieval.

        Args:
            papers: List of papers to index
            show_progress: Whether to show progress (for CLI)

        Returns:
            Number of chunks indexed
        """
        # Create chunks
        all_chunks = []
        for paper in papers:
            chunks = self.embedder.create_chunks_from_paper(paper)
            all_chunks.extend(chunks)

        if show_progress:
            print(f"Indexing {len(all_chunks)} chunks from {len(papers)} papers...")

        # Embed chunks (with caching)
        embeddings = await self.embedder.embed_chunks(all_chunks, use_cache=True)

        # Add to vector store
        self.vector_store.add_batch(all_chunks, embeddings)

        if show_progress:
            stats = self.embedder.get_cache_stats()
            print(f"✓ Indexed {len(all_chunks)} chunks")
            print(f"Cache: {stats.total_embeddings} embeddings, {stats.cache_size_bytes:,} bytes")

        return len(all_chunks)

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        """Retrieve relevant documents for a query.

        Args:
            query: Retrieval query

        Returns:
            Retrieval response with ranked results
        """
        start_time = time.time()

        # Embed the query
        query_chunk = TextChunk(
            paper_id="query",
            chunk_type=ChunkType.ABSTRACT,
            text=query.query_text,
        )
        query_embedding = await self.embedder.embed_chunk(query_chunk, use_cache=False)

        # Search vector store
        # Note: We search for more than top_k to allow filtering
        search_k = query.top_k * 3 if query.chunk_types or query.exclude_paper_ids else query.top_k
        raw_results = self.vector_store.search(query_embedding.vector, top_k=search_k)

        # Convert distances to similarity scores (inverse of L2 distance)
        # For L2 distance, closer = lower distance, so we use 1/(1+distance)
        results = []
        seen_papers = set()

        for chunk, distance in raw_results:
            # Apply filters
            if query.chunk_types and chunk.chunk_type not in query.chunk_types:
                continue

            if chunk.paper_id in query.exclude_paper_ids:
                continue

            # Convert distance to similarity score (0-1, higher = more similar)
            score = 1.0 / (1.0 + distance)

            # Apply minimum score filter
            if query.min_score is not None and score < query.min_score:
                continue

            # Apply diversity (skip if paper already seen and diversity enabled)
            if query.diversity_weight > 0.5 and chunk.paper_id in seen_papers:
                continue

            seen_papers.add(chunk.paper_id)

            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    rank=len(results) + 1,
                )
            )

            # Stop when we have enough results
            if len(results) >= query.top_k:
                break

        elapsed_ms = int((time.time() - start_time) * 1000)

        return RetrievalResponse(
            query=query,
            results=results,
            total_candidates=len(raw_results),
            search_time_ms=elapsed_ms,
            model_used=self.embedder.model,
        )

    async def retrieve_simple(
        self, query_text: str, top_k: int = 10, diversity: bool = True
    ) -> list[RetrievalResult]:
        """Simple retrieval interface.

        Args:
            query_text: Query text
            top_k: Number of results
            diversity: Whether to enforce paper diversity

        Returns:
            List of retrieval results
        """
        query = RetrievalQuery(
            query_text=query_text,
            top_k=top_k,
            diversity_weight=0.8 if diversity else 0.0,
        )
        response = await self.retrieve(query)
        return response.results

    def save(self, save_dir: Optional[Union[Path, str]] = None):
        """Save the retriever state to disk.

        Args:
            save_dir: Directory to save to (uses cache_dir if None)
        """
        save_dir = Path(save_dir) if save_dir else self.cache_dir / "retriever"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save vector store
        self.vector_store.save(save_dir / "vector_store")

    @classmethod
    def load(cls, load_dir: Union[Path, str], cache_dir: str = ".arakis_cache") -> "Retriever":
        """Load a saved retriever.

        Args:
            load_dir: Directory to load from
            cache_dir: Cache directory for embedder

        Returns:
            Loaded retriever
        """
        load_dir = Path(load_dir)

        # Load vector store
        vector_store = VectorStore.load(load_dir / "vector_store")

        # Create embedder (will use cache)
        embedder = Embedder(cache_dir=cache_dir)

        return cls(embedder=embedder, vector_store=vector_store, cache_dir=cache_dir)

    def get_stats(self) -> dict:
        """Get retriever statistics.

        Returns:
            Dictionary with statistics
        """
        vector_stats = self.vector_store.get_stats()
        cache_stats = self.embedder.get_cache_stats()

        return {
            "vector_store": vector_stats,
            "embedding_cache": {
                "total_embeddings": cache_stats.total_embeddings,
                "cache_size_bytes": cache_stats.cache_size_bytes,
                "total_tokens_embedded": cache_stats.total_tokens_embedded,
                "models_used": cache_stats.models_used,
            },
        }

    def clear(self):
        """Clear the vector store (keeps embedding cache)."""
        self.vector_store.clear()
