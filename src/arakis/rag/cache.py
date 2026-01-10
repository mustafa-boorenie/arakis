"""Persistent cache for embeddings.

Caches embeddings to disk to avoid re-embedding the same text.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from arakis.models.rag import Embedding, EmbeddingCache, EmbeddingStats


class EmbeddingCacheStore:
    """SQLite-based persistent cache for embeddings."""

    def __init__(self, cache_dir: Union[Path, str] = ".arakis_cache"):
        """Initialize the cache store.

        Args:
            cache_dir: Directory to store cache database
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "embeddings.db"
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    embedding_hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    token_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hash_model
                ON embeddings(embedding_hash, model)
                """
            )
            conn.commit()

    def _hash_text(self, text: str) -> str:
        """Generate hash of text for cache lookup.

        Args:
            text: Text to hash

        Returns:
            SHA256 hash of the text
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, chunk_id: str, text: str, model: str) -> Optional[Embedding]:
        """Get cached embedding if available.

        Args:
            chunk_id: Chunk identifier
            text: Text content (for hash verification)
            model: Model name

        Returns:
            Cached embedding or None if not found/invalid
        """
        text_hash = self._hash_text(text)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT vector, dimensions, created_at
                FROM embeddings
                WHERE chunk_id = ? AND embedding_hash = ? AND model = ?
                """,
                (chunk_id, text_hash, model),
            )
            row = cursor.fetchone()

        if not row:
            return None

        vector_json, dimensions, created_at_str = row
        vector = json.loads(vector_json)
        created_at = datetime.fromisoformat(created_at_str)

        return Embedding(
            chunk_id=chunk_id,
            vector=vector,
            model=model,
            dimensions=dimensions,
            created_at=created_at,
        )

    def put(self, chunk_id: str, text: str, embedding: Embedding, token_count: int):
        """Store embedding in cache.

        Args:
            chunk_id: Chunk identifier
            text: Original text (for hash)
            embedding: Embedding to cache
            token_count: Number of tokens in the text
        """
        text_hash = self._hash_text(text)
        vector_json = json.dumps(embedding.vector)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings
                (chunk_id, embedding_hash, model, vector, dimensions, token_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    text_hash,
                    embedding.model,
                    vector_json,
                    embedding.dimensions,
                    token_count,
                    embedding.created_at.isoformat(),
                ),
            )
            conn.commit()

    def get_metadata(self, chunk_id: str) -> Optional[EmbeddingCache]:
        """Get cache metadata for a chunk.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Cache metadata or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT embedding_hash, model, token_count, created_at
                FROM embeddings
                WHERE chunk_id = ?
                """,
                (chunk_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        embedding_hash, model, token_count, created_at_str = row
        created_at = datetime.fromisoformat(created_at_str)

        return EmbeddingCache(
            chunk_id=chunk_id,
            embedding_hash=embedding_hash,
            model=model,
            created_at=created_at,
            token_count=token_count,
        )

    def get_stats(self) -> EmbeddingStats:
        """Get cache statistics.

        Returns:
            Statistics about cached embeddings
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get counts and token totals
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(token_count) as total_tokens,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM embeddings
                """
            )
            row = cursor.fetchone()
            total, total_tokens, oldest_str, newest_str = row

            # Get unique models
            cursor = conn.execute("SELECT DISTINCT model FROM embeddings")
            models = [row[0] for row in cursor.fetchall()]

        # Get cache file size
        cache_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        oldest = datetime.fromisoformat(oldest_str) if oldest_str else None
        newest = datetime.fromisoformat(newest_str) if newest_str else None

        return EmbeddingStats(
            total_chunks=total,
            total_embeddings=total,
            cache_size_bytes=cache_size,
            models_used=models,
            oldest_embedding=oldest,
            newest_embedding=newest,
            total_tokens_embedded=total_tokens or 0,
        )

    def clear(self, model: Optional[str] = None):
        """Clear cache entries.

        Args:
            model: If specified, only clear embeddings for this model.
                   If None, clear all embeddings.
        """
        with sqlite3.connect(self.db_path) as conn:
            if model:
                conn.execute("DELETE FROM embeddings WHERE model = ?", (model,))
            else:
                conn.execute("DELETE FROM embeddings")
            conn.commit()

    def delete(self, chunk_id: str):
        """Delete a specific embedding from cache.

        Args:
            chunk_id: Chunk identifier to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM embeddings WHERE chunk_id = ?", (chunk_id,))
            conn.commit()
