from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session, sessionmaker

from mcp_twitter.db.models import QueryCacheEntry, QueryCacheItem, Tweet, TweetAuthor

if TYPE_CHECKING:
    from mcp_twitter.twitter import OutputFormat, QueryType

log = logging.getLogger(__name__)


class CacheRepository:
    """
    Repository for Twitter query cache operations.

    Provides methods to store and retrieve cached query results.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        cache_ttl_config: dict[str, int] | None = None,
    ):
        """
        Initialize repository with session factory.

        Args:
            session_factory: SQLAlchemy sessionmaker instance
            cache_ttl_config: Optional TTL config dict with keys:
                - topic_latest: TTL for topic queries with Latest sort (default: 900)
                - topic_top: TTL for topic queries with Top sort (default: 86400)
                - profile: TTL for profile queries (default: 1800)
                - replies: TTL for replies queries (default: 3600)

        """
        self.Session = session_factory
        self._cache_ttl = cache_ttl_config or {}

    def get_cache_ttl(self, query_type: QueryType, sort: str | None = None) -> int:
        """Get cache TTL in seconds for a query type."""
        if query_type == "topic":
            if sort == "Top":
                return self._cache_ttl.get("topic_top", 86400)
            return self._cache_ttl.get("topic_latest", 900)
        elif query_type == "profile":
            return self._cache_ttl.get("profile", 1800)
        elif query_type == "replies":
            return self._cache_ttl.get("replies", 3600)
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
        with self.Session() as session:
            entry = (
                session.query(QueryCacheEntry)
                .filter(QueryCacheEntry.query_key == query_key)
                .first()
            )
            if not entry:
                return None

            # Check if expired
            now = datetime.now(UTC)
            expires_at = entry.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
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
                tweet = session.query(Tweet).filter(Tweet.id == item.tweet_id).first()
                if not tweet:
                    log.warning(
                        f"Tweet {item.tweet_id} not found for cache item {item.id}"
                    )
                    continue

                if output_format == "min":
                    tweet_dict = self._tweet_to_min_dict(tweet)
                else:
                    tweet_dict = self._tweet_to_max_dict(tweet)

                tweets.append(tweet_dict)

            log.info(
                f"Cache hit for query_key={query_key[:16]}... ({len(tweets)} items)"
            )
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
        ttl_seconds = self.get_cache_ttl(query_type, params.get("sort"))
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        with self.Session() as session:
            # Create or update cache entry
            entry = (
                session.query(QueryCacheEntry)
                .filter(QueryCacheEntry.query_key == query_key)
                .first()
            )
            if entry:
                entry.item_count = len(items)
                entry.expires_at = expires_at
                if dataset_id:
                    entry.dataset_id = dataset_id
                # Delete old cache items
                session.query(QueryCacheItem).filter(
                    QueryCacheItem.query_key == query_key
                ).delete()
            else:
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
                author_id = self._upsert_author(session, item.get("author"))

                # Get or create tweet
                self._upsert_tweet(session, item, author_id, output_format)

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

    def _upsert_author(
        self, session: Session, author_data: dict[str, Any] | None
    ) -> str | None:
        """Create or update author, return author_id."""
        if not isinstance(author_data, dict) or not author_data.get("id"):
            return None

        author_id = author_data["id"]
        fields = {
            "username": author_data.get("userName") or "",
            "name": author_data.get("name"),
            "url": author_data.get("url") or author_data.get("twitterUrl"),
        }

        author = session.query(TweetAuthor).filter(TweetAuthor.id == author_id).first()
        if author:
            for attr, val in fields.items():
                if val:
                    setattr(author, attr, val)
        else:
            session.add(TweetAuthor(id=author_id, **fields))
        return author_id

    def _upsert_tweet(
        self,
        session: Session,
        item: dict[str, Any],
        author_id: str | None,
        output_format: OutputFormat,
    ) -> None:
        """Create or update tweet."""
        tweet_id = item["id"]
        tweet = session.query(Tweet).filter(Tweet.id == tweet_id).first()

        # Field mapping: api_key -> db_column
        count_fields = {
            "retweetCount": "retweet_count",
            "replyCount": "reply_count",
            "likeCount": "like_count",
            "quoteCount": "quote_count",
            "viewCount": "view_count",
        }

        if tweet:
            if output_format == "max" and not tweet.raw_data:
                tweet.raw_data = item
            for api_key, db_col in count_fields.items():
                if item.get(api_key) is not None:
                    setattr(tweet, db_col, item[api_key])
        else:
            session.add(
                Tweet(
                    id=tweet_id,
                    url=item.get("url"),
                    text=item.get("text"),
                    full_text=item.get("fullText"),
                    author_id=author_id,
                    created_at=self._parse_twitter_date(item.get("createdAt")),
                    format=output_format,
                    raw_data=item if output_format == "max" else None,
                    **{
                        db_col: item.get(api_key)
                        for api_key, db_col in count_fields.items()
                    },
                )
            )

    @staticmethod
    def _author_to_dict(author: TweetAuthor) -> dict[str, Any]:
        """Convert TweetAuthor model to dict, filtering None values."""
        return {
            k: v
            for k, v in {
                "id": author.id,
                "userName": author.username,
                "name": author.name,
                "url": author.url,
            }.items()
            if v is not None
        }

    @staticmethod
    def _tweet_to_dict(tweet: Tweet) -> dict[str, Any]:
        """Convert Tweet model to dict, filtering None values."""
        return {
            k: v
            for k, v in {
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
            }.items()
            if v is not None
        }

    def _tweet_to_min_dict(self, tweet: Tweet) -> dict[str, Any]:
        """Convert Tweet model to minimized dict."""
        result = self._tweet_to_dict(tweet)
        if tweet.author:
            result["author"] = self._author_to_dict(tweet.author)
        return result

    def _tweet_to_max_dict(self, tweet: Tweet) -> dict[str, Any]:
        """Convert Tweet model to max (raw) dict."""
        if tweet.raw_data:
            return tweet.raw_data.copy()
        result = self._tweet_to_dict(tweet)
        if tweet.author:
            result["author"] = self._author_to_dict(tweet.author)
        return result

    @staticmethod
    def _parse_twitter_date(date_str: str | None) -> datetime | None:
        """Parse Twitter date string to datetime."""
        if not date_str:
            return None

        # Try ISO format first
        if "T" in date_str:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Try Twitter format: "Thu Dec 25 13:49:02 +0000 2025"
        if "+0000" in date_str or "-0000" in date_str or "+00:00" in date_str:
            parts = date_str.split()
            if len(parts) >= 6:
                try:
                    date_part = f"{parts[1]} {parts[2]} {parts[5]} {parts[3]}"
                    dt = datetime.strptime(date_part, "%b %d %Y %H:%M:%S")
                    return dt.replace(tzinfo=UTC)
                except (ValueError, IndexError) as parse_error:
                    log.warning(
                        f"Failed to parse Twitter date format '{date_str}': {parse_error}"
                    )
                    return None

        log.warning(f"Unrecognized date format: '{date_str}'")
        return None


# Backwards compatibility alias
Database = CacheRepository
