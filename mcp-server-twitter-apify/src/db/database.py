"""
Database layer for caching Twitter scraper results in Postgres.

Replaces the legacy file-based `results/*.json` storage with a Postgres-backed cache.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

import logging
from mcp_twitter.config import AppSettings, DatabaseConfig

logger = logging.getLogger(__name__)
from mcp_twitter.twitter import OutputFormat, QueryType

from .models import Base, QueryCacheEntry, QueryCacheItem, Tweet, TweetAuthor

log = logging.getLogger("mcp_twitter.db")

_db_instance: Database | None = None


def get_db_instance() -> Database:
    """Get or create the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def generate_query_key(query_type: QueryType, params: dict[str, Any]) -> str:
    """
    Generate a deterministic hash key for a query.

    Args:
        query_type: Type of query (topic, profile, replies)
        params: Query parameters dict (searchTerms, sort, maxItems, etc.)

    Returns:
        SHA256 hash hex string (64 chars)
    """
    # Normalize params: sort keys, exclude None values, convert to JSON
    normalized = {
        "type": query_type,
        **{k: v for k, v in sorted(params.items()) if v is not None},
    }
    key_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


class Database:
    """
    Database wrapper for Twitter scraper cache.

    Handles connection, table creation, and cache operations.
    """

    def __init__(
        self,
        db_url: str | None = None,
        max_retries: int = 30,
        retry_delay: int = 2,
    ):
        """
        Initialize database connection with retry logic.

        Args:
            db_url: Optional database URL. If None, reads from DatabaseConfig
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        """
        if db_url is None:
            settings = AppSettings()
            db_url = settings.database.DATABASE_URL
            if not db_url:
                raise RuntimeError(
                    "DATABASE_URL not configured. Set it in .env or environment variables."
                )

        self.engine = None
        self.Session: sessionmaker[Session] | None = None

        # Retry connection with exponential backoff
        for attempt in range(max_retries):
            try:
                log.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")

                # Create database engine with connection pooling
                self.engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={
                        "connect_timeout": 10,
                        "options": "-c statement_timeout=30000",
                    },
                )

                # Test connection
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()

                log.info("Database connection test successful!")

                # Create session factory
                self.Session = sessionmaker(bind=self.engine)

                # Create tables if they don't exist
                try:
                    Base.metadata.create_all(self.engine)
                    log.info("Database tables verified/created successfully!")
                except Exception as table_error:
                    log.warning(
                        f"Could not create/verify tables (this is OK if migrations handle it): "
                        f"{str(table_error)[:200]}"
                    )

                log.info("Database connection established successfully!")
                return

            except OperationalError as e:
                if attempt < max_retries - 1:
                    wait_time = min(retry_delay * (2 ** min(attempt, 3)), 10)
                    log.warning(
                        f"Database connection failed (attempt {attempt + 1}/{max_retries}): "
                        f"{str(e)[:200]}"
                    )
                    log.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(retry_delay * (2 ** min(attempt, 3)), 10)
                    log.warning(
                        f"Unexpected error connecting to database "
                        f"(attempt {attempt + 1}/{max_retries}): {str(e)[:200]}"
                    )
                    log.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                    raise

    def get_cache_ttl(self, query_type: QueryType, sort: str | None = None) -> int:
        """
        Get cache TTL in seconds for a query type.

        Args:
            query_type: Type of query
            sort: Sort order (for topic queries)

        Returns:
            TTL in seconds
        """
        settings = AppSettings()
        db_config = settings.database

        if query_type == "topic":
            return db_config.cache_ttl_topic_top if sort == "Top" else db_config.cache_ttl_topic_latest
        elif query_type == "profile":
            return db_config.cache_ttl_profile
        elif query_type == "replies":
            return db_config.cache_ttl_replies
        else:
            return 1800  # Default 30 minutes

    def get_cached_query(
        self, query_key: str, output_format: OutputFormat = "min"
    ) -> list[dict[str, Any]] | None:
        """
        Retrieve cached query results if valid (not expired).

        Args:
            query_key: Query cache key (hash)
            output_format: Desired output format (min/max)

        Returns:
            List of tweet dicts if cache hit and valid, None if miss or expired
        """
        if not self.Session:
            return None

        with self.Session() as session:
            entry = session.query(QueryCacheEntry).filter(QueryCacheEntry.query_key == query_key).first()
            if not entry:
                return None

            # Check if expired
            now = datetime.now(timezone.utc)
            # Handle SQLite which may return naive datetimes
            expires_at = entry.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                log.debug(f"Cache expired for query_key={query_key[:16]}...")
                return None

            # Load tweets with relationship
            cache_items = (
                session.query(QueryCacheItem)
                .filter(QueryCacheItem.query_key == query_key)
                .order_by(QueryCacheItem.idx)
                .all()
            )

            if not cache_items:
                log.debug(f"No cache items found for query_key={query_key[:16]}...")
                return []

            # Build result list
            tweets = []
            for item in cache_items:
                # Load tweet explicitly (in case of lazy loading issues)
                tweet = session.query(Tweet).filter(Tweet.id == item.tweet_id).first()
                if not tweet:
                    log.warning(f"Tweet {item.tweet_id} not found for cache item {item.id}")
                    continue
                if output_format == "min":
                    # Return minimized format
                    tweet_dict = {
                        "id": tweet.id,
                        "url": tweet.url,
                        "text": tweet.text,
                        "fullText": tweet.full_text,
                        "retweetCount": tweet.retweet_count,
                        "replyCount": tweet.reply_count,
                        "likeCount": tweet.like_count,
                        "quoteCount": tweet.quote_count,
                        "viewCount": tweet.view_count,
                        "createdAt": tweet.created_at.isoformat() if tweet.created_at else None,
                    }
                    tweet_dict = {k: v for k, v in tweet_dict.items() if v is not None}

                    # Add author if available
                    if tweet.author:
                        author_dict = {
                            "id": tweet.author.id,
                            "userName": tweet.author.username,
                            "name": tweet.author.name,
                            "url": tweet.author.url,
                        }
                        author_dict = {k: v for k, v in author_dict.items() if v is not None}
                        tweet_dict["author"] = author_dict
                else:
                    # Return max format (raw_data if available, otherwise reconstruct)
                    if tweet.raw_data:
                        tweet_dict = tweet.raw_data.copy()
                    else:
                        # Reconstruct from normalized fields
                        tweet_dict = {
                            "id": tweet.id,
                            "url": tweet.url,
                            "text": tweet.text,
                            "fullText": tweet.full_text,
                            "retweetCount": tweet.retweet_count,
                            "replyCount": tweet.reply_count,
                            "likeCount": tweet.like_count,
                            "quoteCount": tweet.quote_count,
                            "viewCount": tweet.view_count,
                            "createdAt": tweet.created_at.isoformat() if tweet.created_at else None,
                        }
                        if tweet.author:
                            tweet_dict["author"] = {
                                "id": tweet.author.id,
                                "userName": tweet.author.username,
                                "name": tweet.author.name,
                                "url": tweet.author.url,
                            }

                tweets.append(tweet_dict)

            log.info(f"Cache hit for query_key={query_key[:16]}... ({len(tweets)} items)")
            return tweets

    def save_query_cache(
        self,
        query_key: str,
        query_type: QueryType,
        params: dict[str, Any],
        items: list[dict[str, Any]],
        dataset_id: str | None = None,
        output_format: OutputFormat = "min",
    ) -> None:
        """
        Save query results to cache.

        Args:
            query_key: Query cache key (hash)
            query_type: Type of query
            params: Query parameters dict
            items: List of tweet dicts from Apify
            dataset_id: Optional Apify dataset ID
            output_format: Format of items (min/max)
        """
        if not self.Session:
            raise RuntimeError("Database session not initialized")

        settings = AppSettings()
        ttl_seconds = self.get_cache_ttl(query_type, params.get("sort"))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        with self.Session() as session:
            # Create or update cache entry
            entry = session.query(QueryCacheEntry).filter(QueryCacheEntry.query_key == query_key).first()
            if entry:
                # Update existing entry
                entry.item_count = len(items)
                entry.expires_at = expires_at
                if dataset_id:
                    entry.dataset_id = dataset_id
                # Delete old cache items
                session.query(QueryCacheItem).filter(QueryCacheItem.query_key == query_key).delete()
            else:
                # Create new entry
                entry = QueryCacheEntry(
                    query_key=query_key,
                    query_type=query_type,
                    params=params,
                    dataset_id=dataset_id,
                    item_count=len(items),
                    expires_at=expires_at,
                )
                session.add(entry)

            # Save tweets and link to cache
            for idx, item in enumerate(items):
                tweet_id = item.get("id")
                if not tweet_id:
                    log.warning(f"Skipping item without id at index {idx}")
                    continue

                # Get or create author
                author_id = None
                author_data = item.get("author")
                if author_data and isinstance(author_data, dict):
                    author_id = author_data.get("id")
                    if author_id:
                        author = (
                            session.query(TweetAuthor).filter(TweetAuthor.id == author_id).first()
                        )
                        if not author:
                            author = TweetAuthor(
                                id=author_id,
                                username=author_data.get("userName") or "",
                                name=author_data.get("name"),
                                url=author_data.get("url") or author_data.get("twitterUrl"),
                            )
                            session.add(author)
                        else:
                            # Update author info if changed
                            if author_data.get("userName"):
                                author.username = author_data["userName"]
                            if author_data.get("name"):
                                author.name = author_data["name"]
                            url = author_data.get("url") or author_data.get("twitterUrl")
                            if url:
                                author.url = url

                # Get or create tweet
                tweet = session.query(Tweet).filter(Tweet.id == tweet_id).first()
                if not tweet:
                    tweet = Tweet(
                        id=tweet_id,
                        url=item.get("url"),
                        text=item.get("text"),
                        full_text=item.get("fullText"),
                        author_id=author_id,
                        retweet_count=item.get("retweetCount"),
                        reply_count=item.get("replyCount"),
                        like_count=item.get("likeCount"),
                        quote_count=item.get("quoteCount"),
                        view_count=item.get("viewCount"),
                        created_at=self._parse_twitter_date(item.get("createdAt")),
                        format=output_format,
                        raw_data=item if output_format == "max" else None,
                    )
                    session.add(tweet)
                else:
                    # Update tweet if newer or if we have max format data
                    if output_format == "max" and not tweet.raw_data:
                        tweet.raw_data = item
                    if item.get("retweetCount") is not None:
                        tweet.retweet_count = item["retweetCount"]
                    if item.get("replyCount") is not None:
                        tweet.reply_count = item["replyCount"]
                    if item.get("likeCount") is not None:
                        tweet.like_count = item["likeCount"]
                    if item.get("quoteCount") is not None:
                        tweet.quote_count = item["quoteCount"]
                    if item.get("viewCount") is not None:
                        tweet.view_count = item["viewCount"]

                # Create cache item link
                cache_item = QueryCacheItem(
                    query_key=query_key,
                    tweet_id=tweet_id,
                    idx=idx,
                )
                session.add(cache_item)

            session.commit()
            log.info(
                f"Saved {len(items)} items to cache (query_key={query_key[:16]}..., "
                f"expires_at={expires_at.isoformat()})"
            )

    @staticmethod
    def _parse_twitter_date(date_str: str | None) -> datetime | None:
        """
        Parse Twitter date string to datetime.

        Twitter dates are typically in format: "Thu Dec 25 13:49:02 +0000 2025"
        """
        if not date_str:
            return None

        # Try ISO format first
        if "T" in date_str:
            try:
                # ISO format: "2025-12-29T09:02:42+00:00" or "2025-12-29T09:02:42Z"
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        # Try Twitter format: "Thu Dec 25 13:49:02 +0000 2025"
        if "+0000" in date_str or "-0000" in date_str or "+00:00" in date_str:
            parts = date_str.split()
            if len(parts) >= 6:
                try:
                    # parts[0] = "Thu" (day name, skip)
                    # parts[1] = "Dec" (month)
                    # parts[2] = "25" (day)
                    # parts[3] = "13:49:02" (time)
                    # parts[4] = "+0000" (timezone, skip)
                    # parts[5] = "2025" (year)
                    date_part = f"{parts[1]} {parts[2]} {parts[5]} {parts[3]}"
                    # Parse without timezone, then add UTC
                    dt = datetime.strptime(date_part, "%b %d %Y %H:%M:%S")
                    return dt.replace(tzinfo=timezone.utc)
                except (ValueError, IndexError) as parse_error:
                    log.warning(f"Failed to parse Twitter date format '{date_str}': {parse_error}")
                    return None
        
        log.warning(f"Unrecognized date format: '{date_str}'")
        return None
