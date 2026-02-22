"""Wikipedia client module for the MCP server."""

from mcp_server_wikipedia.wikipedia.config import WikipediaConfig
from mcp_server_wikipedia.wikipedia.models import (
    ArticleNotFoundError,
    WikipediaAPIError,
    WikipediaConfigError,
    WikipediaServiceError,
)
from mcp_server_wikipedia.wikipedia.module import (
    _WikipediaService,
    get_wikipedia_service,
)

__all__ = [
    "_WikipediaService",
    "get_wikipedia_service",
    "WikipediaConfig",
    "WikipediaServiceError",
    "WikipediaConfigError",
    "WikipediaAPIError",
    "ArticleNotFoundError",
]
