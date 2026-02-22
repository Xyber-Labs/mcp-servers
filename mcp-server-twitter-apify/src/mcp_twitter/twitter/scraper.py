from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apify_client import ApifyClient

from mcp_twitter.config import AppSettings
from mcp_twitter.twitter.models import (
    OutputFormat,
    QueryDefinition,
    TwitterScraperInput,
)

if TYPE_CHECKING:
    from mcp_twitter.db import CacheRepository

log = logging.getLogger(__name__)


class TwitterScraper:
    """
    Thin wrapper around Apify runs + Postgres cache.

    Uses database-backed caching to reduce Apify API costs.
    """

    def __init__(
        self,
        apify_token: str,
        actor_name: str | None = None,
        output_format: OutputFormat = "min",
        database: CacheRepository | None = None,
    ):
        # Use config actor_name if not provided
        if actor_name is None:
            settings = AppSettings()
            actor_name = settings.apify.actor_name

        self.apify_token = apify_token
        self.client = ApifyClient(apify_token)
        self.actor_id = actor_name  # Internal name remains actor_id for Apify client
        self.output_format: OutputFormat = output_format
        self._db = database
        self.use_cache = database is not None

        # Store last run items for API access
        self._last_items: list[dict[str, Any]] | None = None

    @staticmethod
    def _minimize_item(item: dict[str, Any]) -> dict[str, Any]:
        """Keep only the highest-signal tweet fields."""
        author = item.get("author") or {}
        if isinstance(author, dict):
            author_min = {
                "id": author.get("id"),
                "userName": author.get("userName"),
                "name": author.get("name"),
                "url": author.get("url") or author.get("twitterUrl"),
            }
            author_min = {k: v for k, v in author_min.items() if v is not None}
        else:
            author_min = None

        out: dict[str, Any] = {
            "id": item.get("id"),
            "url": item.get("url"),
            "text": item.get("text"),
            "fullText": item.get("fullText"),
            "author": author_min,
            "retweetCount": item.get("retweetCount"),
            "replyCount": item.get("replyCount"),
            "likeCount": item.get("likeCount"),
            "quoteCount": item.get("quoteCount"),
            "viewCount": item.get("viewCount"),
            "createdAt": item.get("createdAt"),
        }
        return {k: v for k, v in out.items() if v is not None}

    def run(self, run_input: TwitterScraperInput) -> list[dict[str, Any]]:
        """Run Apify query without caching."""
        run_dict: dict[str, Any] = run_input.model_dump(exclude_none=True)

        run = self.client.actor(self.actor_id).call(run_input=run_dict)
        dataset_id = run["defaultDatasetId"]
        log.info(f"Dataset: https://console.apify.com/storage/datasets/{dataset_id}")

        items: list[dict[str, Any]] = list(
            self.client.dataset(dataset_id).iterate_items()
        )

        if self.output_format == "min":
            items = [self._minimize_item(i) for i in items]

        self._last_items = items
        log.info(f"Processed {len(items)} items")
        return items

    def get_last_items(self) -> list[dict[str, Any]] | None:
        """Get items from the last run (for API access)."""
        return self._last_items

    def run_query(self, query: QueryDefinition) -> list[dict[str, Any]]:
        """Run a query definition with caching."""
        # Try cache first
        if self._db:
            cached = self._db.get_cached_query(query.cache_key, self.output_format)
            if cached is not None:
                log.info(f"Cache hit for {query.type}, returning {len(cached)} items")
                self._last_items = cached
                return cached

        # Cache miss - call Apify
        log.info(f"Cache miss, calling Apify for {query.type}")
        run_dict = query.input.model_dump(exclude_none=True)
        run = self.client.actor(self.actor_id).call(run_input=run_dict)
        dataset_id = run["defaultDatasetId"]
        log.info(f"Dataset: https://console.apify.com/storage/datasets/{dataset_id}")

        items: list[dict[str, Any]] = list(
            self.client.dataset(dataset_id).iterate_items()
        )

        if self.output_format == "min":
            items = [self._minimize_item(i) for i in items]

        self._last_items = items

        # Save to cache
        if self._db:
            try:
                self._db.save_query_cache(
                    query_key=query.cache_key,
                    query_type=query.type,
                    params=run_dict,
                    items=items,
                    dataset_id=dataset_id,
                    output_format=self.output_format,
                )
                log.info(f"Saved {len(items)} items to cache")
            except Exception as e:
                log.warning(f"Failed to save to cache: {e}")

        log.info(f"Processed {len(items)} items")
        return items
