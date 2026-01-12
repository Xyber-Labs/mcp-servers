"""
Hybrid router for YouTube search - available via both REST and MCP.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_youtube.dependencies import get_youtube_service_search_only
from mcp_server_youtube.schemas import (
    SearchVideosRequest,
    SearchOnlyResponse,
    VideoSearchResponse,
)
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search",
    tags=["YouTube"],
    operation_id="search_youtube_videos",
    response_model=SearchOnlyResponse,
)
async def search_youtube_videos(
    request: SearchVideosRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service_search_only),
) -> SearchOnlyResponse:
    """
    Search for YouTube videos without extracting transcripts.

    This endpoint is available to both REST API consumers and AI agents via MCP.
    It does not require Apify API token.
    """
    try:
        logger.info(f"Search only - query: '{request.query}', num_videos: {request.num_videos}")

        videos = await service.search_videos(
            request.query,
            max_results=request.num_videos,
            exclude_shorts=request.exclude_shorts,
            shorts_only=request.shorts_only,
            upload_date_filter=request.upload_date_filter,
            sort_by=request.sort_by,
            sleep_interval=request.sleep_interval,
            max_retries=request.max_retries,
        )

        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")

        video_responses = [VideoSearchResponse.from_video(video.model_dump()) for video in videos]

        return SearchOnlyResponse(
            query=request.query,
            max_results=request.num_videos,
            num_videos=request.num_videos,
            videos=video_responses,
            total_found=len(videos),
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        error_msg = str(e)
        if "usage limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail=error_msg)
        elif "authentication" in error_msg.lower() or "token" in error_msg.lower():
            raise HTTPException(status_code=401, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

