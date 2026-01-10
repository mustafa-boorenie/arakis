"""Text embedder for RAG system.

Generates embeddings using OpenAI's text-embedding models with caching.
"""

import time
from typing import Any

import tiktoken
from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.models.rag import ChunkType, Embedding, TextChunk
from arakis.rag.cache import EmbeddingCacheStore
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class Embedder:
    """Generates and caches text embeddings using OpenAI."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        cache_dir: str = ".arakis_cache",
        batch_size: int = 100,
    ):
        """Initialize the embedder.

        Args:
            model: OpenAI embedding model to use
            cache_dir: Directory for embedding cache
            batch_size: Number of texts to embed in one API call
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.batch_size = batch_size
        self.cache = EmbeddingCacheStore(cache_dir)
        self.rate_limiter = get_openai_rate_limiter()
        self.encoding = tiktoken.get_encoding("cl100k_base")  # For token counting

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def create_chunks_from_paper(self, paper: Paper) -> list[TextChunk]:
        """Create text chunks from a paper.

        Args:
            paper: Paper to chunk

        Returns:
            List of text chunks
        """
        chunks = []

        # Title chunk
        if paper.title:
            chunks.append(
                TextChunk(
                    paper_id=paper.best_identifier,
                    chunk_type=ChunkType.TITLE,
                    text=paper.title,
                    metadata={
                        "year": paper.year,
                        "journal": paper.journal,
                        "authors": paper.authors[:3] if paper.authors else [],
                    },
                )
            )

        # Abstract chunk
        if paper.abstract:
            chunks.append(
                TextChunk(
                    paper_id=paper.best_identifier,
                    chunk_type=ChunkType.ABSTRACT,
                    text=paper.abstract,
                    metadata={
                        "year": paper.year,
                        "journal": paper.journal,
                    },
                )
            )

        return chunks

    @retry_with_exponential_backoff(max_retries=5, initial_delay=1.0, max_delay=30.0)
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using OpenAI API.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If API call fails after retries
        """
        await self.rate_limiter.wait()

        response = await self.client.embeddings.create(input=texts, model=self.model)

        # Extract vectors in order
        vectors = [item.embedding for item in response.data]
        return vectors

    async def embed_chunk(self, chunk: TextChunk, use_cache: bool = True) -> Embedding:
        """Embed a single text chunk.

        Args:
            chunk: Text chunk to embed
            use_cache: Whether to use cached embedding if available

        Returns:
            Embedding vector
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(chunk.chunk_id, chunk.text, self.model)
            if cached:
                return cached

        # Embed the text
        vectors = await self._embed_batch([chunk.text])
        vector = vectors[0]

        # Create embedding object
        embedding = Embedding(
            chunk_id=chunk.chunk_id,
            vector=vector,
            model=self.model,
            dimensions=len(vector),
        )

        # Cache it
        token_count = self._count_tokens(chunk.text)
        self.cache.put(chunk.chunk_id, chunk.text, embedding, token_count)

        return embedding

    async def embed_chunks(
        self, chunks: list[TextChunk], use_cache: bool = True
    ) -> list[Embedding]:
        """Embed multiple text chunks efficiently.

        Args:
            chunks: List of text chunks to embed
            use_cache: Whether to use cached embeddings

        Returns:
            List of embeddings
        """
        embeddings = []
        chunks_to_embed = []
        chunk_indices = []

        # Check cache for each chunk
        for i, chunk in enumerate(chunks):
            if use_cache:
                cached = self.cache.get(chunk.chunk_id, chunk.text, self.model)
                if cached:
                    embeddings.append((i, cached))
                    continue

            chunks_to_embed.append(chunk)
            chunk_indices.append(i)

        # Embed uncached chunks in batches
        if chunks_to_embed:
            for batch_start in range(0, len(chunks_to_embed), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(chunks_to_embed))
                batch = chunks_to_embed[batch_start:batch_end]

                # Extract texts
                texts = [chunk.text for chunk in batch]

                # Embed batch
                vectors = await self._embed_batch(texts)

                # Create and cache embeddings
                for chunk, vector in zip(batch, vectors):
                    embedding = Embedding(
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        model=self.model,
                        dimensions=len(vector),
                    )

                    # Cache it
                    token_count = self._count_tokens(chunk.text)
                    self.cache.put(chunk.chunk_id, chunk.text, embedding, token_count)

                    # Add to results
                    original_idx = chunk_indices[batch_start + batch.index(chunk)]
                    embeddings.append((original_idx, embedding))

                # Small delay between batches
                if batch_end < len(chunks_to_embed):
                    await self.rate_limiter.wait()

        # Sort by original index
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]

    async def embed_papers(
        self, papers: list[Paper], use_cache: bool = True
    ) -> dict[str, list[Embedding]]:
        """Embed all chunks from multiple papers.

        Args:
            papers: List of papers to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Dictionary mapping paper_id to list of embeddings
        """
        # Create all chunks
        all_chunks = []
        paper_chunk_counts = {}

        for paper in papers:
            chunks = self.create_chunks_from_paper(paper)
            paper_id = paper.best_identifier
            paper_chunk_counts[paper_id] = len(chunks)
            all_chunks.extend(chunks)

        # Embed all chunks
        all_embeddings = await self.embed_chunks(all_chunks, use_cache=use_cache)

        # Group by paper
        result = {}
        idx = 0
        for paper in papers:
            paper_id = paper.best_identifier
            count = paper_chunk_counts[paper_id]
            result[paper_id] = all_embeddings[idx : idx + count]
            idx += count

        return result

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost for embedding tokens.

        Args:
            token_count: Number of tokens to embed

        Returns:
            Estimated cost in USD
        """
        # text-embedding-3-small: $0.00002 per 1K tokens
        return (token_count / 1000) * 0.00002

    def get_cache_stats(self):
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        return self.cache.get_stats()
