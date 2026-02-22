from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server_lurky.lurky.config import LurkyServiceConfig
from mcp_server_lurky.lurky.errors import (
    LurkyAPIError,
    LurkyAuthError,
    LurkyNotFoundError,
)
from mcp_server_lurky.lurky.models import MindMap, SearchResponse, SpaceDetails
from mcp_server_lurky.lurky.module import LurkyClient
from tests.unit.lurky.mocks import (
    MockHTTPResponse,
    MockLurkyHttpClient,
    build_discussions_list,
    build_mind_map,
    build_search_response,
    build_space_details,
)


@pytest.fixture
def lurky_client() -> LurkyClient:
    """Provide a LurkyClient with test configuration."""
    config = LurkyServiceConfig(
        api_key="test-api-key",
        base_url="https://api.lurky.app",
        timeout_seconds=10,
    )
    return LurkyClient(config)


def _patch_httpx_client(mock_client: MockLurkyHttpClient):
    """Create a context manager that patches httpx.AsyncClient."""
    return patch("httpx.AsyncClient", return_value=mock_client)


# =============================================================================
# Feature 1: Search Discussions
# =============================================================================


class TestSearchDiscussions:
    """Tests for search_discussions method."""

    @pytest.mark.asyncio
    async def test_search_discussions_success(self, lurky_client: LurkyClient):
        """Successful search returns SearchResponse with discussions."""
        payload = build_search_response(total=5)
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await lurky_client.search_discussions("bitcoin", limit=10, page=0)

        assert isinstance(result, SearchResponse)
        assert len(result.discussions) == 1
        assert result.total == 5
        assert result.discussions[0].title == "Test Discussion"
        assert len(mock_client.calls) == 1
        assert mock_client.calls[0]["params"]["search_term"] == "bitcoin"

    @pytest.mark.asyncio
    async def test_search_discussions_with_pagination(self, lurky_client: LurkyClient):
        """Search respects pagination parameters."""
        payload = build_search_response(page=2, limit=5)
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await lurky_client.search_discussions("crypto", limit=5, page=2)

        assert result.page == 2
        assert result.limit == 5
        assert mock_client.calls[0]["params"]["limit"] == 5
        assert mock_client.calls[0]["params"]["page"] == 2


# =============================================================================
# Feature 2: Get Space Details
# =============================================================================


class TestGetSpaceDetails:
    """Tests for get_space_details method."""

    @pytest.mark.asyncio
    async def test_get_space_details_success(self, lurky_client: LurkyClient):
        """Successful fetch returns SpaceDetails."""
        payload = build_space_details(space_id="space-123", title="Bitcoin Spaces")
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await lurky_client.get_space_details("space-123")

        assert isinstance(result, SpaceDetails)
        assert result.id == "space-123"
        assert result.title == "Bitcoin Spaces"
        assert result.participant_count == 100

    @pytest.mark.asyncio
    async def test_get_space_details_not_found(self, lurky_client: LurkyClient):
        """404 response raises LurkyNotFoundError."""
        mock_client = MockLurkyHttpClient(
            [MockHTTPResponse(payload={}, status_code=404)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(LurkyNotFoundError):
                await lurky_client.get_space_details("nonexistent-space")


# =============================================================================
# Feature 3: Get Space Mind Map
# =============================================================================


class TestGetSpaceMindMap:
    """Tests for get_space_mind_map method."""

    @pytest.mark.asyncio
    async def test_get_mind_map_success(self, lurky_client: LurkyClient):
        """Successful fetch returns MindMap with nodes."""
        payload = build_mind_map()
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await lurky_client.get_space_mind_map("space-123")

        assert isinstance(result, MindMap)
        assert len(result.nodes) == 3
        assert result.nodes[0].title == "Main Topic"
        assert result.nodes[1].parent_id == "node-1"


# =============================================================================
# Feature 4: Get Space Discussions
# =============================================================================


class TestGetSpaceDiscussions:
    """Tests for get_space_discussions method."""

    @pytest.mark.asyncio
    async def test_get_discussions_success(self, lurky_client: LurkyClient):
        """Successful fetch returns list of Discussion objects."""
        payload = build_discussions_list(count=3)
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await lurky_client.get_space_discussions("space-123")

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0].title == "Discussion 0"
        assert result[2].title == "Discussion 2"


# =============================================================================
# Feature 5: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in LurkyClient."""

    @pytest.mark.asyncio
    async def test_auth_error_raises_lurky_auth_error(self, lurky_client: LurkyClient):
        """401 response raises LurkyAuthError."""
        mock_client = MockLurkyHttpClient(
            [MockHTTPResponse(payload={}, status_code=401)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(LurkyAuthError, match="Invalid API key"):
                await lurky_client.search_discussions("test")

    @pytest.mark.asyncio
    async def test_server_error_raises_lurky_api_error(self, lurky_client: LurkyClient):
        """500 response raises LurkyAPIError."""
        mock_client = MockLurkyHttpClient(
            [MockHTTPResponse(payload={}, status_code=500)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(LurkyAPIError):
                await lurky_client.search_discussions("test")

    @pytest.mark.asyncio
    async def test_api_key_sent_in_header(self, lurky_client: LurkyClient):
        """API key is sent in x-lurky-api-key header."""
        payload = build_search_response()
        mock_client = MockLurkyHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await lurky_client.search_discussions("test")

        assert mock_client.calls[0]["headers"]["x-lurky-api-key"] == "test-api-key"


# =============================================================================
# Feature 6: URL Handling
# =============================================================================


class TestUrlHandling:
    """Tests for URL construction and normalization."""

    def test_base_url_normalized(self):
        """Base URL trailing slashes and /docs are stripped."""
        config = LurkyServiceConfig(
            api_key="test",
            base_url="https://api.lurky.app/docs/",
        )
        client = LurkyClient(config)

        assert client.base_url == "https://api.lurky.app"

    def test_base_url_without_trailing_slash(self):
        """Base URL without trailing slash is preserved."""
        config = LurkyServiceConfig(
            api_key="test",
            base_url="https://api.lurky.app",
        )
        client = LurkyClient(config)

        assert client.base_url == "https://api.lurky.app"
