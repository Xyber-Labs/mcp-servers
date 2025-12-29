"""
Database package for Twitter scraper cache.

Provides Postgres-backed caching to replace file-based results storage.
"""

from __future__ import annotations

from .database import Database, generate_query_key, get_db_instance
from .models import Base, QueryCacheEntry, QueryCacheItem, Tweet, TweetAuthor

__all__ = [
    "Base",
    "Database",
    "QueryCacheEntry",
    "QueryCacheItem",
    "Tweet",
    "TweetAuthor",
    "generate_query_key",
    "get_db_instance",
]

