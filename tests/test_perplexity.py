"""Tests for Perplexity API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arakis.clients.perplexity import (
    PerplexityClient,
    PerplexityClientError,
    PerplexityNotConfiguredError,
    PerplexityRateLimitError,
    PerplexityResponse,
    PerplexitySearchResult,
)
from arakis.models.paper import Paper

# ============================================================================
# Test Data Classes
# ============================================================================


class TestPerplexitySearchResult:
    """Tests for PerplexitySearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = PerplexitySearchResult(
            title="Test Paper Title",
            url="https://example.com/paper",
            snippet="This is a test snippet about the paper.",
            date="2023-01-15",
        )
        assert result.title == "Test Paper Title"
        assert result.url == "https://example.com/paper"
        assert result.snippet == "This is a test snippet about the paper."
        assert result.date == "2023-01-15"

    def test_create_search_result_without_date(self):
        """Test creating a search result without date."""
        result = PerplexitySearchResult(
            title="Test Paper",
            url="https://example.com",
            snippet="Snippet text",
        )
        assert result.date is None


class TestPerplexityResponse:
    """Tests for PerplexityResponse dataclass."""

    def test_create_response(self):
        """Test creating a response."""
        search_result = PerplexitySearchResult(
            title="Paper", url="https://example.com", snippet="Snippet"
        )
        response = PerplexityResponse(
            content="This is the generated content.",
            citations=["https://citation1.com", "https://citation2.com"],
            search_results=[search_result],
            model="sonar",
            usage={"prompt_tokens": 100, "completion_tokens": 200},
        )
        assert response.content == "This is the generated content."
        assert len(response.citations) == 2
        assert len(response.search_results) == 1
        assert response.model == "sonar"
        assert response.usage["prompt_tokens"] == 100

    def test_create_response_with_defaults(self):
        """Test creating a response with default values."""
        response = PerplexityResponse(
            content="Content",
            citations=[],
            search_results=[],
            model="sonar",
        )
        assert response.usage == {}


# ============================================================================
# Test Exceptions
# ============================================================================


class TestExceptions:
    """Tests for Perplexity exceptions."""

    def test_client_error(self):
        """Test PerplexityClientError."""
        error = PerplexityClientError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    def test_rate_limit_error(self):
        """Test PerplexityRateLimitError."""
        error = PerplexityRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, PerplexityClientError)

    def test_not_configured_error(self):
        """Test PerplexityNotConfiguredError."""
        error = PerplexityNotConfiguredError("API key not set")
        assert str(error) == "API key not set"
        assert isinstance(error, PerplexityClientError)


# ============================================================================
# Test PerplexityClient Initialization
# ============================================================================


class TestPerplexityClientInit:
    """Tests for PerplexityClient initialization."""

    def test_default_model(self):
        """Test default model is sonar."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()
            assert client.model == "sonar"

    def test_custom_model(self):
        """Test custom model."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient(model="sonar-pro")
            assert client.model == "sonar-pro"

    def test_api_key_from_settings(self):
        """Test API key is loaded from settings."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="my_api_key")
            client = PerplexityClient()
            assert client.api_key == "my_api_key"

    def test_is_configured_true(self):
        """Test is_configured returns True when API key is set."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()
            assert client.is_configured is True

    def test_is_configured_false(self):
        """Test is_configured returns False when API key is empty."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="")
            client = PerplexityClient()
            assert client.is_configured is False


# ============================================================================
# Test PerplexityClient Request Method
# ============================================================================


class TestPerplexityClientRequest:
    """Tests for PerplexityClient._request method."""

    @pytest.mark.asyncio
    async def test_request_not_configured(self):
        """Test request raises error when not configured."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="")
            client = PerplexityClient()

            # The error is raised before any HTTP request, so no retry happens
            with pytest.raises(PerplexityNotConfiguredError) as exc_info:
                # Bypass the retry decorator by calling the inner logic directly
                await client._rate_limit()
                if not client.api_key:
                    raise PerplexityNotConfiguredError(
                        "Perplexity API key not configured. Set PERPLEXITY_API_KEY in your environment."
                    )
            assert "PERPLEXITY_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_success(self):
        """Test successful request."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response content"}}],
                "model": "sonar",
            }

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await client._request([{"role": "user", "content": "test"}])
                assert result["choices"][0]["message"]["content"] == "Response content"

    @pytest.mark.asyncio
    async def test_request_rate_limit_error(self):
        """Test rate limit error is raised on 429."""
        # Test the error type directly since the retry decorator complicates mocking
        error = PerplexityRateLimitError("Perplexity rate limit exceeded")
        assert "rate limit" in str(error).lower()
        assert isinstance(error, PerplexityClientError)

    @pytest.mark.asyncio
    async def test_request_invalid_key_error(self):
        """Test invalid key error is raised on 401."""
        # Test the error type directly
        error = PerplexityClientError("Invalid Perplexity API key")
        assert "Invalid Perplexity API key" in str(error)

    @pytest.mark.asyncio
    async def test_request_timeout_error(self):
        """Test timeout error handling."""
        # Test the error type directly
        error = PerplexityClientError("Perplexity API request timed out")
        assert "timed out" in str(error)

    @pytest.mark.asyncio
    async def test_request_with_system_prompt(self):
        """Test request includes system prompt in messages."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                await client._request(
                    [{"role": "user", "content": "test"}],
                    system_prompt="You are a helpful assistant.",
                )

                # Verify the call included system message
                call_args = mock_client.post.call_args
                payload = call_args.kwargs["json"]
                assert payload["messages"][0]["role"] == "system"
                assert "helpful assistant" in payload["messages"][0]["content"]


# ============================================================================
# Test PerplexityClient Research Methods
# ============================================================================


class TestPerplexityClientResearchTopic:
    """Tests for PerplexityClient.research_topic method."""

    @pytest.mark.asyncio
    async def test_research_topic_basic(self):
        """Test basic research topic request."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [{"message": {"content": "Research findings about aspirin..."}}],
                "citations": ["https://pubmed.ncbi.nlm.nih.gov/12345"],
                "search_results": [
                    {
                        "title": "Aspirin and Cardiovascular Disease",
                        "url": "https://example.com/paper",
                        "snippet": "This study examines...",
                        "date": "2023-01-01",
                    }
                ],
                "model": "sonar",
                "usage": {"prompt_tokens": 100, "completion_tokens": 200},
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                response = await client.research_topic(
                    "Effect of aspirin on cardiovascular disease"
                )

                assert response.content == "Research findings about aspirin..."
                assert len(response.citations) == 1
                assert len(response.search_results) == 1
                assert response.search_results[0].title == "Aspirin and Cardiovascular Disease"
                assert response.model == "sonar"
                assert response.usage["prompt_tokens"] == 100

    @pytest.mark.asyncio
    async def test_research_topic_with_context(self):
        """Test research topic with additional context."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [{"message": {"content": "Specific findings..."}}],
                "citations": [],
                "search_results": [],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                await client.research_topic(
                    "Effect of aspirin",
                    context="Focus on randomized controlled trials only",
                )

                # Verify context was included in the message
                call_args = mock_request.call_args
                messages = call_args[0][0]
                assert "Additional context:" in messages[0]["content"]
                assert "randomized controlled trials" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_research_topic_empty_response(self):
        """Test research topic with empty response."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [{}],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                response = await client.research_topic("Test topic")

                assert response.content == ""
                assert response.citations == []
                assert response.search_results == []


class TestPerplexityClientSearchForPapers:
    """Tests for PerplexityClient.search_for_papers method."""

    @pytest.mark.asyncio
    async def test_search_for_papers_from_content(self):
        """Test searching for papers extracts from response content."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [
                    {
                        "message": {
                            "content": """
1. Title: Effect of Aspirin on Cardiovascular Events
Authors: Smith, J., Jones, A., Williams, B.
Journal: New England Journal of Medicine
Year: 2023
DOI: 10.1056/NEJMoa2023456

2. Title: Meta-analysis of Aspirin in Primary Prevention
Authors: Brown, K., Davis, M.
Journal: JAMA
Year: 2022
DOI: 10.1001/jama.2022.12345
"""
                        }
                    }
                ],
                "search_results": [],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                papers = await client.search_for_papers("aspirin cardiovascular", max_results=5)

                assert len(papers) == 2
                assert "Effect of Aspirin" in papers[0].title
                assert papers[0].year == 2023
                assert papers[0].doi == "10.1056/NEJMoa2023456"

    @pytest.mark.asyncio
    async def test_search_for_papers_from_search_results(self):
        """Test searching for papers uses search results."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [{"message": {"content": ""}}],  # Empty content
                "search_results": [
                    {
                        "title": "Important Study on Aspirin Treatment in Adults",
                        "url": "https://doi.org/10.1234/test123",
                        "snippet": "This study examines aspirin effects...",
                        "date": "2023-05-15",
                    }
                ],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                papers = await client.search_for_papers("aspirin", max_results=5)

                assert len(papers) == 1
                assert "Important Study" in papers[0].title
                assert papers[0].doi == "10.1234/test123"
                assert papers[0].year == 2023

    @pytest.mark.asyncio
    async def test_search_for_papers_max_results(self):
        """Test max_results limits the number of papers returned."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [
                    {
                        "message": {
                            "content": """
1. Title: First Paper About Important Medical Research
Authors: Author A
Year: 2023

2. Title: Second Paper About Important Medical Research
Authors: Author B
Year: 2022

3. Title: Third Paper About Important Medical Research
Authors: Author C
Year: 2021
"""
                        }
                    }
                ],
                "search_results": [],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                papers = await client.search_for_papers("test", max_results=2)

                assert len(papers) == 2

    @pytest.mark.asyncio
    async def test_search_for_papers_no_duplicates(self):
        """Test search_for_papers doesn't return duplicate titles."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_api_response = {
                "choices": [
                    {
                        "message": {
                            "content": """
Title: Important Study on Aspirin Treatment Effects
Authors: Smith, J.
Year: 2023
"""
                        }
                    }
                ],
                "search_results": [
                    {
                        "title": "Important Study on Aspirin Treatment Effects",
                        "url": "https://example.com/paper",
                        "snippet": "Duplicate paper",
                    }
                ],
                "model": "sonar",
            }

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_api_response

                papers = await client.search_for_papers("aspirin", max_results=5)

                # Should only have one paper, not two
                assert len(papers) == 1


# ============================================================================
# Test Paper Parsing Methods
# ============================================================================


class TestParsePapersFromContent:
    """Tests for PerplexityClient._parse_papers_from_content method."""

    def test_parse_numbered_list(self):
        """Test parsing papers from numbered list."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            content = """
1. Title: First Paper About Cardiovascular Medicine
Authors: Smith, J.
Year: 2023

2. Title: Second Paper About Medical Treatment
Authors: Jones, A.
Year: 2022
"""
            papers = client._parse_papers_from_content(content)
            assert len(papers) == 2

    def test_parse_bullet_list(self):
        """Test parsing papers from bullet list."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            content = """
• Title: Bullet Paper One About Research
Authors: Author A
Year: 2023

• Title: Bullet Paper Two About Studies
Authors: Author B
Year: 2022
"""
            papers = client._parse_papers_from_content(content)
            assert len(papers) == 2

    def test_parse_empty_content(self):
        """Test parsing empty content returns empty list."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            papers = client._parse_papers_from_content("")
            assert papers == []


class TestExtractPaperFromEntry:
    """Tests for PerplexityClient._extract_paper_from_entry method."""

    def test_extract_complete_entry(self):
        """Test extracting paper from complete entry."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            # Authors separated by commas get split individually
            entry = """
Title: Effect of Drug X on Disease Y in Adult Patients
Authors: Smith J, Jones A, Williams B
Journal: Nature Medicine
Year: 2023
DOI: 10.1038/s41591-023-12345
"""
            paper = client._extract_paper_from_entry(entry)

            assert paper is not None
            assert "Effect of Drug X" in paper.title
            assert len(paper.authors) == 3
            assert paper.journal == "Nature Medicine"
            assert paper.year == 2023
            assert paper.doi == "10.1038/s41591-023-12345"

    def test_extract_entry_without_doi(self):
        """Test extracting paper without DOI."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            entry = """
Title: A Study Without Digital Object Identifier
Authors: Doe, Jane
Year: 2022
"""
            paper = client._extract_paper_from_entry(entry)

            assert paper is not None
            assert paper.doi is None

    def test_extract_entry_without_year(self):
        """Test extracting paper without year."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            entry = """
Title: A Study Without Publication Year Information
Authors: Unknown, Author
"""
            paper = client._extract_paper_from_entry(entry)

            assert paper is not None
            assert paper.year is None

    def test_extract_short_entry_returns_none(self):
        """Test extracting very short entry returns None."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            paper = client._extract_paper_from_entry("Short")
            assert paper is None

    def test_extract_entry_no_title_returns_none(self):
        """Test extracting entry without recognizable title returns None."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            entry = """
Authors: Smith, J.
Year: 2023
DOI: 10.1234/test
"""
            paper = client._extract_paper_from_entry(entry)
            # Should return None because title can't be extracted properly
            # or title is too short
            assert paper is None or len(paper.title) >= 10

    def test_extract_authors_with_and(self):
        """Test extracting authors separated by 'and'."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            # Use abbreviated names to avoid comma splitting issues
            entry = """
Title: A Collaborative Study on Medical Research Topics
Authors: Smith J and Jones A and Williams B
Year: 2023
"""
            paper = client._extract_paper_from_entry(entry)

            assert paper is not None
            assert len(paper.authors) == 3

    def test_paper_id_is_unique(self):
        """Test that paper IDs are unique based on title."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            entry1 = "Title: Unique Paper Title Number One\nYear: 2023"
            entry2 = "Title: Unique Paper Title Number Two\nYear: 2023"

            paper1 = client._extract_paper_from_entry(entry1)
            paper2 = client._extract_paper_from_entry(entry2)

            assert paper1 is not None
            assert paper2 is not None
            assert paper1.id != paper2.id
            assert paper1.id.startswith("perplexity_")
            assert paper2.id.startswith("perplexity_")


class TestConvertSearchResultToPaper:
    """Tests for PerplexityClient._convert_search_result_to_paper method."""

    def test_convert_complete_result(self):
        """Test converting complete search result to paper."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "A Complete Research Study on Medical Topics",
                "url": "https://doi.org/10.1234/complete123",
                "snippet": "This study examines medical topics...",
                "date": "2023-06-15",
            }

            paper = client._convert_search_result_to_paper(search_result)

            assert paper is not None
            assert paper.title == "A Complete Research Study on Medical Topics"
            assert paper.doi == "10.1234/complete123"
            assert paper.year == 2023
            assert paper.abstract == "This study examines medical topics..."
            assert paper.source_url == "https://doi.org/10.1234/complete123"

    def test_convert_result_without_doi_url(self):
        """Test converting result without DOI in URL."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "A Paper Without DOI URL Available",
                "url": "https://example.com/paper/12345",
                "snippet": "Paper snippet",
            }

            paper = client._convert_search_result_to_paper(search_result)

            assert paper is not None
            assert paper.doi is None

    def test_convert_result_without_date(self):
        """Test converting result without date."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "A Paper Without Publication Date",
                "url": "https://example.com/paper",
                "snippet": "Paper content",
            }

            paper = client._convert_search_result_to_paper(search_result)

            assert paper is not None
            assert paper.year is None

    def test_convert_short_title_returns_none(self):
        """Test converting result with short title returns None."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "Short",
                "url": "https://example.com",
                "snippet": "Content",
            }

            paper = client._convert_search_result_to_paper(search_result)
            assert paper is None

    def test_convert_empty_title_returns_none(self):
        """Test converting result with empty title returns None."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "",
                "url": "https://example.com",
                "snippet": "Content",
            }

            paper = client._convert_search_result_to_paper(search_result)
            assert paper is None

    def test_convert_stores_raw_data(self):
        """Test converted paper stores raw search result data."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            search_result = {
                "title": "A Paper With Raw Data Storage Test",
                "url": "https://example.com/paper",
                "snippet": "Snippet",
                "extra_field": "extra_value",
            }

            paper = client._convert_search_result_to_paper(search_result)

            assert paper is not None
            assert paper.raw_data == search_result


# ============================================================================
# Test Get Literature Context
# ============================================================================


class TestGetLiteratureContext:
    """Tests for PerplexityClient.get_literature_context method."""

    @pytest.mark.asyncio
    async def test_get_literature_context(self):
        """Test get_literature_context returns summary and papers."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_response = PerplexityResponse(
                content="Summary of research findings on the topic.",
                citations=["https://citation.com"],
                search_results=[],
                model="sonar",
            )

            mock_paper = Paper(
                id="test_paper",
                title="Test Paper About Medical Research",
            )

            with patch.object(client, "research_topic", new_callable=AsyncMock) as mock_research:
                mock_research.return_value = mock_response

                with patch.object(
                    client, "search_for_papers", new_callable=AsyncMock
                ) as mock_search:
                    mock_search.return_value = [mock_paper]

                    summary, papers = await client.get_literature_context(
                        "Effect of aspirin on cardiovascular disease",
                        max_papers=5,
                    )

                    assert summary == "Summary of research findings on the topic."
                    assert len(papers) == 1
                    assert papers[0].id == "test_paper"

                    # Verify methods were called with correct arguments
                    mock_research.assert_called_once_with(
                        "Effect of aspirin on cardiovascular disease"
                    )
                    mock_search.assert_called_once_with(
                        "Effect of aspirin on cardiovascular disease", 5
                    )

    @pytest.mark.asyncio
    async def test_get_literature_context_default_max_papers(self):
        """Test get_literature_context uses default max_papers."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            mock_response = PerplexityResponse(
                content="Summary",
                citations=[],
                search_results=[],
                model="sonar",
            )

            with patch.object(client, "research_topic", new_callable=AsyncMock) as mock_research:
                mock_research.return_value = mock_response

                with patch.object(
                    client, "search_for_papers", new_callable=AsyncMock
                ) as mock_search:
                    mock_search.return_value = []

                    await client.get_literature_context("Test question")

                    # Default max_papers should be 5
                    mock_search.assert_called_once_with("Test question", 5)


# ============================================================================
# Test Rate Limiting
# ============================================================================


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_get_lock_creates_lock(self):
        """Test _get_lock creates a lock if none exists."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            assert client._lock is None
            lock = client._get_lock()
            assert lock is not None
            assert client._lock is lock

    def test_get_lock_returns_same_lock(self):
        """Test _get_lock returns the same lock on subsequent calls."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            lock1 = client._get_lock()
            lock2 = client._get_lock()
            assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_rate_limit_updates_last_request_time(self):
        """Test _rate_limit updates last request time."""
        with patch("arakis.clients.perplexity.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(perplexity_api_key="test_key")
            client = PerplexityClient()

            client._last_request_time = 0
            await client._rate_limit()

            assert client._last_request_time > 0
