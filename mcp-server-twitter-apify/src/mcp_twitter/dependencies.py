from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp_twitter.twitter import TwitterScraper

if TYPE_CHECKING:
    from mcp_twitter.db import CacheRepository

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for application dependencies.

    Usage:
        # In app.py lifespan:
        db = try_init_database()  # May return None
        DependencyContainer.create(apify_token=token, actor_name=name, database=db)
        yield
        DependencyContainer.clear()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(
            scraper: TwitterScraper = Depends(get_scraper),
        ):
            ...

    """

    _scraper: TwitterScraper | None = None
    _database: CacheRepository | None = None

    @classmethod
    def create(
        cls, *, apify_token: str, actor_name: str, database: CacheRepository | None = None
    ) -> None:
        """Store all dependencies (call from lifespan startup)."""
        logger.info("Initializing dependencies...")

        cls._database = database

        cls._scraper = TwitterScraper(
            apify_token=apify_token,
            actor_name=actor_name,
            output_format="min",
            database=database,
        )

        logger.info("Dependencies initialized successfully.")

    @classmethod
    def clear(cls) -> None:
        """Clear all dependencies (call from lifespan shutdown)."""
        logger.info("Shutting down dependencies...")

        cls._scraper = None
        cls._database = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_scraper(cls) -> TwitterScraper:
        """
        Get the TwitterScraper instance.

        Usage as FastAPI dependency:
            @router.post("/search")
            async def search(scraper: TwitterScraper = Depends(get_scraper)):
                ...
        """
        if cls._scraper is None:
            raise RuntimeError(
                "DependencyContainer not created. Call DependencyContainer.create() first."
            )
        return cls._scraper


# Alias the class method for use as FastAPI dependency
get_scraper = DependencyContainer.get_scraper
