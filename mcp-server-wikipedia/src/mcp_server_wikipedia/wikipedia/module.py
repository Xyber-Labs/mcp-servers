import logging
from functools import lru_cache
from typing import Any

import wikipediaapi

import wikipedia
from mcp_server_wikipedia.wikipedia.config import WikipediaConfig
from mcp_server_wikipedia.wikipedia.models import (
    ArticleNotFoundError,
    WikipediaAPIError,
    WikipediaConfigError,
)

logger = logging.getLogger(__name__)


class _WikipediaService:
    """Encapsulates Wikipedia client logic and configuration."""

    def __init__(self, config: WikipediaConfig):
        try:
            self.wiki = wikipediaapi.Wikipedia(
                user_agent=config.user_agent,
                language=config.language,
                extract_format=wikipediaapi.ExtractFormat.WIKI,
            )
            # Set up the wikipedia library for search functionality
            wikipedia.set_lang(config.language)
            wikipedia.set_user_agent(config.user_agent)
            self.config = config
            logger.info(
                f"WikipediaService initialized for language '{config.language}'."
            )
        except Exception as e:
            raise WikipediaConfigError(
                f"Failed to initialize Wikipedia API: {e}"
            ) from e

    def _get_page(self, title: str) -> wikipediaapi.WikipediaPage:
        """Fetches a page and raises an error if it doesn't exist."""
        page = self.wiki.page(title)
        if not page.exists():
            raise ArticleNotFoundError(title)
        return page

    async def search(self, query: str, limit: int = 10) -> list[str]:
        """Search Wikipedia for articles matching a query."""
        if not query:
            raise ValueError("Search query cannot be empty.")
        logger.info(f"Searching Wikipedia for: '{query}' with limit {limit}")
        try:
            # Use the wikipedia library for search functionality
            results = wikipedia.search(query, results=limit)
            return results
        except Exception as e:
            logger.error(
                f"Wikipedia search failed for query '{query}': {e}", exc_info=True
            )
            raise WikipediaAPIError(f"Wikipedia search failed: {e}") from e

    async def get_article(self, title: str) -> dict[str, Any]:
        """Get the full content and metadata of a Wikipedia article."""
        logger.info(f"Fetching full article for: '{title}'")
        page = self._get_page(title)
        return {
            "title": page.title,
            "summary": page.summary,
            "text": page.text,
            "url": page.fullurl,
            "sections": [s.title for s in page.sections],
            "links": list(page.links.keys()),
        }

    async def get_summary(self, title: str) -> str:
        """Get a summary of a Wikipedia article."""
        logger.info(f"Fetching summary for: '{title}'")
        page = self._get_page(title)
        return page.summary

    async def get_sections(self, title: str) -> list[str]:
        """Get the section titles of a Wikipedia article."""
        logger.info(f"Fetching sections for: '{title}'")
        page = self._get_page(title)
        return [s.title for s in page.sections]

    async def get_links(self, title: str) -> list[str]:
        """Get the links contained within a Wikipedia article."""
        logger.info(f"Fetching links for: '{title}'")
        page = self._get_page(title)
        return list(page.links.keys())

    async def get_related_topics(self, title: str, limit: int = 20) -> list[str]:
        """Get topics related to an article (based on its links)."""
        logger.info(f"Fetching related topics for: '{title}'")
        page = self._get_page(title)
        return list(page.links.keys())[:limit]


@lru_cache(maxsize=1)
def get_wikipedia_service() -> _WikipediaService:
    """Factory to get a singleton instance of the Wikipedia service."""
    config = WikipediaConfig()
    service = _WikipediaService(config=config)
    logger.info("Wikipedia service instance retrieved successfully.")
    return service
