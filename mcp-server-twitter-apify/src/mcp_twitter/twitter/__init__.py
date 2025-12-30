"""
This module should be changed to fit your domain-specific service layer, using it as a central place to expose clients, configuration, errors, and models.

Main responsibility: Provide a public facade for the twitter service by re-exporting the client, configuration helpers, error types, and data models.
"""

from mcp_twitter.twitter.config import (
    TwitterConfig,
    get_twitter_config,
)
from mcp_twitter.twitter.errors import (
    TwitterApiError,
    TwitterClientError,
    TwitterConfigError,
)
from mcp_twitter.twitter.models import (
    MinimalTweet,
    OutputFormat,
    QueryDefinition,
    QueryType,
    SortOrder,
    TwitterScraperInput,
)
from mcp_twitter.twitter.module import TwitterClient, TwitterData, get_twitter_client
from mcp_twitter.twitter.queries import (
    build_default_registry,
    create_profile_query,
    create_replies_query,
    create_topic_query,
)
from mcp_twitter.twitter.registry import QueryRegistry
from mcp_twitter.twitter.scraper import TwitterScraper

__all__ = [
    "TwitterClient",
    "get_twitter_client",
    "TwitterConfig",
    "get_twitter_config",
    "TwitterApiError",
    "TwitterClientError",
    "TwitterConfigError",
    "TwitterData",
    # Re-export models, queries, registry, scraper for backward compatibility
    "QueryType",
    "SortOrder",
    "OutputFormat",
    "TwitterScraperInput",
    "QueryDefinition",
    "MinimalTweet",
    "QueryRegistry",
    "build_default_registry",
    "create_profile_query",
    "create_replies_query",
    "create_topic_query",
    "TwitterScraper",
]

