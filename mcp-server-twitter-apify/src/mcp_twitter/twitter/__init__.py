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
from mcp_twitter.twitter.models import TwitterData
from mcp_twitter.twitter.module import TwitterClient, get_twitter_client

__all__ = [
    "TwitterClient",
    "get_twitter_client",
    "TwitterConfig",
    "get_twitter_config",
    "TwitterApiError",
    "TwitterClientError",
    "TwitterConfigError",
    "TwitterData",
]

