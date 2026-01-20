"""
MCP router for transcript extraction - available via MCP and also accessible via REST API.
These endpoints are exposed as MCP tools and can also be called via REST at /api/*.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_youtube.dependencies import get_youtube_service, get_db_manager
from mcp_server_youtube.schemas import (
    ExtractTranscriptsRequest,
    ExtractTranscriptsResponse,
    SearchVideosRequest,
    SearchTranscriptsResponse,
    VideoResponse,
)
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript
from mcp_server_youtube.youtube.methods import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _process_video_transcript(
    video: any,
    service: YouTubeVideoSearchAndTranscript,
    db_manager: DatabaseManager,
    cached_transcripts: dict[str, bool],
    existing_videos: dict[str, bool],
) -> dict:
    """
    Process transcript for a single video (cached or fetch from API).
    
    This function is designed to be called in parallel for multiple videos.
    """
    video_id = video.video_id or video.id or video.display_id
    if not video_id:
        return None
    
    transcript_result = None
    cached_video = None
    
    # Check cache first
    if cached_transcripts.get(video_id, False):
        logger.info(f"💾 Loading transcript from cache for video {video_id}")
        cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
        if cached_video and cached_video.transcript_success and cached_video.transcript:
            transcript_result = {
                "success": cached_video.transcript_success,
                "transcript": cached_video.transcript,
                "transcript_length": cached_video.transcript_length,
                "is_generated": cached_video.is_auto_generated,
                "language": cached_video.language,
                "error": cached_video.error,
            }
    elif existing_videos.get(video_id, False):
        # Video exists in DB but transcript failed - load from cache to avoid retrying
        logger.info(f"💾 Loading failed transcript attempt from cache for video {video_id} - skipping retry")
        cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
        if cached_video:
            transcript_result = {
                "success": cached_video.transcript_success,
                "transcript": cached_video.transcript,
                "transcript_length": cached_video.transcript_length or 0,
                "is_generated": cached_video.is_auto_generated,
                "language": cached_video.language,
                "error": cached_video.error,
            }
    
    # Fetch from API if not cached
    if transcript_result is None:
        logger.info(f"🌐 Fetching transcript from API for video {video_id}")
        transcript_api_result = await service.get_transcript_safe(video_id)
        transcript_result = {
            "success": transcript_api_result.success,
            "transcript": transcript_api_result.transcript,
            "transcript_length": len(transcript_api_result.transcript) if transcript_api_result.transcript else 0,
            "is_generated": transcript_api_result.is_generated,
            "language": transcript_api_result.language,
            "error": transcript_api_result.error,
        }
        
        # Save to cache
        if transcript_result["success"]:
            video_data = {
                "video_id": video_id,
                "title": video.title or "Unknown",
                "channel": video.channel or video.uploader or "Unknown",
                "channel_id": video.channel_id,
                "channel_url": video.channel_url,
                "video_url": video.url or video.link or video.webpage_url or f"https://www.youtube.com/watch?v={video_id}",
                "duration": video.duration,
                "views": video.views or video.view_count,
                "likes": video.likes or video.like_count,
                "comments": video.comments or video.comment_count,
                "upload_date": video.upload_date,
                "description": video.description or "",
                "thumbnail": video.thumbnail,
                "transcript_success": transcript_result["success"],
                "transcript": transcript_result["transcript"],
                "transcript_length": transcript_result["transcript_length"],
                "error": transcript_result["error"],
                "is_auto_generated": transcript_result["is_generated"],
                "language": transcript_result["language"],
            }
            await asyncio.to_thread(db_manager.save_video, video_data)
    
    # Combine video and transcript data
    combined = {
        "title": video.title or "Unknown",
        "channel": video.channel or video.uploader or "Unknown",
        "channel_id": video.channel_id,
        "channel_url": video.channel_url,
        "video_url": video.url or video.link or video.webpage_url or f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
        "duration": video.duration,
        "views": video.views or video.view_count,
        "likes": video.likes or video.like_count,
        "comments": video.comments or video.comment_count,
        "upload_date": video.upload_date,
        "description": video.description or "",
        "thumbnail": video.thumbnail,
        "transcript_success": transcript_result["success"],
        "transcript": transcript_result["transcript"],
        "transcript_length": transcript_result["transcript_length"],
        "error": transcript_result["error"],
        "is_auto_generated": transcript_result["is_generated"],
        "language": transcript_result["language"],
    }
    return combined


async def _process_video_id_transcript(
    video_id: str,
    service: YouTubeVideoSearchAndTranscript,
    db_manager: DatabaseManager,
    cached_transcripts: dict[str, bool],
    existing_videos: dict[str, bool],
) -> dict:
    """
    Process transcript for a single video ID (cached or fetch from API).
    
    This function is designed to be called in parallel for multiple video IDs.
    """
    transcript_result = None
    cached_video = None
    
    if cached_transcripts.get(video_id, False):
        logger.info(f"💾 Loading transcript from cache for video {video_id}")
        cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
        if cached_video and cached_video.transcript_success and cached_video.transcript:
            transcript_result = {
                "success": cached_video.transcript_success,
                "transcript": cached_video.transcript,
                "transcript_length": cached_video.transcript_length,
                "is_generated": cached_video.is_auto_generated,
                "language": cached_video.language,
                "error": cached_video.error,
            }
    elif existing_videos.get(video_id, False):
        # Video exists in DB but transcript failed - load from cache to avoid retrying
        logger.info(f"💾 Loading failed transcript attempt from cache for video {video_id} - skipping retry")
        cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
        if cached_video:
            transcript_result = {
                "success": cached_video.transcript_success,
                "transcript": cached_video.transcript,
                "transcript_length": cached_video.transcript_length or 0,
                "is_generated": cached_video.is_auto_generated,
                "language": cached_video.language,
                "error": cached_video.error,
            }
    
    if transcript_result is None:
        logger.info(f"🌐 Fetching transcript from API for video {video_id}")
        transcript_api_result = await service.get_transcript_safe(video_id)
        transcript_result = {
            "success": transcript_api_result.success,
            "transcript": transcript_api_result.transcript,
            "transcript_length": len(transcript_api_result.transcript) if transcript_api_result.transcript else 0,
            "is_generated": transcript_api_result.is_generated,
            "language": transcript_api_result.language,
            "error": transcript_api_result.error,
        }
        
        # Save to cache (both successful and failed attempts to avoid retrying)
        video_data = {
            "video_id": video_id,
            "title": cached_video.title if cached_video else "Unknown",
            "channel": cached_video.channel if cached_video else "Unknown",
            "channel_id": cached_video.channel_id if cached_video else None,
            "channel_url": cached_video.channel_url if cached_video else None,
            "video_url": cached_video.video_url if cached_video else f"https://www.youtube.com/watch?v={video_id}",
            "duration": cached_video.duration if cached_video else None,
            "views": cached_video.views if cached_video else None,
            "likes": cached_video.likes if cached_video else None,
            "comments": cached_video.comments if cached_video else None,
            "upload_date": cached_video.upload_date if cached_video else None,
            "description": cached_video.description or "" if cached_video else "",
            "thumbnail": cached_video.thumbnail if cached_video else None,
            "transcript_success": transcript_result["success"],
            "transcript": transcript_result["transcript"] if transcript_result["success"] else None,
            "transcript_length": transcript_result["transcript_length"] if transcript_result["success"] else 0,
            "error": transcript_result["error"],
            "is_auto_generated": transcript_result["is_generated"],
            "language": transcript_result["language"],
        }
        saved = await asyncio.to_thread(db_manager.save_video, video_data)
        if saved:
            if transcript_result["success"]:
                logger.info(f"💾 Saved transcript to cache for video {video_id}")
            else:
                logger.info(f"💾 Cached failed transcript attempt for video {video_id} (error: {transcript_result.get('error')}) - will not retry")
        # Reload cached_video after saving
        cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
    
    # Use cached_video if available, otherwise use defaults
    combined = {
        "title": cached_video.title if cached_video else "Unknown",
        "channel": cached_video.channel if cached_video else "Unknown",
        "channel_id": cached_video.channel_id if cached_video else None,
        "channel_url": cached_video.channel_url if cached_video else None,
        "video_url": cached_video.video_url if cached_video else f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
        "duration": cached_video.duration if cached_video else None,
        "views": cached_video.views if cached_video else None,
        "likes": cached_video.likes if cached_video else None,
        "comments": cached_video.comments if cached_video else None,
        "upload_date": cached_video.upload_date if cached_video else None,
        "description": cached_video.description or "" if cached_video else "",
        "thumbnail": cached_video.thumbnail if cached_video else None,
        "transcript_success": transcript_result["success"],
        "transcript": transcript_result["transcript"],
        "transcript_length": transcript_result["transcript_length"],
        "error": transcript_result["error"],
        "is_auto_generated": transcript_result["is_generated"],
        "language": transcript_result["language"],
    }
    return combined


@router.post(
    "/search-transcripts",
    tags=["YouTube"],
    operation_id="search_and_extract_transcripts",
    response_model=SearchTranscriptsResponse,
)
async def search_and_extract_transcripts(
    request: SearchVideosRequest,
    service: YouTubeVideoSearchAndTranscript = Depends(get_youtube_service),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> SearchTranscriptsResponse:
    """
    Search for YouTube videos and extract their transcripts.

    Available via:
    - REST API: POST /api/search-transcripts
    - MCP: As a tool via /mcp endpoint

    This premium tool requires x402 payment when pricing is enabled.
    It searches for videos and retrieves their transcripts with caching support.
    """
    try:
        logger.info(
            f"MCP: Search and extract transcripts - query: '{request.query}', num_videos: {request.num_videos}"
        )

        # Check cache first
        try:
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
        except RuntimeError as e:
            error_msg = str(e)
            if "usage limit" in error_msg.lower():
                raise HTTPException(status_code=429, detail=error_msg)
            elif "authentication" in error_msg.lower() or "token" in error_msg.lower():
                raise HTTPException(status_code=401, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")

        video_ids = [v.video_id or v.id or v.display_id for v in videos if v.video_id or v.id or v.display_id]
        cached_transcripts = await asyncio.to_thread(db_manager.batch_check_transcripts, video_ids)
        existing_videos = await asyncio.to_thread(db_manager.batch_check_video_exists, video_ids)

        # Process all videos in parallel
        logger.info(f"🚀 Processing {len(videos)} videos in parallel for transcript extraction")
        tasks = [
            _process_video_transcript(video, service, db_manager, cached_transcripts, existing_videos)
            for video in videos
            if video.video_id or video.id or video.display_id
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions that occurred
        exceptions = [r for r in raw_results if isinstance(r, Exception)]
        if exceptions:
            logger.warning(f"⚠️ {len(exceptions)} exceptions occurred during parallel processing: {exceptions}")
        
        # Filter out None results and exceptions
        results = [r for r in raw_results if r is not None and not isinstance(r, Exception)]

        if not results:
            raise HTTPException(status_code=404, detail="No videos found")

        cached_count = sum(cached_transcripts.values())
        video_responses = [VideoResponse.from_video(video) for video in results]

        return SearchTranscriptsResponse(
            query=request.query,
            num_videos=request.num_videos,
            videos=video_responses,
            total_found=len(results),
            cached_count=cached_count,
        )
    except HTTPException:
        raise
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
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ExtractTranscriptsResponse:
    """
    Extract transcripts for a given list of YouTube video IDs.

    Available via:
    - REST API: POST /api/extract-transcripts
    - MCP: As a tool via /mcp endpoint

    This premium tool requires x402 payment when pricing is enabled.
    It fetches transcripts for the provided video IDs with caching support.
    """
    try:
        logger.info(f"MCP: Extract transcripts for {len(request.video_ids)} video IDs")

        cached_transcripts = await asyncio.to_thread(db_manager.batch_check_transcripts, request.video_ids)
        existing_videos = await asyncio.to_thread(db_manager.batch_check_video_exists, request.video_ids)

        # Process all video IDs in parallel
        logger.info(f"🚀 Processing {len(request.video_ids)} video IDs in parallel for transcript extraction")
        tasks = [
            _process_video_id_transcript(video_id, service, db_manager, cached_transcripts, existing_videos)
            for video_id in request.video_ids
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions that occurred
        exceptions = [r for r in raw_results if isinstance(r, Exception)]
        if exceptions:
            logger.warning(f"⚠️ {len(exceptions)} exceptions occurred during parallel processing: {exceptions}")
        
        # Filter out exceptions
        results = [r for r in raw_results if not isinstance(r, Exception)]

        if not results:
            raise HTTPException(status_code=404, detail="No transcripts could be extracted")

        cached_transcripts_after = await asyncio.to_thread(db_manager.batch_check_transcripts, request.video_ids)
        cached_count_after = sum(cached_transcripts_after.values())

        video_responses = [VideoResponse.from_video(video) for video in results]

        return ExtractTranscriptsResponse(
            video_ids=request.video_ids,
            videos=video_responses,
            total_processed=len(results),
            cached_count=cached_count_after,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in extract-transcripts endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

