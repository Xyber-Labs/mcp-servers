from __future__ import annotations

import arxiv
import pytest

from mcp_server_arxiv.xy_arxiv.config import ArxivConfig
from mcp_server_arxiv.xy_arxiv.errors import ArxivApiError, ArxivServiceError
from mcp_server_arxiv.xy_arxiv.models import ArxivSearchResult
from mcp_server_arxiv.xy_arxiv.module import _ArxivService


@pytest.fixture
def arxiv_service() -> _ArxivService:
    """Provide an ArxivService with deterministic configuration for tests."""

    config = ArxivConfig(
        max_results=5,
        max_text_length=2000,
    )
    return _ArxivService(config)


@pytest.mark.asyncio
async def test_search_empty_query_raises_error(
    arxiv_service: _ArxivService,
) -> None:
    """Test that empty query raises ValueError."""

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await arxiv_service.search(query="")


@pytest.mark.asyncio
async def test_search_by_id_not_found_raises_api_error(
    monkeypatch: pytest.MonkeyPatch, arxiv_service: _ArxivService
) -> None:
    """Test that missing arxiv_id raises ArxivApiError from metadata fetch."""

    monkeypatch.setattr(arxiv_service.client, "results", lambda search: iter([]))

    with pytest.raises(ArxivApiError, match="not found"):
        await arxiv_service.search(arxiv_id="1706.03762")


@pytest.mark.asyncio
async def test_search_respects_max_results_override(
    monkeypatch: pytest.MonkeyPatch, arxiv_service: _ArxivService
) -> None:
    captured: dict[str, int] = {}

    def fake_results(search: arxiv.Search):
        captured["max_results"] = search.max_results
        return iter([])

    monkeypatch.setattr(arxiv_service.client, "results", fake_results)

    results = await arxiv_service.search(query="test query", max_results=10)

    assert isinstance(results, list)
    assert captured["max_results"] == 10


@pytest.mark.asyncio
async def test_search_by_id_empty_id_raises_error(
    arxiv_service: _ArxivService,
) -> None:
    """Test that empty arxiv_id raises ValueError."""

    with pytest.raises(ValueError, match="arxiv_id cannot be empty"):
        await arxiv_service.search(arxiv_id="")


@pytest.mark.asyncio
async def test_search_both_query_and_id_raises_error(
    arxiv_service: _ArxivService,
) -> None:
    """Test that providing both query and arxiv_id raises ValueError."""

    with pytest.raises(ValueError, match="Cannot provide both"):
        await arxiv_service.search(query="test", arxiv_id="1706.03762")


@pytest.mark.asyncio
async def test_search_neither_query_nor_id_raises_error(
    arxiv_service: _ArxivService,
) -> None:
    """Test that providing neither query nor arxiv_id raises ValueError."""

    with pytest.raises(ValueError, match="Either"):
        await arxiv_service.search()

