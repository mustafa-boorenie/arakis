"""Tests for RAG system components."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from arakis.models.paper import Paper
from arakis.models.rag import ChunkType, RetrievalQuery, TextChunk
from arakis.rag import Embedder, Retriever, VectorStore
from arakis.rag.cache import EmbeddingCacheStore


@pytest.fixture
def sample_papers():
    """Create sample papers for testing."""
    return [
        Paper(
            id="test1",
            title="Machine Learning in Healthcare",
            abstract="This paper discusses machine learning applications in healthcare settings.",
            authors=["Smith, J.", "Jones, A."],
            year=2020,
            journal="Medical AI",
            doi="10.1234/test1",
        ),
        Paper(
            id="test2",
            title="Deep Learning for Medical Diagnosis",
            abstract="Deep learning models can improve diagnostic accuracy in medical imaging.",
            authors=["Brown, K.", "Davis, L."],
            year=2021,
            journal="AI Medicine",
            doi="10.1234/test2",
        ),
        Paper(
            id="test3",
            title="Natural Language Processing in Clinical Notes",
            abstract="NLP techniques extract valuable information from electronic health records.",
            authors=["Wilson, M."],
            year=2022,
            journal="Clinical NLP",
            doi="10.1234/test3",
        ),
    ]


class TestEmbeddingCache:
    """Tests for embedding cache."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCacheStore(tmpdir)
            assert cache.db_path.exists()

    def test_cache_put_and_get(self):
        """Test storing and retrieving embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCacheStore(tmpdir)

            # Create dummy embedding
            from arakis.models.rag import Embedding
            from datetime import datetime

            chunk_id = "test_paper:title"
            text = "Test title"
            embedding = Embedding(
                chunk_id=chunk_id,
                vector=[0.1, 0.2, 0.3] * 512,  # 1536 dimensions
                model="text-embedding-3-small",
                dimensions=1536,
            )

            # Store in cache
            cache.put(chunk_id, text, embedding, token_count=10)

            # Retrieve from cache
            retrieved = cache.get(chunk_id, text, "text-embedding-3-small")

            assert retrieved is not None
            assert retrieved.chunk_id == chunk_id
            assert retrieved.model == embedding.model
            assert len(retrieved.vector) == len(embedding.vector)

    def test_cache_invalidation_on_text_change(self):
        """Test that cache is invalidated when text changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCacheStore(tmpdir)

            from arakis.models.rag import Embedding

            chunk_id = "test_paper:abstract"
            text1 = "Original text"
            text2 = "Modified text"

            embedding = Embedding(
                chunk_id=chunk_id,
                vector=[0.1] * 1536,
                model="test-model",
                dimensions=1536,
            )

            # Store with original text
            cache.put(chunk_id, text1, embedding, token_count=5)

            # Try to retrieve with modified text (should fail)
            retrieved = cache.get(chunk_id, text2, "test-model")
            assert retrieved is None

            # Retrieve with original text (should succeed)
            retrieved = cache.get(chunk_id, text1, "test-model")
            assert retrieved is not None

    def test_cache_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCacheStore(tmpdir)

            from arakis.models.rag import Embedding

            # Add some embeddings
            for i in range(5):
                embedding = Embedding(
                    chunk_id=f"paper_{i}:title",
                    vector=[0.1] * 1536,
                    model="test-model",
                    dimensions=1536,
                )
                cache.put(f"paper_{i}:title", f"Title {i}", embedding, token_count=10)

            stats = cache.get_stats()
            assert stats.total_embeddings == 5
            assert stats.total_tokens_embedded == 50


class TestVectorStore:
    """Tests for vector store."""

    def test_vector_store_initialization(self):
        """Test vector store initialization."""
        store = VectorStore(dimension=1536)
        assert store.size == 0
        assert store.dimension == 1536

    def test_add_and_search(self):
        """Test adding vectors and searching."""
        from arakis.models.rag import Embedding

        store = VectorStore(dimension=128)  # Small dimension for testing

        # Create test chunks and embeddings
        chunks = [
            TextChunk(
                paper_id="paper1",
                chunk_type=ChunkType.TITLE,
                text="Machine learning in healthcare",
            ),
            TextChunk(
                paper_id="paper2",
                chunk_type=ChunkType.TITLE,
                text="Deep learning for diagnosis",
            ),
        ]

        embeddings = [
            Embedding(chunk_id="paper1:title", vector=[0.1] * 128, model="test", dimensions=128),
            Embedding(chunk_id="paper2:title", vector=[0.9] * 128, model="test", dimensions=128),
        ]

        # Add to store
        store.add_batch(chunks, embeddings)
        assert store.size == 2

        # Search with query similar to first embedding
        query = [0.11] * 128
        results = store.search(query, top_k=2)

        assert len(results) == 2
        assert results[0][0].paper_id == "paper1"  # Closest match
        assert results[0][1] < results[1][1]  # First result has lower distance

    def test_save_and_load(self):
        """Test saving and loading vector store."""
        from arakis.models.rag import Embedding

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate store
            store = VectorStore(dimension=128)
            chunk = TextChunk(
                paper_id="test",
                chunk_type=ChunkType.ABSTRACT,
                text="Test abstract",
            )
            embedding = Embedding(
                chunk_id="test:abstract",
                vector=[0.5] * 128,
                model="test",
                dimensions=128,
            )
            store.add(chunk, embedding)

            # Save
            store.save(tmpdir)

            # Load
            loaded_store = VectorStore.load(tmpdir)
            assert loaded_store.size == 1
            assert loaded_store.dimension == 128
            assert "test:abstract" in loaded_store.chunks


class TestEmbedder:
    """Tests for embedder."""

    @pytest.mark.asyncio
    async def test_create_chunks_from_paper(self, sample_papers):
        """Test chunk creation from papers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Embedder(cache_dir=tmpdir)
            paper = sample_papers[0]

            chunks = embedder.create_chunks_from_paper(paper)

            assert len(chunks) == 2  # Title + Abstract
            assert chunks[0].chunk_type == ChunkType.TITLE
            assert chunks[1].chunk_type == ChunkType.ABSTRACT
            assert chunks[0].text == paper.title
            assert chunks[1].text == paper.abstract

    @pytest.mark.asyncio
    async def test_embed_chunk_with_mock(self):
        """Test embedding a chunk with mocked API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Embedder(cache_dir=tmpdir)

            chunk = TextChunk(
                paper_id="test",
                chunk_type=ChunkType.TITLE,
                text="Test title",
            )

            # Mock the OpenAI API call
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

            with patch.object(embedder.client.embeddings, "create", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response

                embedding = await embedder.embed_chunk(chunk, use_cache=False)

                assert embedding.chunk_id == "test:title"
                assert len(embedding.vector) == 1536
                assert embedding.model == "text-embedding-3-small"
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_chunk_uses_cache(self):
        """Test that embedding uses cache on second call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Embedder(cache_dir=tmpdir)

            chunk = TextChunk(
                paper_id="test",
                chunk_type=ChunkType.TITLE,
                text="Test title",
            )

            # Mock the OpenAI API call
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

            with patch.object(embedder.client.embeddings, "create", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response

                # First call (should hit API)
                embedding1 = await embedder.embed_chunk(chunk, use_cache=True)
                assert mock_create.call_count == 1

                # Second call (should use cache)
                embedding2 = await embedder.embed_chunk(chunk, use_cache=True)
                assert mock_create.call_count == 1  # No additional call

                assert embedding1.vector == embedding2.vector

    def test_cost_estimation(self):
        """Test cost estimation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Embedder(cache_dir=tmpdir)

            # 1000 tokens should cost $0.00002
            cost = embedder.estimate_cost(1000)
            assert cost == pytest.approx(0.00002, rel=1e-6)

            # 100,000 tokens should cost $0.002
            cost = embedder.estimate_cost(100000)
            assert cost == pytest.approx(0.002, rel=1e-6)


class TestRetriever:
    """Tests for retriever."""

    @pytest.mark.asyncio
    async def test_index_and_retrieve_with_mock(self, sample_papers):
        """Test indexing and retrieval with mocked embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = Retriever(cache_dir=tmpdir)

            # Mock embeddings
            def mock_embedding_vector(text):
                # Create deterministic embeddings based on text length
                base = hash(text) % 100 / 100.0
                return [base + i * 0.001 for i in range(1536)]

            mock_response = MagicMock()

            async def mock_create_fn(*args, **kwargs):
                texts = kwargs.get("input", [])
                mock_response.data = [
                    MagicMock(embedding=mock_embedding_vector(text)) for text in texts
                ]
                return mock_response

            with patch.object(
                retriever.embedder.client.embeddings, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.side_effect = mock_create_fn

                # Index papers
                count = await retriever.index_papers(sample_papers[:2])
                assert count == 4  # 2 papers × 2 chunks each

                # Retrieve
                query = RetrievalQuery(
                    query_text="machine learning healthcare",
                    top_k=3,
                )
                response = await retriever.retrieve(query)

                assert len(response.results) > 0
                assert response.model_used == "text-embedding-3-small"
                assert response.search_time_ms > 0

    @pytest.mark.asyncio
    async def test_retriever_diversity(self, sample_papers):
        """Test diversity filtering in retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = Retriever(cache_dir=tmpdir)

            # Mock embeddings
            async def mock_create_fn(*args, **kwargs):
                texts = kwargs.get("input", [])
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[0.5] * 1536) for _ in texts]
                return mock_response

            with patch.object(
                retriever.embedder.client.embeddings, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.side_effect = mock_create_fn

                # Index papers
                await retriever.index_papers(sample_papers)

                # High diversity should limit results per paper
                query = RetrievalQuery(
                    query_text="test query",
                    top_k=10,
                    diversity_weight=0.9,
                )
                response = await retriever.retrieve(query)

                # Each paper should appear at most once
                paper_ids = [r.chunk.paper_id for r in response.results]
                assert len(paper_ids) == len(set(paper_ids))

    def test_retriever_save_and_load(self):
        """Test saving and loading retriever."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = Retriever(cache_dir=tmpdir)

            # Add some data to vector store
            from arakis.models.rag import Embedding

            chunk = TextChunk(
                paper_id="test",
                chunk_type=ChunkType.TITLE,
                text="Test",
            )
            embedding = Embedding(
                chunk_id="test:title",
                vector=[0.1] * 1536,
                model="test",
                dimensions=1536,
            )
            retriever.vector_store.add(chunk, embedding)

            # Save
            save_path = Path(tmpdir) / "saved_retriever"
            retriever.save(save_path)

            # Load
            loaded = Retriever.load(save_path, cache_dir=tmpdir)
            assert loaded.vector_store.size == 1
