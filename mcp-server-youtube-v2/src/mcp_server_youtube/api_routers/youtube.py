"""
REST API endpoints for YouTube search and transcript extraction.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from mcp_server_youtube.dependencies import get_youtube_service, get_youtube_service_search_only
from mcp_server_youtube.schemas import (
    ExtractTranscriptsRequest,
    ExtractTranscriptsResponse,
    SearchRequest,
    SearchTranscriptsResponse,
    SearchOnlyRequest,
    SearchOnlyResponse,
    VideoResponse,
    VideoSearchResponse,
)
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript
from mcp_server_youtube.youtube.methods import get_db_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def format_video_response(video: dict, include_transcript_preview: bool = True) -> VideoResponse:
    """Format video dictionary to VideoResponse model."""
    transcript_preview = None
    if include_transcript_preview and video.get("transcript"):
        transcript_preview = (
            video["transcript"][:300] + "..."
            if len(video["transcript"]) > 300
            else video["transcript"]
        )

    return VideoResponse(
        title=video.get("title", "Unknown"),
        channel=video.get("channel", "Unknown"),
        channel_id=video.get("channel_id"),
        channel_url=video.get("channel_url"),
        video_url=video.get("video_url", ""),
        video_id=video.get("video_id", ""),
        duration=video.get("duration"),
        views=video.get("views"),
        likes=video.get("likes"),
        comments=video.get("comments"),
        upload_date=video.get("upload_date"),
        description=video.get("description"),
        thumbnail=video.get("thumbnail"),
        transcript_success=video.get("transcript_success", False),
        transcript=video.get("transcript"),
        transcript_length=video.get("transcript_length"),
        transcript_preview=transcript_preview,
        error=video.get("error"),
        is_auto_generated=video.get("is_auto_generated"),
        language=video.get("language"),
    )


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


@router.post("/search-transcripts", response_model=SearchTranscriptsResponse, tags=["Transcripts"], operation_id="api_search_and_extract_transcripts")
async def search_and_extract_transcripts(
    request: SearchRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
):
    """
    Search for YouTube videos and extract their transcripts.

    - **query**: Search query for YouTube videos
    - **num_videos**: Number of videos to process (1-50)

    Returns videos sorted by likes (highest first) with transcripts.
    Uses caching to avoid re-fetching transcripts that are already in the database.
    """
    try:
        logger.info(
            f"API: Search and extract transcripts - query: '{request.query}', num_videos: {request.num_videos}"
        )

        db_manager = get_db_manager()

        results = await service.search_and_get_transcripts(
            query=request.query, num_videos=request.num_videos
        )

        if not results:
            raise HTTPException(status_code=404, detail="No videos found")

        video_ids = [r.get("video_id") for r in results if r.get("video_id")]
        cached_transcripts = db_manager.batch_check_transcripts(video_ids)
        cached_count = sum(cached_transcripts.values())

        video_responses = [format_video_response(video) for video in results]

        return SearchTranscriptsResponse(
            query=request.query,
            num_videos=request.num_videos,
            videos=video_responses,
            total_found=len(results),
            cached_count=cached_count,
        )
    except Exception as e:
        logger.error(f"Error in search-transcripts endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-transcripts", response_model=ExtractTranscriptsResponse, tags=["Transcripts"], operation_id="api_extract_transcripts")
async def extract_transcripts(
    request: ExtractTranscriptsRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
):
    """
    Extract transcripts for a given list of YouTube video IDs.

    - **video_ids**: List of YouTube video IDs (1-50 IDs)

    Fetches transcripts for the provided video IDs without performing a search.
    Uses caching to avoid re-fetching transcripts that are already in the database.
    """
    try:
        logger.info(f"API: Extract transcripts for {len(request.video_ids)} video IDs")

        db_manager = get_db_manager()
        cached_transcripts = db_manager.batch_check_transcripts(request.video_ids)
        cached_count_before = sum(cached_transcripts.values())

        results = await service.extract_transcripts_for_video_ids(request.video_ids)

        if not results:
            raise HTTPException(status_code=404, detail="No transcripts could be extracted")

        cached_transcripts_after = db_manager.batch_check_transcripts(request.video_ids)
        cached_count_after = sum(cached_transcripts_after.values())

        video_responses = [format_video_response(video) for video in results]

        return ExtractTranscriptsResponse(
            video_ids=request.video_ids,
            videos=video_responses,
            total_processed=len(results),
            cached_count=cached_count_after,
        )
    except Exception as e:
        logger.error(f"Error in extract-transcripts endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract-transcript", response_model=VideoResponse, tags=["Transcripts"], operation_id="api_extract_single_transcript")
async def extract_single_transcript(
    video_id: str = Query(..., description="YouTube video ID"),
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
):
    """
    Extract transcript for a single YouTube video ID.

    - **video_id**: YouTube video ID (e.g., "dQw4w9WgXcQ")

    Fetches transcript for the provided video ID without performing a search.
    Uses caching to avoid re-fetching transcripts that are already in the database.
    """
    try:
        logger.info(f"API: Extract transcript for video ID: {video_id}")

        results = await service.extract_transcripts_for_video_ids([video_id])

        if not results:
            raise HTTPException(status_code=404, detail="No transcript could be extracted")

        video_response = format_video_response(results[0])

        return video_response
    except Exception as e:
        logger.error(f"Error in extract-transcript endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchOnlyResponse, tags=["Search"], operation_id="api_search_videos_only")
async def search_videos_only(
    request: SearchOnlyRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service_search_only),
):
    """
    Search for YouTube videos without extracting transcripts.

    - **query**: Search query for YouTube videos
    - **max_results**: Maximum number of videos to return (1-50)

    Returns videos sorted by likes (highest first) without transcripts.
    This endpoint does not require Apify API token.
    """
    try:
        logger.info(f"API: Search only - query: '{request.query}', max_results: {request.max_results}")

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

