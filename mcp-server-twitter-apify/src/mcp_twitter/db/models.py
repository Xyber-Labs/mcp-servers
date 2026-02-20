"""
Database models for caching Apify Twitter scraper results in Postgres.

This replaces the legacy file-based `results/*.json` storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def _json_type() -> type[JSON]:
    """
    Use a portable JSON column type.

    Postgres will store this as JSON; if you want JSONB specifically later, we can
    introduce dialect-specific types via migrations.
    """
    return JSON


class QueryCacheEntry(Base):
    """
    One cached query (fingerprint + metadata + TTL).

    `query_key` is a deterministic hash of the request payload used to avoid re-running Apify.
    """

    __tablename__ = "twitter_query_cache"

    query_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    params: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)  # type: ignore[arg-type]

    dataset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationship
    items: Mapped[list[QueryCacheItem]] = relationship(
        "QueryCacheItem", back_populates="cache_entry", cascade="all, delete-orphan"
    )


class TweetAuthor(Base):
    """
    Twitter author/user information (normalized).

    This allows deduplication and efficient querying by author.
    """

    __tablename__ = "twitter_authors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Twitter user ID
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship
    tweets: Mapped[list[Tweet]] = relationship("Tweet", back_populates="author")


class Tweet(Base):
    """
    Individual tweet stored in normalized form.

    Supports both 'min' and 'max' output formats:
    - Common fields are stored as columns for efficient querying
    - Full raw data is stored in `raw_data` JSON column (for max format)
    - `format` indicates whether this was stored as min or max

    The same tweet can appear in multiple query cache entries (via QueryCacheItem).
    """

    __tablename__ = "twitter_tweets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Tweet ID
    url: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Author reference
    author_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("twitter_authors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author: Mapped[TweetAuthor | None] = relationship(
        "TweetAuthor", back_populates="tweets"
    )

    # Engagement metrics
    retweet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Timestamps
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Format and raw data
    format: Mapped[str] = mapped_column(
        String(8), nullable=False, default="min"
    )  # 'min' or 'max'
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(
        _json_type(), nullable=True
    )  # Full tweet JSON for max format

    # Relationship to query cache items
    cache_items: Mapped[list[QueryCacheItem]] = relationship(
        "QueryCacheItem", back_populates="tweet"
    )


class QueryCacheItem(Base):
    """
    Links tweets to query cache entries (many-to-many).
    """

    __tablename__ = "twitter_query_cache_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("twitter_query_cache.query_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tweet_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("twitter_tweets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idx: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Order within the query result

    # Relationships
    tweet: Mapped[Tweet] = relationship("Tweet", back_populates="cache_items")
    cache_entry: Mapped[QueryCacheEntry] = relationship(
        "QueryCacheEntry", back_populates="items"
    )


Index(
    "ix_twitter_query_cache_items_key_tweet_idx",
    QueryCacheItem.query_key,
    QueryCacheItem.tweet_id,
    unique=True,
)
Index(
    "ix_twitter_query_cache_items_key_idx", QueryCacheItem.query_key, QueryCacheItem.idx
)
