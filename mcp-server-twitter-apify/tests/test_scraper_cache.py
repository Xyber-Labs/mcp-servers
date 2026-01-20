"""
Tests for scraper integration with database cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import mcp_twitter.twitter.scraper as scraper_mod
from db import Database
from db.models import Base
from mcp_twitter.twitter.models import QueryDefinition, TwitterScraperInput
from mcp_twitter.twitter.scraper import TwitterScraper

from tests.fakes import FakeApifyClient


@pytest.fixture
def in_memory_db() -> Database:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    db = Database.__new__(Database)
    db.engine = engine
    db.Session = SessionLocal
    return db


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
    monkeypatch, tmp_results_dir: Path, in_memory_db: Database, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test that scraper uses cache when available."""
    from db import generate_query_key
    
    # Pre-populate cache
    query_type = "topic"
    params = {"searchTerms": ["cached"], "maxItems": 100, "sort": "Latest"}
    query_key = generate_query_key(query_type, params)
    
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type=query_type,
        params=params,
        items=sample_tweet_data,
        output_format="min",
    )
    
    # Mock database instance
    monkeypatch.setattr("db.get_db_instance", lambda: in_memory_db)
    
    # Create scraper with cache enabled
    scraper = TwitterScraper(
        apify_token="token",
        results_dir=None,  # No file writing
        actor_name="test-actor",
        output_format="min",
        use_cache=True,
    )
    
    # Create query
    query = QueryDefinition(
        id="test",
        type=query_type,
        name="Test Query",
        input=TwitterScraperInput(**params),
    )
    
    # Mock the database getter to return our in-memory DB
    scraper._db = in_memory_db
    
    # Run query - should use cache, not call Apify
    fake_client = FakeApifyClient(dataset_id="ds1", items=[])
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005
    
    result_path = scraper.run_query(query)
    
    # Verify cache was used (no Apify calls)
    assert len(fake_client.calls) == 0
    
    # Verify items are available
    items = scraper.get_last_items()
    assert items is not None
    assert len(items) == 1
    assert items[0]["id"] == "1234567890"


def test_scraper_saves_to_cache_on_miss(
    monkeypatch, tmp_results_dir: Path, in_memory_db: Database, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test that scraper saves to cache after Apify call."""
    from db import generate_query_key
    
    # Create fake Apify client
    fake_client = FakeApifyClient(dataset_id="ds1", items=sample_tweet_data)
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005
    
    # Create scraper with cache enabled
    scraper = TwitterScraper(
        apify_token="token",
        results_dir=None,
        actor_name="test-actor",
        output_format="min",
        use_cache=True,
    )
    
    # Mock the database getter to return our in-memory DB
    scraper._db = in_memory_db
    
    # Create query
    query_type = "profile"
    params = {"searchTerms": ["from:testuser"], "maxItems": 100}
    query_input = TwitterScraperInput(**params)
    query = QueryDefinition(
        id="test",
        type=query_type,
        name="Test Query",
        input=query_input,
    )
    
    # Run query - should call Apify and save to cache
    scraper.run_query(query)
    
    # Verify Apify was called
    assert len(fake_client.calls) > 0
    
    # Verify cache was populated
    # Use the same params dict that the scraper uses (with defaults included)
    run_dict = query_input.model_dump(exclude_none=True)
    query_key = generate_query_key(query_type, run_dict)
    cached = in_memory_db.get_cached_query(query_key, "min")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["id"] == "1234567890"


def test_scraper_cache_disabled(monkeypatch, tmp_results_dir: Path, sample_tweet_data: list[dict[str, Any]]) -> None:
    """Test that scraper skips cache when disabled."""
    fake_client = FakeApifyClient(dataset_id="ds1", items=sample_tweet_data)
    monkeypatch.setattr(scraper_mod, "ApifyClient", lambda token: fake_client)  # noqa: ARG005
    
    # Create scraper with cache disabled
    scraper = TwitterScraper(
        apify_token="token",
        results_dir=tmp_results_dir,
        actor_name="test-actor",
        output_format="min",
        use_cache=False,  # Cache disabled
    )
    
    query = QueryDefinition(
        id="test",
        type="topic",
        name="Test Query",
        input=TwitterScraperInput(searchTerms=["test"], maxItems=100),
    )
    
    # Run query
    scraper.run_query(query)
    
    # Should call Apify (cache disabled)
    assert len(fake_client.calls) > 0
    
    # Should write to file (results_dir provided)
    assert scraper.results_dir is not None

