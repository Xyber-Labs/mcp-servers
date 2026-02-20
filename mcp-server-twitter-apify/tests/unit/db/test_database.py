from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_twitter.db import CacheRepository
from mcp_twitter.db.models import (
    Base,
    QueryCacheEntry,
    QueryCacheItem,
    Tweet,
    TweetAuthor,
)
from mcp_twitter.twitter import QueryDefinition, QueryType, TwitterScraperInput


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
        {
            "id": "0987654321",
            "url": "https://x.com/user2/status/0987654321",
            "text": "Another tweet",
            "fullText": "Another tweet with different content",
            "author": {
                "id": "user456",
                "userName": "testuser2",
                "name": "Test User 2",
                "url": "https://x.com/testuser2",
            },
            "retweetCount": 0,
            "replyCount": 0,
            "likeCount": 5,
            "quoteCount": 0,
            "viewCount": 100,
            "createdAt": "Thu Dec 25 13:30:55 +0000 2025",
        },
    ]


def test_query_cache_key_deterministic() -> None:
    """Test query cache key generation is deterministic."""
    q1 = QueryDefinition(
        id="1", type="topic", name="test",
        input=TwitterScraperInput(searchTerms=["test"], maxItems=100, sort="Latest"),
    )
    q2 = QueryDefinition(
        id="2", type="topic", name="different",
        input=TwitterScraperInput(searchTerms=["test"], maxItems=100, sort="Latest"),
    )
    q3 = QueryDefinition(
        id="3", type="topic", name="test",
        input=TwitterScraperInput(searchTerms=["test"], maxItems=50, sort="Latest"),
    )

    assert q1.cache_key == q2.cache_key  # Same type+input = same key (id/name ignored)
    assert q1.cache_key != q3.cache_key  # Different input = different key
    assert len(q1.cache_key) == 64  # SHA256 hex = 64 chars


def test_query_cache_key_differs_by_type() -> None:
    """Test query keys differ by query type."""
    input_params = TwitterScraperInput(searchTerms=["test"], maxItems=100)

    q_topic = QueryDefinition(id="1", type="topic", name="t", input=input_params)
    q_profile = QueryDefinition(id="2", type="profile", name="p", input=input_params)
    q_replies = QueryDefinition(id="3", type="replies", name="r", input=input_params)

    assert q_topic.cache_key != q_profile.cache_key
    assert q_profile.cache_key != q_replies.cache_key
    assert q_topic.cache_key != q_replies.cache_key


def test_save_query_cache(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test saving query results to cache."""
    query_key = "test_key_123"
    query_type: QueryType = "topic"
    params = {"searchTerms": ["test"], "maxItems": 100}

    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type=query_type,
        params=params,
        items=sample_tweet_data,
        dataset_id="dataset123",
        output_format="min",
    )

    # Verify cache entry was created
    with in_memory_db.Session() as session:
        entry = (
            session.query(QueryCacheEntry)
            .filter(QueryCacheEntry.query_key == query_key)
            .first()
        )
        assert entry is not None
        assert entry.query_type == query_type
        assert entry.item_count == 2
        assert entry.dataset_id == "dataset123"
        assert entry.params == params

        # Verify tweets were created
        tweets = session.query(Tweet).all()
        assert len(tweets) == 2
        assert tweets[0].id == "1234567890"
        assert tweets[1].id == "0987654321"

        # Verify authors were created
        authors = session.query(TweetAuthor).all()
        assert len(authors) == 2
        assert authors[0].id == "user123"
        assert authors[0].username == "testuser"

        # Verify cache items link tweets to query
        cache_items = (
            session.query(QueryCacheItem)
            .filter(QueryCacheItem.query_key == query_key)
            .all()
        )
        assert len(cache_items) == 2
        assert cache_items[0].idx == 0
        assert cache_items[1].idx == 1


def test_get_cached_query_hit(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test retrieving cached query results."""
    query_key = "test_key_456"
    query_type: QueryType = "profile"
    params = {"searchTerms": ["from:testuser"], "maxItems": 100}

    # Save to cache
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type=query_type,
        params=params,
        items=sample_tweet_data,
        output_format="min",
    )

    # Retrieve from cache
    cached = in_memory_db.get_cached_query(query_key, "min")

    assert cached is not None
    assert len(cached) == 2
    assert cached[0]["id"] == "1234567890"
    assert cached[0]["text"] == "Hello world"
    assert cached[0]["author"]["userName"] == "testuser"
    assert "retweetCount" in cached[0]
    assert cached[0]["retweetCount"] == 10


def test_get_cached_query_miss(in_memory_db: CacheRepository) -> None:
    """Test cache miss returns None."""
    result = in_memory_db.get_cached_query("nonexistent_key", "min")
    assert result is None


def test_get_cached_query_expired(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test expired cache returns None."""
    query_key = "test_key_expired"
    params = {"searchTerms": ["test"]}

    # Save with past expiration
    with in_memory_db.Session() as session:
        entry = QueryCacheEntry(
            query_key=query_key,
            query_type="topic",
            params=params,
            item_count=len(sample_tweet_data),
            expires_at=datetime.now(UTC)
            - timedelta(hours=1),  # Expired 1 hour ago
        )
        session.add(entry)

        # Add tweets and cache items
        for idx, item in enumerate(sample_tweet_data):
            tweet = Tweet(
                id=item["id"],
                url=item.get("url"),
                text=item.get("text"),
                full_text=item.get("fullText"),
                retweet_count=item.get("retweetCount"),
                format="min",
            )
            session.add(tweet)

            cache_item = QueryCacheItem(
                query_key=query_key,
                tweet_id=item["id"],
                idx=idx,
            )
            session.add(cache_item)

        session.commit()

    # Try to retrieve - should return None due to expiration
    result = in_memory_db.get_cached_query(query_key, "min")
    assert result is None


def test_get_cached_query_max_format(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test retrieving cached query in max format."""
    query_key = "test_key_max"
    params = {"searchTerms": ["test"]}

    # Save with max format (includes raw_data)
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type="topic",
        params=params,
        items=sample_tweet_data,
        output_format="max",
    )

    # Retrieve in max format
    cached = in_memory_db.get_cached_query(query_key, "max")

    assert cached is not None
    assert len(cached) == 2
    # Max format should have raw_data or reconstructed full data
    assert "id" in cached[0]
    assert "text" in cached[0]


def test_author_deduplication(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test that authors are deduplicated when multiple tweets share author."""
    # Create tweets with same author
    tweets_same_author = [
        {
            **sample_tweet_data[0],
            "id": "tweet1",
        },
        {
            **sample_tweet_data[0],
            "id": "tweet2",
            "text": "Different text",
        },
    ]

    query_key = "test_key_dedup"
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type="topic",
        params={"searchTerms": ["test"]},
        items=tweets_same_author,
        output_format="min",
    )

    # Should only have one author
    with in_memory_db.Session() as session:
        authors = session.query(TweetAuthor).all()
        assert len(authors) == 1
        assert authors[0].id == "user123"

        # But two tweets
        tweets = session.query(Tweet).all()
        assert len(tweets) == 2


def test_tweet_deduplication(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test that same tweet in multiple queries is deduplicated."""
    query_key1 = "query1"
    query_key2 = "query2"

    # Save same tweet in two different queries
    in_memory_db.save_query_cache(
        query_key=query_key1,
        query_type="topic",
        params={"searchTerms": ["test1"]},
        items=[sample_tweet_data[0]],
        output_format="min",
    )

    in_memory_db.save_query_cache(
        query_key=query_key2,
        query_type="topic",
        params={"searchTerms": ["test2"]},
        items=[sample_tweet_data[0]],  # Same tweet
        output_format="min",
    )

    # Should only have one tweet in database
    with in_memory_db.Session() as session:
        tweets = session.query(Tweet).all()
        assert len(tweets) == 1

        # But two cache items linking to it
        cache_items = session.query(QueryCacheItem).all()
        assert len(cache_items) == 2
        assert cache_items[0].tweet_id == cache_items[1].tweet_id


def test_parse_twitter_date() -> None:
    """Test Twitter date parsing."""
    # Test Twitter format
    date_str = "Thu Dec 25 13:49:02 +0000 2025"
    parsed = CacheRepository._parse_twitter_date(date_str)
    assert parsed is not None
    assert parsed.year == 2025
    assert parsed.month == 12
    assert parsed.day == 25
    assert parsed.hour == 13
    assert parsed.minute == 49
    assert parsed.second == 2
    assert parsed.tzinfo == UTC

    # Test ISO format
    iso_date = "2025-12-25T13:49:02+00:00"
    parsed_iso = CacheRepository._parse_twitter_date(iso_date)
    assert parsed_iso is not None
    assert parsed_iso.year == 2025

    # Test None
    assert CacheRepository._parse_twitter_date(None) is None

    # Test invalid format
    invalid = CacheRepository._parse_twitter_date("invalid date")
    assert invalid is None


def test_get_cache_ttl(in_memory_db: CacheRepository) -> None:
    """Test cache TTL retrieval."""
    # Topic Latest
    ttl = in_memory_db.get_cache_ttl("topic", "Latest")
    assert ttl > 0

    # Topic Top
    ttl_top = in_memory_db.get_cache_ttl("topic", "Top")
    assert ttl_top > ttl  # Top should have longer TTL

    # Profile
    ttl_profile = in_memory_db.get_cache_ttl("profile")
    assert ttl_profile > 0

    # Replies
    ttl_replies = in_memory_db.get_cache_ttl("replies")
    assert ttl_replies > 0


def test_cache_update_existing_entry(
    in_memory_db: CacheRepository, sample_tweet_data: list[dict[str, Any]]
) -> None:
    """Test updating an existing cache entry."""
    query_key = "test_update"
    params = {"searchTerms": ["test"]}

    # Save initial cache
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type="topic",
        params=params,
        items=[sample_tweet_data[0]],
        output_format="min",
    )

    # Update with new items
    new_items = [sample_tweet_data[1]]
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type="topic",
        params=params,
        items=new_items,
        output_format="min",
    )

    # Verify entry was updated (not duplicated)
    with in_memory_db.Session() as session:
        entries = (
            session.query(QueryCacheEntry)
            .filter(QueryCacheEntry.query_key == query_key)
            .all()
        )
        assert len(entries) == 1
        assert entries[0].item_count == 1  # Updated count

        # Old cache items should be deleted
        cache_items = (
            session.query(QueryCacheItem)
            .filter(QueryCacheItem.query_key == query_key)
            .all()
        )
        assert len(cache_items) == 1
        assert cache_items[0].tweet_id == "0987654321"


def test_cache_without_author(in_memory_db: CacheRepository) -> None:
    """Test caching tweets without author information."""
    tweet_no_author = {
        "id": "tweet_no_author",
        "text": "Tweet without author",
        "createdAt": "Thu Dec 25 13:49:02 +0000 2025",
    }

    query_key = "test_no_author"
    in_memory_db.save_query_cache(
        query_key=query_key,
        query_type="topic",
        params={"searchTerms": ["test"]},
        items=[tweet_no_author],
        output_format="min",
    )

    # Should still save successfully
    cached = in_memory_db.get_cached_query(query_key, "min")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["id"] == "tweet_no_author"
    assert "author" not in cached[0] or cached[0].get("author") is None
