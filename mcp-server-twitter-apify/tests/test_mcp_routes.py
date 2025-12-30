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
        self._last_items: list[dict[str, Any]] | None = None

    def run_query(self, query) -> Path:  # noqa: ANN001
        """Run a query and store fake results."""
        # Store fake tweet data
        self._last_items = [
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
async def test_summarize_tweets_returns_analysis(mcp_client: AsyncClient) -> None:
    """Test that summarize_tweets endpoint returns structured analysis."""
    response = await mcp_client.post(
        "/summarize_tweets",
        json={
            "topic": "AI",
            "max_items": 10,
            "sort": "Top",
        },
    )

    assert response.status_code == 200
    body = response.json()

    # Verify structure
    assert "topic" in body
    assert "summary" in body
    assert "tweet_count" in body
    assert "key_themes" in body
    assert "sentiment" in body
    assert "notable_mentions" in body
    assert "analysis_metadata" in body

    # Verify values
    assert body["topic"] == "AI"
    assert body["tweet_count"] == 3  # We return 3 fake tweets
    assert isinstance(body["key_themes"], list)
    assert body["sentiment"] in ["positive", "negative", "neutral"]
    assert isinstance(body["notable_mentions"], list)
    assert len(body["notable_mentions"]) > 0

    # Verify summary contains topic
    assert "AI" in body["summary"] or "ai" in body["summary"].lower()


@pytest.mark.asyncio
async def test_summarize_tweets_with_no_results(mcp_client: AsyncClient, monkeypatch) -> None:
    """Test summarize_tweets when no tweets are found."""
    # Create a scraper that returns no items
    class EmptyScraper(FakeScraper):
        def get_last_items(self) -> list[dict[str, Any]] | None:
            return None

    # Note: We can't access mcp_client.app directly with AsyncClient
    # Instead, we'll create a new client with the modified app
    from fastapi import FastAPI
    from mcp_twitter.hybrid_routers import routers as hybrid_routers
    from mcp_twitter.mcp_routers import routers as mcp_routers
    
    app = FastAPI()
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")
    for router in mcp_routers:
        app.include_router(router)
    app.state.registry = build_default_registry()
    app.state.scraper = EmptyScraper(Path("/tmp"))
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.post(
            "/summarize_tweets",
            json={
                "topic": "nonexistent_topic_xyz",
                "max_items": 10,
                "sort": "Latest",
            },
        )

        assert response.status_code == 200
        body = response.json()

    assert body["tweet_count"] == 0
    assert body["key_themes"] == []
    assert "No tweets found" in body["summary"]


@pytest.mark.asyncio
async def test_summarize_tweets_validates_input(mcp_client: AsyncClient) -> None:
    """Test that summarize_tweets validates input parameters."""
    # Test with invalid max_items (too high)
    response = await mcp_client.post(
        "/summarize_tweets",
        json={
            "topic": "AI",
            "max_items": 200,  # Exceeds limit of 100
            "sort": "Top",
        },
    )

    assert response.status_code == 422  # Validation error

    # Test with missing topic
    response = await mcp_client.post(
        "/summarize_tweets",
        json={
            "max_items": 10,
            "sort": "Top",
        },
    )

    assert response.status_code == 422  # Validation error


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

