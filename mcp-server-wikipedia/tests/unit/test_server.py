from unittest.mock import AsyncMock

import pytest

from mcp_server_wikipedia.wikipedia import (
    ArticleNotFoundError,
    WikipediaAPIError,
    WikipediaServiceError,
)

# Import helper functions from conftest
from tests.conftest import (
    _test_get_article,
    _test_get_links,
    _test_get_related_topics,
    _test_get_sections,
    _test_get_summary,
    _test_search_wikipedia,
)

# === Test Classes ===
# NOTE: TestAppLifespan and TestHelperFunctions were removed as they tested
# outdated server.py code that has been refactored into app.py with a different
# architecture using DependencyContainer instead of direct service passing


# --- Search Wikipedia Tests ---


class TestSearchWikipedia:
    """Test search wikipedia functionality."""

    @pytest.mark.asyncio
    async def test_search_wikipedia_successful(self):
        """Test successful Wikipedia search."""
        expected_results = ["Article 1", "Article 2", "Article 3"]
        mock_service = AsyncMock()
        mock_service.search.return_value = expected_results

        context = {"wikipedia_service": mock_service}
        result = await _test_search_wikipedia("test query", context)

        assert result["success"] is True
        assert result["data"] == expected_results
        mock_service.search.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_search_wikipedia_validation_error(self):
        """Test search with validation error."""
        mock_service = AsyncMock()
        mock_service.search.side_effect = WikipediaServiceError("Invalid query")

        context = {"wikipedia_service": mock_service}
        result = await _test_search_wikipedia("", context)

        assert result["success"] is False
        assert "Invalid query" in result["error"]

    @pytest.mark.asyncio
    async def test_search_wikipedia_api_error(self):
        """Test search with API error."""
        mock_service = AsyncMock()
        mock_service.search.side_effect = Exception("Connection failed")

        context = {"wikipedia_service": mock_service}
        result = await _test_search_wikipedia("test", context)

        assert result["success"] is False
        assert "Unexpected error" in result["error"]


# --- Get Article Tests ---


class TestGetArticle:
    """Test get article functionality."""

    @pytest.mark.asyncio
    async def test_get_article_successful(self):
        """Test successful article retrieval."""
        expected_article = {"title": "Test Article", "content": "Article content..."}
        mock_service = AsyncMock()
        mock_service.get_article.return_value = expected_article

        context = {"wikipedia_service": mock_service}
        result = await _test_get_article("Test Article", context)

        assert result["success"] is True
        assert result["data"] == expected_article
        mock_service.get_article.assert_called_once_with("Test Article")

    @pytest.mark.asyncio
    async def test_get_article_not_found(self):
        """Test article retrieval when article is not found."""
        mock_service = AsyncMock()
        mock_service.get_article.side_effect = ArticleNotFoundError(
            "Article not found: Nonexistent"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_article("Nonexistent", context)

        assert result["success"] is False
        assert "Article not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_article_api_error(self):
        """Test article retrieval with Wikipedia API error."""
        mock_service = AsyncMock()
        mock_service.get_article.side_effect = WikipediaAPIError(
            "API connection failed"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_article("Test Article", context)

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]


# --- Get Summary Tests ---


class TestGetSummary:
    """Test get summary functionality."""

    @pytest.mark.asyncio
    async def test_get_summary_successful(self):
        """Test successful summary retrieval."""
        expected_summary = "This is a test article summary."
        mock_service = AsyncMock()
        mock_service.get_summary.return_value = expected_summary

        context = {"wikipedia_service": mock_service}
        result = await _test_get_summary("Test Article", context)

        assert result["success"] is True
        assert result["data"] == expected_summary
        mock_service.get_summary.assert_called_once_with("Test Article")

    @pytest.mark.asyncio
    async def test_get_summary_article_not_found(self):
        """Test summary retrieval when article is not found."""
        mock_service = AsyncMock()
        mock_service.get_summary.side_effect = ArticleNotFoundError(
            "Article not found: Missing"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_summary("Missing", context)

        assert result["success"] is False
        assert "Article not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_summary_api_error(self):
        """Test summary retrieval with Wikipedia API error."""
        mock_service = AsyncMock()
        mock_service.get_summary.side_effect = WikipediaAPIError("Network timeout")

        context = {"wikipedia_service": mock_service}
        result = await _test_get_summary("Test Article", context)

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]


# --- Get Sections Tests ---


class TestGetSections:
    """Test get sections functionality."""

    @pytest.mark.asyncio
    async def test_get_sections_successful(self):
        """Test successful sections retrieval."""
        expected_sections = [
            "Introduction",
            "History",
            "Geography",
            "Culture",
            "References",
        ]
        mock_service = AsyncMock()
        mock_service.get_sections.return_value = expected_sections

        context = {"wikipedia_service": mock_service}
        result = await _test_get_sections("Test Article", context)

        assert result["success"] is True
        assert result["data"] == expected_sections
        mock_service.get_sections.assert_called_once_with("Test Article")

    @pytest.mark.asyncio
    async def test_get_sections_article_not_found(self):
        """Test sections retrieval when article is not found."""
        mock_service = AsyncMock()
        mock_service.get_sections.side_effect = ArticleNotFoundError(
            "Article not found: Missing"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_sections("Missing", context)

        assert result["success"] is False
        assert "Article not found: Missing" in result["error"]

    @pytest.mark.asyncio
    async def test_get_sections_api_error(self):
        """Test sections retrieval with API error."""
        mock_service = AsyncMock()
        mock_service.get_sections.side_effect = WikipediaAPIError("API error")

        context = {"wikipedia_service": mock_service}
        result = await _test_get_sections("Test Article", context)

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]


# --- Get Links Tests ---


class TestGetLinks:
    """Test get links functionality."""

    @pytest.mark.asyncio
    async def test_get_links_successful(self):
        """Test successful links retrieval."""
        expected_links = [
            "Related Article 1",
            "Related Article 2",
            "External Source",
            "Reference Link",
        ]
        mock_service = AsyncMock()
        mock_service.get_links.return_value = expected_links

        context = {"wikipedia_service": mock_service}
        result = await _test_get_links("Test Article", 10, context)

        assert result["success"] is True
        assert result["data"] == expected_links
        mock_service.get_links.assert_called_once_with("Test Article", 10)

    @pytest.mark.asyncio
    async def test_get_links_article_not_found(self):
        """Test links retrieval when article is not found."""
        mock_service = AsyncMock()
        mock_service.get_links.side_effect = ArticleNotFoundError(
            "Article not found: Unknown"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_links("Unknown", 10, context)

        assert result["success"] is False
        assert "Article not found: Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_get_links_api_error(self):
        """Test links retrieval with API error."""
        mock_service = AsyncMock()
        mock_service.get_links.side_effect = WikipediaAPIError("API error")

        context = {"wikipedia_service": mock_service}
        result = await _test_get_links("Test Article", 10, context)

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]


# --- Get Related Topics Tests ---


class TestGetRelatedTopics:
    """Test get related topics functionality."""

    @pytest.mark.asyncio
    async def test_get_related_topics_successful(self):
        """Test successful related topics retrieval."""
        expected_topics = ["Related Topic 1", "Related Topic 2", "Connected Subject"]
        mock_service = AsyncMock()
        mock_service.get_related_topics.return_value = expected_topics

        context = {"wikipedia_service": mock_service}
        result = await _test_get_related_topics("Test Article", 20, context)

        assert result["success"] is True
        assert result["data"] == expected_topics
        mock_service.get_related_topics.assert_called_once_with("Test Article", 20)

    @pytest.mark.asyncio
    async def test_get_related_topics_default_limit(self):
        """Test related topics retrieval with default limit."""
        expected_topics = ["Topic A", "Topic B"]
        mock_service = AsyncMock()
        mock_service.get_related_topics.return_value = expected_topics

        context = {"wikipedia_service": mock_service}
        result = await _test_get_related_topics("Test Article", 5, context)

        assert result["success"] is True
        assert result["data"] == expected_topics
        mock_service.get_related_topics.assert_called_once_with("Test Article", 5)

    @pytest.mark.asyncio
    async def test_get_related_topics_api_error(self):
        """Test related topics retrieval with API error."""
        mock_service = AsyncMock()
        mock_service.get_related_topics.side_effect = WikipediaAPIError("API error")

        context = {"wikipedia_service": mock_service}
        result = await _test_get_related_topics("Test Article", 5, context)

        assert result["success"] is False
        assert "Wikipedia API error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_related_topics_article_not_found(self):
        """Test related topics when article is not found."""
        mock_service = AsyncMock()
        mock_service.get_related_topics.side_effect = ArticleNotFoundError(
            "Article not found"
        )

        context = {"wikipedia_service": mock_service}
        result = await _test_get_related_topics("Nonexistent Article", 5, context)

        assert result["success"] is False
        assert "Article not found" in result["error"]
