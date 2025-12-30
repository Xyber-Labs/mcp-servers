"""
This module should be changed as you add or modify dependencies for your own business logic, while keeping the pattern of thin wrappers around shared clients.

Main responsibility: Provide FastAPI dependency functions that expose shared service clients to routers and tools.
"""

from fastapi import Request

from mcp_twitter.twitter import TwitterClient
from mcp_twitter.twitter import get_twitter_client as _get_twitter_client


def get_twitter_client(request: Request) -> TwitterClient:
    """
    Dependency to get the TwitterClient instance.

    For this template we use the globally cached TwitterClient provided by the
    twitter module so that both REST and MCP calls share the same client.
    """
    return _get_twitter_client()

