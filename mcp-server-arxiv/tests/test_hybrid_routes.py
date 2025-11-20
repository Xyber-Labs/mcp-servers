from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_arxiv.dependencies import get_arxiv_client
from mcp_server_arxiv.hybrid_routers.search import arxiv_search
from mcp_server_arxiv.hybrid_routers.search import router as search_router
from mcp_server_arxiv.schemas import ArxivPaperResponse, SearchRequest
from mcp_server_arxiv.xy_arxiv.models import ArxivSearchResult


class StubArxivClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | int | None]] = []

    async def search(
        self,
        *,
        query: str | None = None,
        arxiv_id: str | None = None,
        max_results: int | None = None,
        max_text_length: int | None = None,
    ) -> list[ArxivSearchResult]:
        self.calls.append(
            {
                "query": query,
                "arxiv_id": arxiv_id,
                "max_results": max_results,
                "max_text_length": max_text_length,
            }
        )
        if arxiv_id:
            return [
                ArxivSearchResult(
                    title="Attention Is All You Need",
                    authors=["Vaswani et al."],
                    published_date="2017-06-12",
                    summary="We propose the Transformer...",
                    arxiv_id="1706.03762",
                    pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
                    full_text="Test full text content",
                    processing_error=None,
                )
            ]
        return [
            ArxivSearchResult(
                title="Test Paper",
                authors=["Author One", "Author Two"],
                published_date="2024-01-01",
                summary="Test summary",
                arxiv_id="2401.00001",
                pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
                full_text="Test full text content",
                processing_error=None,
            )
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("max_results", [None, 5, 10])
async def test_arxiv_search_returns_serialised_results(
    max_results: int | None,
) -> None:
    request = SearchRequest(query="test query", max_results=max_results)
    client = StubArxivClient()

    result = await arxiv_search(
        search=request,
        arxiv_client=client,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ArxivPaperResponse)
    # Verify all required fields are present, especially title
    assert result[0].title == "Test Paper"
    assert result[0].arxiv_id == "2401.00001"
    assert result[0].authors == ["Author One", "Author Two"]
    assert result[0].published_date == "2024-01-01"
    assert result[0].summary == "Test summary"
    assert result[0].pdf_url == "https://arxiv.org/pdf/2401.00001.pdf"


@pytest.mark.asyncio
async def test_arxiv_search_with_text_length_limit() -> None:
    request = SearchRequest(query="test query", max_results=5, max_text_length=1000)
    client = StubArxivClient()

    result = await arxiv_search(
        search=request,
        arxiv_client=client,
    )

    assert isinstance(result, list)
    assert client.calls[0]["max_text_length"] == 1000


@pytest_asyncio.fixture
async def hybrid_client() -> AsyncClient:
    """HTTP-level client for hybrid routers to exercise validation rules."""

    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_search_endpoint_calls_arxiv_client() -> None:
    stub_client = StubArxivClient()
    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")
    app.dependency_overrides[get_arxiv_client] = lambda: stub_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/search",
            json={"query": "test query"},
        )

    assert response.status_code == 200
    assert len(stub_client.calls) == 1
    assert stub_client.calls[0]["query"] == "test query"
    # Verify response structure includes title
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "title" in data[0]
    assert data[0]["title"] == "Test Paper"


@pytest.mark.asyncio
@pytest.mark.parametrize("max_results", [0, 51])
async def test_arxiv_search_max_results_out_of_range_returns_422(
    hybrid_client: AsyncClient, max_results: int
) -> None:
    response = await hybrid_client.post(
        "/hybrid/search",
        json={"query": "test", "max_results": max_results},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("max_text_length", [99])
async def test_arxiv_search_max_text_length_too_small_returns_422(
    hybrid_client: AsyncClient, max_text_length: int
) -> None:
    response = await hybrid_client.post(
        "/hybrid/search",
        json={"query": "test", "max_text_length": max_text_length},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_arxiv_search_empty_body_returns_422() -> None:
    """HTTP-level validation for search payload."""

    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/search",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_arxiv_search_by_id_returns_single_result() -> None:
    """Test searching by arxiv_id returns a single paper result."""
    request = SearchRequest(arxiv_id="1706.03762", max_text_length=1000)
    client = StubArxivClient()
    
    result = await arxiv_search(
        search=request,
        arxiv_client=client,
    )
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ArxivPaperResponse)
    # Verify all required fields are present, especially title
    assert result[0].arxiv_id == "1706.03762"
    assert result[0].title == "Attention Is All You Need"
    assert result[0].authors == ["Vaswani et al."]
    assert result[0].published_date == "2017-06-12"
    assert result[0].summary == "We propose the Transformer..."
    assert result[0].pdf_url == "https://arxiv.org/pdf/1706.03762.pdf"
    assert len(client.calls) == 1
    assert client.calls[0]["arxiv_id"] == "1706.03762"


@pytest.mark.asyncio
async def test_arxiv_search_both_query_and_id_returns_422() -> None:
    """Test that providing both query and arxiv_id returns validation error."""
    app = FastAPI()
    app.include_router(search_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/search",
            json={"query": "test", "arxiv_id": "1706.03762"},
        )
        assert response.status_code == 422

