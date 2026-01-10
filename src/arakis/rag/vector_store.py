"""Vector store for embeddings using FAISS.

Stores and searches embedding vectors efficiently.
"""

import json
import pickle
from pathlib import Path
from typing import Any, Optional, Union

import faiss
import numpy as np

from arakis.models.rag import Embedding, TextChunk


class VectorStore:
    """FAISS-based vector store for similarity search."""

    def __init__(self, dimension: int = 1536, index_type: str = "flat"):
        """Initialize the vector store.

        Args:
            dimension: Dimension of embedding vectors (1536 for text-embedding-3-small)
            index_type: Type of FAISS index ('flat' for exact search, 'ivf' for approximate)
        """
        self.dimension = dimension
        self.index_type = index_type

        # Initialize FAISS index
        if index_type == "flat":
            # Exact search (L2 distance)
            self.index = faiss.IndexFlatL2(dimension)
        elif index_type == "ivf":
            # Approximate search with inverted file index
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
        else:
            raise ValueError(f"Unknown index type: {index_type}")

        # Store metadata (chunk_id -> TextChunk)
        self.chunks: dict[str, TextChunk] = {}
        # Map index position to chunk_id
        self.id_map: list[str] = []

    def add(self, chunk: TextChunk, embedding: Embedding):
        """Add a single embedding to the store.

        Args:
            chunk: Text chunk metadata
            embedding: Embedding vector
        """
        self.add_batch([chunk], [embedding])

    def add_batch(self, chunks: list[TextChunk], embeddings: list[Embedding]):
        """Add multiple embeddings to the store.

        Args:
            chunks: List of text chunks
            embeddings: List of corresponding embeddings
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        # Convert to numpy array
        vectors = np.array([emb.vector for emb in embeddings], dtype=np.float32)

        # Train index if needed (for IVF)
        if self.index_type == "ivf" and not self.index.is_trained:
            self.index.train(vectors)

        # Add to index
        self.index.add(vectors)

        # Store metadata
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
            self.id_map.append(chunk.chunk_id)

    def search(
        self, query_vector: list[float], top_k: int = 10, min_distance: Optional[float] = None
    ) -> list[tuple[TextChunk, float]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            min_distance: Minimum distance threshold (filter out results with distance > threshold)

        Returns:
            List of (chunk, distance) tuples, sorted by distance (lower = more similar)
        """
        # Convert to numpy
        query = np.array([query_vector], dtype=np.float32)

        # Search
        distances, indices = self.index.search(query, top_k)

        # Convert to results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS uses -1 for empty slots
                continue

            if min_distance is not None and dist > min_distance:
                continue

            chunk_id = self.id_map[idx]
            chunk = self.chunks[chunk_id]
            results.append((chunk, float(dist)))

        return results

    def get_chunk(self, chunk_id: str) -> Optional[TextChunk]:
        """Get chunk by ID.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Text chunk or None if not found
        """
        return self.chunks.get(chunk_id)

    def remove(self, chunk_id: str):
        """Remove a chunk from the store.

        Note: FAISS doesn't support efficient removal, so this only removes from metadata.
        Consider rebuilding the index if you need to remove many items.

        Args:
            chunk_id: Chunk identifier to remove
        """
        if chunk_id in self.chunks:
            del self.chunks[chunk_id]

    def save(self, save_dir: Union[Path, str]):
        """Save the vector store to disk.

        Args:
            save_dir: Directory to save to
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(save_dir / "faiss.index"))

        # Save metadata
        with open(save_dir / "chunks.pkl", "wb") as f:
            pickle.dump(self.chunks, f)

        with open(save_dir / "id_map.json", "w") as f:
            json.dump(self.id_map, f)

        # Save config
        config = {
            "dimension": self.dimension,
            "index_type": self.index_type,
            "total_vectors": len(self.id_map),
        }
        with open(save_dir / "config.json", "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def load(cls, load_dir: Union[Path, str]) -> "VectorStore":
        """Load a vector store from disk.

        Args:
            load_dir: Directory to load from

        Returns:
            Loaded vector store
        """
        load_dir = Path(load_dir)

        # Load config
        with open(load_dir / "config.json") as f:
            config = json.load(f)

        # Create instance
        store = cls(dimension=config["dimension"], index_type=config["index_type"])

        # Load FAISS index
        store.index = faiss.read_index(str(load_dir / "faiss.index"))

        # Load metadata
        with open(load_dir / "chunks.pkl", "rb") as f:
            store.chunks = pickle.load(f)

        with open(load_dir / "id_map.json") as f:
            store.id_map = json.load(f)

        return store

    def clear(self):
        """Clear all vectors and metadata from the store."""
        # Reset index
        if self.index_type == "flat":
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)

        self.chunks = {}
        self.id_map = []

    @property
    def size(self) -> int:
        """Number of vectors in the store."""
        return len(self.id_map)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_vectors": self.size,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "is_trained": self.index.is_trained if self.index_type == "ivf" else True,
            "unique_papers": len(set(chunk.paper_id for chunk in self.chunks.values())),
        }
