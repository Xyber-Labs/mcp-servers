"""
FastAPI dependencies for YouTube service.
"""

from functools import lru_cache

from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript, get_youtube_client
from mcp_server_youtube.youtube.methods import DatabaseManager, get_db_manager as _get_db_manager


def get_youtube_service() -> YouTubeVideoSearchAndTranscript:
    """Dependency to get YouTube service instance."""
    return get_youtube_client()


def get_youtube_service_search_only() -> YouTubeVideoSearchAndTranscript:
    """Dependency to get YouTube service instance for search-only.
    
    Note: Search now requires Apify API token, so this uses the same service as get_youtube_service().
    """
    return get_youtube_client()


@lru_cache(maxsize=1)
def get_db_manager() -> DatabaseManager:
    """Dependency to get database manager instance."""
    # Delegates to youtube.methods.get_db_manager() which can fall back to a
    # NullDatabaseManager when Postgres is unavailable.
    return _get_db_manager()

