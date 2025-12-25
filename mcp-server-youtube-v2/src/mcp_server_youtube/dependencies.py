"""
FastAPI dependencies for YouTube service.
"""

from fastapi import HTTPException

from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript, get_youtube_client


def get_youtube_service() -> YouTubeVideoSearchAndTranscript:
    """Dependency to get YouTube service instance."""
    try:
        return get_youtube_client()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_youtube_service_search_only() -> YouTubeVideoSearchAndTranscript:
    """Dependency to get YouTube service instance for search-only (no Apify required)."""
    from mcp_server_youtube.config import get_app_settings
    
    settings = get_app_settings()
    return YouTubeVideoSearchAndTranscript(
        delay_between_requests=settings.youtube.delay_between_requests,
        apify_api_token=None,
        require_apify=False,
    )

