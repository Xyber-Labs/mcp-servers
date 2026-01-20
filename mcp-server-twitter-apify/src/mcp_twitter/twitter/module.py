"""
This module should be changed to match the external twitter (or other) API you call, including any retry, caching, and client behavior specific to your use case.

Main responsibility: Implement the async TwitterClient and its factory, handling HTTP calls, retries, caching, and response parsing for twitter data.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from mcp_twitter.twitter.config import (
    TwitterConfig,
    get_twitter_config,
)
from mcp_twitter.twitter.errors import TwitterApiError, TwitterClientError
from mcp_twitter.twitter.models import TwitterData

# Import the existing scraper to wrap it
from mcp_twitter.twitter.scraper import TwitterScraper

# --- Logger Setup --- #

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_twitter_client() -> TwitterClient:
    """
    Get a cached instance of TwitterClient.

    Returns:
        Initialized TwitterClient instance

    Raises:
        TwitterConfigError: If configuration validation fails

    """
    config = get_twitter_config()
    return TwitterClient(config)


class TwitterClient:
    """
    Twitter client for fetching twitter data from Apify API.

    Handles interaction with the Apify API with retry logic and caching.
    Wraps the existing TwitterScraper for compatibility with the template structure.
    """

    def __init__(self, config: TwitterConfig) -> None:
        """
        Initialize the TwitterClient.

        Args:
            config: Twitter configuration settings

        Raises:
            TwitterConfigError: If configuration validation fails

        """
        self.config = config
        self._scraper: TwitterScraper | None = None
        logger.info("TwitterClient initialized")

    def _ensure_scraper(self) -> TwitterScraper:
        """
        Ensure the scraper is initialized.

        Returns:
            An active TwitterScraper instance.

        """
        if self._scraper is None:
            apify_token = self.config.apify_token
            if not apify_token:
                raise TwitterClientError(
                    "Twitter API key (apify_token) is not configured."
                )
            self._scraper = TwitterScraper(
                apify_token=apify_token,
                results_dir=None,
                actor_name=self.config.actor_name,
                output_format="min",
                use_cache=self.config.enable_caching,
            )
        return self._scraper

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        # The scraper doesn't have async cleanup, but we can clear the reference
        self._scraper = None

    async def get_twitter_data(
        self,
        query: Any,
        apify_token: str | None = None,
    ) -> TwitterData:
        """
        Get twitter data for a query.

        Args:
            query: Query definition for twitter search
            apify_token: Optional API token from request header (takes precedence over config)

        Returns:
            TwitterData object with twitter information

        Raises:
            TwitterApiError: If the API request fails
            TwitterClientError: If no API token is available from header or config

        """
        # Resolve API token: header takes precedence over config
        effective_token = apify_token or self.config.apify_token
        if not effective_token:
            raise TwitterClientError(
                "Twitter API token (apify_token) is not configured and was not provided."
            )

        # Update config if token was provided
        if apify_token:
            self.config.apify_token = apify_token

        try:
            scraper = self._ensure_scraper()
            # Run the query synchronously (scraper is sync)
            scraper.run_query(query)
            items = scraper.get_last_items() or []
            
            twitter_data = TwitterData.from_api_response(
                {"items": items},
                query_id=getattr(query, "id", ""),
                query_name=getattr(query, "name", ""),
            )

            logger.info(f"Successfully retrieved twitter data: {len(items)} items")
            return twitter_data

        except Exception as e:
            logger.error(f"Unexpected error getting twitter data: {e}", exc_info=True)
            raise TwitterClientError(
                f"Unexpected error getting twitter data: {e}"
            ) from e

