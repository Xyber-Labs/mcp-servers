from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from mcp_server_tavily.dependencies import get_tavily_client
from mcp_server_tavily.hybrid_routers.search import (
    API_KEY_HEADER,
    tavily_search,
)
from mcp_server_tavily.hybrid_routers.search import router as search_router
from mcp_server_tavily.schemas import SearchRequest
from mcp_server_tavily.tavily.models import TavilySearchResult


class StubTavilyClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | int | None]] = []

    async def search(
        self,
        query: str,
        max_results: int | None = None,
        api_key: str | None = None,
        search_depth: str | None = None,
    ) -> list[TavilySearchResult]:
        self.calls.append(
            {
                "query": query,
                "max_results": max_results,
                "api_key": api_key,
                "search_depth": search_depth,
            }
        )
        return [
            TavilySearchResult(
                title="Test Result",
                url="https://example.com",
                content="Test content",
            )
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("max_results", [None, 5, 10])
async def test_tavily_search_returns_serialised_results(
    max_results: int | None,
) -> None:
    request = SearchRequest(query="test query", max_results=max_results)
    client = StubTavilyClient()

    result = await tavily_search(
        search=request,
        tavily_api_key="test-header-key",
        tavily_client=client,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].title == "Test Result"
    assert client.calls[0]["api_key"] == "test-header-key"


@pytest.mark.asyncio
async def test_tavily_search_uses_header_api_key() -> None:
    request = SearchRequest(query="test query", max_results=5)
    client = StubTavilyClient()
    api_key = "override-key"

    result = await tavily_search(
        search=request,
        tavily_api_key=api_key,
        tavily_client=client,
    )

    assert isinstance(result, list)
    assert client.calls[0]["api_key"] == api_key


@pytest.mark.asyncio
async def test_tavily_search_missing_header_uses_config() -> None:
    """Test that missing header falls back to config API key."""
    request = SearchRequest(query="test query", max_results=5)
    client = StubTavilyClient()

    # When header is None, it should use config (if available)
    # Since StubTavilyClient doesn't check config, this test verifies the endpoint
    # passes None to the client, which will handle the fallback
    result = await tavily_search(
        search=request,
        tavily_api_key=None,
        tavily_client=client,
    )

    assert isinstance(result, list)
    assert client.calls[0]["api_key"] is None


@pytest_asyncio.fixture
async def hybrid_client() -> AsyncClient:
    """HTTP-level client for hybrid routers to exercise validation rules."""

    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_search_endpoint_passes_header_to_tavily_client() -> None:
    stub_client = StubTavilyClient()
    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")
    app.dependency_overrides[get_tavily_client] = lambda: stub_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/search",
            json={"query": "test query"},
            headers={API_KEY_HEADER: "header-key"},
        )

    assert response.status_code == 200
    assert stub_client.calls[0]["api_key"] == "header-key"


@pytest.mark.asyncio
@pytest.mark.parametrize("max_results", [0, 51])
async def test_tavily_search_max_results_out_of_range_returns_422(
    hybrid_client: AsyncClient, max_results: int
) -> None:
    response = await hybrid_client.post(
        "/hybrid/search",
        json={"query": "test", "max_results": max_results},
        headers={API_KEY_HEADER: "test-key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tavily_search_empty_body_returns_422() -> None:
    """HTTP-level validation for search payload."""

    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/search",
            json={},
            headers={API_KEY_HEADER: "test-header-key"},
        )
        assert response.status_code == 422



