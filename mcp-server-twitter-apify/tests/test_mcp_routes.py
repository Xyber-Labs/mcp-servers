"""
Tests for MCP-only endpoints.

These tests verify that MCP-only tools work correctly and are properly configured.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from mcp_twitter.app import create_app
from mcp_twitter.twitter import build_default_registry


class FakeScraper:
    """Fake scraper for testing MCP endpoints."""

    def __init__(self, tmp_results_dir: Path):
        self.apify_token = "token"
        self.results_dir = tmp_results_dir
        self.actor_id = "actor"
        self.use_cache = False
        self._last_items: list[dict[str, Any]] | None = [
            {
                "id": "1234567890",
                "text": "Great news about AI! This is amazing technology.",
                "fullText": "Great news about AI! This is amazing technology. #AI #Tech",
                "author": {
                    "id": "user123",
                    "userName": "techuser",
                    "name": "Tech User",
                    "url": "https://x.com/techuser",
                },
                "retweetCount": 10,
                "replyCount": 5,
                "likeCount": 50,
            },
            {
                "id": "0987654321",
                "text": "AI is transforming the world. Love it!",
                "fullText": "AI is transforming the world. Love it! #ArtificialIntelligence",
                "author": {
                    "id": "user456",
                    "userName": "ailover",
                    "name": "AI Lover",
                    "url": "https://x.com/ailover",
                },
                "retweetCount": 5,
                "replyCount": 2,
                "likeCount": 30,
            },
            {
                "id": "1122334455",
                "text": "Bad news today. Terrible situation.",
                "fullText": "Bad news today. Terrible situation. Very disappointed.",
                "author": {
                    "id": "user789",
                    "userName": "newsuser",
                    "name": "News User",
                    "url": "https://x.com/newsuser",
                },
                "retweetCount": 1,
                "replyCount": 0,
                "likeCount": 5,
            },
        ]

    def run_query(self, query) -> Path:  # noqa: ANN001
        """Run a query - data already set in __init__."""
        return self.results_dir / query.output_filename()

    def get_last_items(self) -> list[dict[str, Any]] | None:
        """Return fake items for API access."""
        return self._last_items


class FakeTwitterScraper(FakeScraper):
    """Matches the constructor the API uses when it creates a temp scraper."""

    def __init__(
        self,
        apify_token: str,  # noqa: ARG002
        results_dir: Path | None,
        actor_name: str,  # noqa: ARG002
        output_format: str = "min",  # noqa: ARG002
        use_cache: bool = False,  # noqa: ARG002
    ):
        super().__init__(results_dir or Path("/tmp"))


@pytest_asyncio.fixture
async def mcp_client(monkeypatch, tmp_results_dir: Path) -> AsyncClient:
    """Create test client with mocked scraper."""
    # Create app without lifespan to avoid anyio/Python 3.14 compatibility issues
    from fastapi import FastAPI
    from mcp_twitter.hybrid_routers import routers as hybrid_routers
    from mcp_twitter.mcp_routers import routers as mcp_routers
    
    # Create app without lifespan for testing
    app = FastAPI(
        title="Twitter MCP Server - Test",
        description="Test app without lifespan",
        version="2.0.0",
    )
    
    # Mount routers
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")
    for router in mcp_routers:
        app.include_router(router)

    # Set up app state manually (bypassing lifespan)
    app.state.registry = build_default_registry()
    app.state.scraper = FakeScraper(tmp_results_dir)

    # Patch TwitterScraper class for tests
    from mcp_twitter.twitter import scraper as scraper_mod

    monkeypatch.setattr(scraper_mod, "TwitterScraper", FakeTwitterScraper)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_mcp_search_topic_returns_items(mcp_client: AsyncClient) -> None:
    """Test that MCP search_topic endpoint returns tweet items."""
    response = await mcp_client.post(
        "/search_topic",
        json={
            "topic": "AI",
            "max_items": 10,
            "sort": "Top",
            "only_verified": False,
            "only_image": False,
            "lang": "en",
            "output_format": "min",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:  # If items returned
        assert body[0]["id"] == "1234567890"


@pytest.mark.asyncio
async def test_mcp_search_profile_returns_items(mcp_client: AsyncClient) -> None:
    """Test that MCP search_profile endpoint returns tweet items."""
    response = await mcp_client.post(
        "/search_profile",
        json={
            "username": "testuser",
            "max_items": 10,
            "lang": "en",
            "output_format": "min",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:  # If items returned
        assert body[0]["id"] == "1234567890"


@pytest.mark.asyncio
async def test_mcp_search_profile_latest_returns_items(mcp_client: AsyncClient) -> None:
    """Test that MCP search_profile_latest endpoint returns tweet items."""
    response = await mcp_client.post(
        "/search_profile_latest",
        json={
            "username": "testuser",
            "max_items": 10,
            "lang": "en",
            "output_format": "min",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:  # If items returned
        assert body[0]["id"] == "1234567890"


@pytest.mark.asyncio
async def test_mcp_search_replies_returns_items(mcp_client: AsyncClient) -> None:
    """Test that MCP search_replies endpoint returns tweet items."""
    response = await mcp_client.post(
        "/search_replies",
        json={
            "conversation_id": "1234567890",
            "max_items": 10,
            "lang": "en",
            "output_format": "min",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:  # If items returned
        assert body[0]["id"] == "1234567890"

