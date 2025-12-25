"""
MCP router for YouTube search - available via MCP and also accessible via REST API.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_youtube.dependencies import get_youtube_service_search_only
from mcp_server_youtube.schemas import (
    SearchOnlyRequest,
    SearchOnlyResponse,
    VideoSearchResponse,
)
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript

logger = logging.getLogger(__name__)
router = APIRouter()


def format_video_search_response(video: dict) -> VideoSearchResponse:
    """Format video dictionary to VideoSearchResponse model."""
    return VideoSearchResponse(
        title=video.get("title", "Unknown"),
        channel=video.get("channel", "Unknown"),
        channel_id=video.get("channel_id"),
        channel_url=video.get("channel_url"),
        video_url=video.get("url")
        or video.get("link")
        or f"https://www.youtube.com/watch?v={video.get('id') or video.get('video_id')}",
        video_id=video.get("id") or video.get("video_id", ""),
        duration=video.get("duration"),
        views=video.get("views"),
        likes=video.get("likes"),
        comments=video.get("comments"),
        upload_date=video.get("upload_date"),
        description=video.get("description"),
        thumbnail=video.get("thumbnail"),
    )


@router.post(
    "/search",
    tags=["YouTube"],
    operation_id="mcp_search_youtube_videos",
    response_model=SearchOnlyResponse,
)
async def search_youtube_videos(
    request: SearchOnlyRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service_search_only),
) -> SearchOnlyResponse:
    """
    Search for YouTube videos without extracting transcripts.

    Available via:
    - REST API: POST /api/v1/search
    - Hybrid: POST /hybrid/search
    - MCP: As a tool via /mcp endpoint

    This endpoint does not require Apify API token.
    """
    try:
        logger.info(f"MCP: Search only - query: '{request.query}', max_results: {request.max_results}")

        videos = await service.search_videos(request.query, max_results=request.max_results)

        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")

        video_responses = [format_video_search_response(video) for video in videos]

        return SearchOnlyResponse(
            query=request.query,
            max_results=request.max_results,
            videos=video_responses,
            total_found=len(videos),
        )
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

