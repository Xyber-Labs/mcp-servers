"""
Tests for scraper integration with database cache.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import mcp_twitter.twitter.scraper as scraper_mod
from mcp_twitter.db import CacheRepository
from mcp_twitter.db.models import Base
from mcp_twitter.twitter.models import QueryDefinition, TwitterScraperInput
from mcp_twitter.twitter.scraper import TwitterScraper
from tests.unit.fakes import FakeApifyClient


@pytest.fixture
def in_memory_db() -> CacheRepository:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return CacheRepository(session_factory)


@pytest.fixture
def sample_tweet_data() -> list[dict[str, Any]]:
    """Sample tweet data for testing."""
    return [
        {
            "id": "1234567890",
            "url": "https://x.com/user/status/1234567890",
            "text": "Hello world",
            "fullText": "Hello world! This is a test tweet.",
            "author": {
                "id": "user123",
                "userName": "testuser",
                "name": "Test User",
                "url": "https://x.com/testuser",
            },
            "retweetCount": 10,
            "replyCount": 5,
            "likeCount": 50,
            "quoteCount": 2,
            "viewCount": 1000,
            "createdAt": "Thu Dec 25 13:49:02 +0000 2025",
        },
    ]


def test_scraper_uses_cache_on_hit(
    monkeypatch,
    in_memory_db: CacheRepository,
    sample_tweet_data: list[dict[str, Any]],
) -> None:
    """Test that scraper uses cache when available."""
    # Create query first to get cache_key
    query = QueryDefinition(
        id="test",
        type="topic",
        name="Test Query",
        input=TwitterScraperInput(searchTerms=["cached"], maxItems=100, sort="Latest"),
    )

    # Pre-populate cache using query.cache_key
    in_memory_db.save_query_cache(
        query_key=query.cache_key,
        query_type=query.type,
        params=query.input.model_dump(exclude_none=True),
        items=sample_tweet_data,
        output_format="min",
    )

    # Create scraper with database injected
    scraper = TwitterScraper(
        apify_token="token",
        actor_name="test-actor",
        output_format="min",
        database=in_memory_db,
    )

    # Run query - should use cache, not call Apify
    fake_client = FakeApifyClient(dataset_id="ds1", items=[])
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005

    items = scraper.run_query(query)

    # Verify cache was used (no Apify calls)
    assert len(fake_client.calls) == 0

    # Verify items returned from cache
    assert items is not None
    assert len(items) == 1
    assert items[0]["id"] == "1234567890"

    # Also verify get_last_items works
    last_items = scraper.get_last_items()
    assert last_items is not None
    assert len(last_items) == 1


def test_scraper_saves_to_cache_on_miss(
    monkeypatch,
    in_memory_db: CacheRepository,
    sample_tweet_data: list[dict[str, Any]],
) -> None:
    """Test that scraper saves to cache after Apify call."""
    # Create fake Apify client
    fake_client = FakeApifyClient(dataset_id="ds1", items=sample_tweet_data)
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005

    # Create scraper with database injected
    scraper = TwitterScraper(
        apify_token="token",
        actor_name="test-actor",
        output_format="min",
        database=in_memory_db,
    )

    # Create query
    query = QueryDefinition(
        id="test",
        type="profile",
        name="Test Query",
        input=TwitterScraperInput(searchTerms=["from:testuser"], maxItems=100),
    )

    # Run query - should call Apify and save to cache
    items = scraper.run_query(query)

    # Verify Apify was called
    assert len(fake_client.calls) > 0

    # Verify items returned
    assert items is not None
    assert len(items) == 1

    # Verify cache was populated using query.cache_key
    cached = in_memory_db.get_cached_query(query.cache_key, "min")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["id"] == "1234567890"


def test_scraper_cache_disabled(
    monkeypatch, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test that scraper skips cache when no database provided."""
    fake_client = FakeApifyClient(dataset_id="ds1", items=sample_tweet_data)
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005

    # Create scraper without database (cache disabled)
    scraper = TwitterScraper(
        apify_token="token",
        actor_name="test-actor",
        output_format="min",
        database=None,
    )

    query = QueryDefinition(
        id="test",
        type="topic",
        name="Test Query",
        input=TwitterScraperInput(searchTerms=["test"], maxItems=100),
    )

    # Run query
    items = scraper.run_query(query)

    # Should call Apify (no cache)
    assert len(fake_client.calls) > 0

    # Should return items
    assert items is not None
    assert len(items) == 1
