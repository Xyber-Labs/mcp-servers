"""
MCP-only router for transcript extraction - available only via MCP.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_youtube.dependencies import get_youtube_service
from mcp_server_youtube.schemas import (
    ExtractTranscriptsRequest,
    ExtractTranscriptsResponse,
    SearchRequest,
    SearchTranscriptsResponse,
    VideoResponse,
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


@router.post(
    "/search-transcripts",
    tags=["YouTube"],
    operation_id="search_and_extract_transcripts",
    response_model=SearchTranscriptsResponse,
)
async def search_and_extract_transcripts(
    request: SearchRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
) -> SearchTranscriptsResponse:
    """
    Search for YouTube videos and extract their transcripts.

    This premium tool is available only via MCP and requires x402 payment.
    It searches for videos and retrieves their transcripts with caching support.
    """
    try:
        logger.info(
            f"MCP: Search and extract transcripts - query: '{request.query}', num_videos: {request.num_videos}"
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


@router.post(
    "/extract-transcripts",
    tags=["YouTube"],
    operation_id="extract_transcripts",
    response_model=ExtractTranscriptsResponse,
)
async def extract_transcripts(
    request: ExtractTranscriptsRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
) -> ExtractTranscriptsResponse:
    """
    Extract transcripts for a given list of YouTube video IDs.

    This premium tool is available only via MCP and requires x402 payment.
    It fetches transcripts for the provided video IDs with caching support.
    """
    try:
        logger.info(f"MCP: Extract transcripts for {len(request.video_ids)} video IDs")

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

