from __future__ import annotations

import pytest

from mcp_server_tavily.tavily.config import TavilyConfig
from mcp_server_tavily.tavily.errors import (
    TavilyApiError,
    TavilyConfigError,
    TavilyEmptyQueryError,
    TavilyServiceError,
)
from mcp_server_tavily.tavily.models import TavilySearchResult
from mcp_server_tavily.tavily.module import _TavilyService


@pytest.fixture
def tavily_service() -> _TavilyService:
    """Provide a TavilyService with deterministic configuration for tests."""

    config = TavilyConfig(
        api_key="test-api-key",
        max_results=5,
        topic="general",
        search_depth="basic",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )
    return _TavilyService(config)


@pytest.mark.asyncio
async def test_search_success(
    monkeypatch: pytest.MonkeyPatch, tavily_service: _TavilyService
) -> None:
    """Test successful search returns TavilySearchResult list."""

    async def mock_ainvoke(query: str) -> dict:
        return {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                }
            ]
        }

    class MockTool:
        async def ainvoke(self, query: str) -> dict:
            return await mock_ainvoke(query)

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        lambda max_results=None, api_key=None, search_depth=None: MockTool(),
    )

    results = await tavily_service.search("test query", api_key="test-key")

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], TavilySearchResult)
    assert results[0].title == "Test Result"


@pytest.mark.asyncio
async def test_search_empty_query_raises_error(
    tavily_service: _TavilyService,
) -> None:
    """Test that empty query raises TavilyEmptyQueryError."""

    with pytest.raises(TavilyEmptyQueryError):
        await tavily_service.search("")


@pytest.mark.asyncio
async def test_search_handles_error_response(
    monkeypatch: pytest.MonkeyPatch, tavily_service: _TavilyService
) -> None:
    """Test that error responses raise TavilyApiError."""

    class MockTool:
        async def ainvoke(self, query: str) -> str:
            return "error"

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        lambda max_results=None, api_key=None, search_depth=None: MockTool(),
    )

    with pytest.raises(TavilyApiError, match="Tavily API returned an error"):
        await tavily_service.search("test query", api_key="test-key")


@pytest.mark.asyncio
async def test_search_handles_empty_results(
    monkeypatch: pytest.MonkeyPatch, tavily_service: _TavilyService
) -> None:
    """Test that empty results raise TavilyEmptyResultsError."""

    from mcp_server_tavily.tavily.errors import TavilyEmptyResultsError

    class MockTool:
        async def ainvoke(self, query: str) -> dict:
            return {}

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        lambda max_results=None, api_key=None, search_depth=None: MockTool(),
    )

    with pytest.raises(TavilyEmptyResultsError, match="No results were found"):
        await tavily_service.search("test query", api_key="test-key")


@pytest.mark.asyncio
async def test_config_no_header_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that config API key works when no header is provided."""
    config = TavilyConfig(
        api_key="config-api-key",
        max_results=5,
    )
    tavily_service = _TavilyService(config)

    async def mock_ainvoke(query: str) -> dict:
        return {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                }
            ]
        }

    class MockTool:
        async def ainvoke(self, query: str) -> dict:
            return await mock_ainvoke(query)

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        lambda max_results=None, api_key=None, search_depth=None: MockTool(),
    )

    results = await tavily_service.search("test query")

    assert isinstance(results, list)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_no_config_header_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that header API key works when no config is set."""
    config = TavilyConfig(
        api_key="",
        max_results=5,
    )
    tavily_service = _TavilyService(config)

    async def mock_ainvoke(query: str) -> dict:
        return {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                }
            ]
        }

    class MockTool:
        async def ainvoke(self, query: str) -> dict:
            return await mock_ainvoke(query)

    def create_tool(max_results=None, api_key=None, search_depth=None):
        # Verify that header key is passed
        assert api_key == "header-api-key"
        return MockTool()

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        create_tool,
    )

    results = await tavily_service.search("test query", api_key="header-api-key")

    assert isinstance(results, list)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_no_config_no_header_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that request fails when neither config nor header provides an API key."""
    config = TavilyConfig(
        api_key="",
        max_results=5,
    )
    tavily_service = _TavilyService(config)

    # The error gets wrapped in TavilyConfigError when creating the tool
    with pytest.raises(TavilyConfigError) as exc_info:
        await tavily_service.search("test query", api_key=None)

    assert "not configured and was not provided" in str(exc_info.value)


@pytest.mark.asyncio
async def test_header_overrides_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that header API key takes precedence over config API key."""
    config = TavilyConfig(
        api_key="config-api-key",
        max_results=5,
    )
    tavily_service = _TavilyService(config)

    async def mock_ainvoke(query: str) -> dict:
        return {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                }
            ]
        }

    class MockTool:
        async def ainvoke(self, query: str) -> dict:
            return await mock_ainvoke(query)

    def create_tool(max_results=None, api_key=None, search_depth=None):
        # Verify that header key is used, not config key
        assert api_key == "header-api-key"
        return MockTool()

    monkeypatch.setattr(
        tavily_service,
        "_create_tavily_tool",
        create_tool,
    )

    results = await tavily_service.search("test query", api_key="header-api-key")

    assert isinstance(results, list)
    assert len(results) == 1

