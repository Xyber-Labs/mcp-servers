from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apify_client import ApifyClient

import logging

from mcp_twitter.config import AppSettings
from mcp_twitter.twitter.models import OutputFormat, QueryDefinition, QueryType, TwitterScraperInput

# Import moved to _get_db method to avoid circular import

log = logging.getLogger(__name__)


class TwitterScraper:
    """
    Thin wrapper around Apify runs + Postgres cache.

    Replaces file-based storage with database-backed caching to reduce Apify API costs.
    """

    def __init__(
        self,
        apify_token: str,
        results_dir: Path | None = None,  # Deprecated: kept for backward compatibility
        actor_name: str | None = None,
        output_format: OutputFormat = "min",
        use_cache: bool = True,
    ):
        # Use config actor_name if not provided
        if actor_name is None:
            settings = AppSettings()
            actor_name = settings.apify.actor_name
        
        self.apify_token = apify_token
        self.client = ApifyClient(apify_token)
        self.actor_id = actor_name  # Internal name remains actor_id for Apify client
        self.output_format: OutputFormat = output_format
        self.use_cache = use_cache
        
        # Database instance (lazy-loaded)
        self._db: "Database | None" = None
        
        # Store last run items for API access
        self._last_items: list[dict[str, Any]] | None = None
        
        # Legacy file support (deprecated)
        if results_dir:
            self.results_dir = results_dir
            self.results_dir.mkdir(exist_ok=True)
        else:
            self.results_dir = None

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

    def _get_db(self) -> "Database | None":
        """Get database instance, initializing if needed."""
        if not self.use_cache:
            return None
        if self._db is None:
            try:
                from db import Database, get_db_instance
                self._db = get_db_instance()
            except Exception as e:
                log.warning(f"Failed to initialize database cache: {e}")
                return None
        return self._db

    def run(
        self,
        run_input: TwitterScraperInput,
        output_filename: str | None = None,
        query_type: QueryType | None = None,
    ) -> Path:
        """
        Run Apify query with caching support.

        Args:
            run_input: Apify input parameters
            output_filename: Legacy filename (deprecated, kept for compatibility)
            query_type: Query type for cache key generation (topic/profile/replies)

        Returns:
            Path object (for backward compatibility, but data is stored in DB)
        """
        db = self._get_db()
        run_dict: dict[str, Any] = run_input.model_dump(exclude_none=True)
        
        # Try cache first if enabled
        if db and query_type:
            from db import generate_query_key
            query_key = generate_query_key(query_type, run_dict)
            cached_items = db.get_cached_query(query_key, self.output_format)
            if cached_items is not None:
                log.info(f"Cache hit for query_type={query_type}, returning {len(cached_items)} items")
                self._last_items = cached_items
                # Still write to file for backward compatibility if results_dir exists
                if self.results_dir and output_filename:
                    filename = output_filename if output_filename.endswith(".json") else f"{output_filename}.json"
                    output_path = self.results_dir / filename
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(cached_items, f, indent=2, ensure_ascii=False)
                    return output_path
                # Return a dummy path if no file writing
                return Path(output_filename or "cached_results.json")
        
        # Cache miss or cache disabled - call Apify
        log.info(f"Cache miss or cache disabled, calling Apify for query_type={query_type}")
        run = self.client.actor(self.actor_id).call(run_input=run_dict)
        dataset_id = run["defaultDatasetId"]
        print("💾 Dataset:", f"https://console.apify.com/storage/datasets/{dataset_id}")

        items: list[dict[str, Any]] = []
        for item in self.client.dataset(dataset_id).iterate_items():
            items.append(item)

        # Apply format transformation
        if self.output_format == "min":
            items = [self._minimize_item(i) for i in items]

        # Store items for API access
        self._last_items = items

        # Save to cache if enabled
        if db and query_type:
            try:
                from db import generate_query_key
                db.save_query_cache(
                    query_key=generate_query_key(query_type, run_dict),
                    query_type=query_type,
                    params=run_dict,
                    items=items,
                    dataset_id=dataset_id,
                    output_format=self.output_format,
                )
                log.info(f"Saved {len(items)} items to cache")
            except Exception as e:
                log.warning(f"Failed to save to cache: {e}")

        # Legacy file writing (deprecated)
        if self.results_dir:
            filename = output_filename or "results.json"
            if not filename.endswith(".json"):
                filename += ".json"
            output_path = self.results_dir / filename
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(items)} items to: {output_path}")
            return output_path

        # Return dummy path if no file writing
        dummy_path = Path(output_filename or "results.json")
        print(f"✅ Processed {len(items)} items (cached in database)")
        return dummy_path

    def get_last_items(self) -> list[dict[str, Any]] | None:
        """Get items from the last run (for API access)."""
        return self._last_items

    def run_query(self, query: QueryDefinition) -> Path:
        """Run a query definition with caching."""
        return self.run(query.input, query.output_filename(), query_type=query.type)


