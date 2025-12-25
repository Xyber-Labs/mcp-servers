"""
YouTube client for searching videos and retrieving transcripts.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from datetime import datetime

import yt_dlp
from apify_client import ApifyClient

from mcp_server_youtube.config import get_app_settings
import logging

logger = logging.getLogger(__name__)
from mcp_server_youtube.youtube.methods import get_db_manager

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_youtube_client() -> YouTubeVideoSearchAndTranscript:
    """
    Get a cached instance of YouTubeVideoSearchAndTranscript.

    Returns:
        Initialized YouTubeVideoSearchAndTranscript instance
    """
    settings = get_app_settings()
    return YouTubeVideoSearchAndTranscript(
        delay_between_requests=settings.youtube.delay_between_requests,
        apify_api_token=settings.apify.apify_token,
    )


class YouTubeVideoSearchAndTranscript:
    """Search for videos and retrieve their transcripts using Apify."""

    def __init__(
        self,
        delay_between_requests: float | None = None,
        apify_api_token: str | None = None,
        require_apify: bool = True,
    ):
        """
        Args:
            delay_between_requests: Seconds to wait between API calls. Defaults to config value.
            apify_api_token: Apify API token. Defaults to config value if not provided.
            require_apify: If False, skip Apify initialization (for search-only mode).
        """
        settings = get_app_settings()
        self.delay = delay_between_requests or settings.youtube.delay_between_requests
        self.apify_api_token = (
            apify_api_token
            or settings.apify.apify_token
            or os.getenv("APIFY_TOKEN")
            or os.getenv("APIFY_API_TOKEN")
        )

        if require_apify and not self.apify_api_token:
            raise ValueError(
                "Apify API token is required. "
                "Provide it via apify_api_token parameter, set APIFY_TOKEN in .env file, "
                "or set APIFY_API_TOKEN environment variable."
            )

        if self.apify_api_token:
            self.apify_client = ApifyClient(self.apify_api_token)
        else:
            self.apify_client = None

        logger.info("YouTubeVideoSearchAndTranscript initialized")

    async def search_videos(self, query: str, max_results: int | None = None) -> list:
        """
        Search YouTube for videos matching a query using yt-dlp.

        Args:
            query: Search topic (e.g., "quantum computing")
            max_results: Number of videos to return (defaults to config value)

        Returns:
            List of video dictionaries with enhanced metadata
        """
        settings = get_app_settings()
        if max_results is None:
            max_results = settings.youtube.max_results

        try:

            def search_with_ytdlp():
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": False,
                    "default_search": "ytsearch",
                    "noplaylist": True,
                    "writesubtitles": False,
                    "writeautomaticsub": False,
                    "skip_download": True,
                }

                results = []
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    search_query = f"ytsearch{max_results}:{query}"
                    search_results = ydl.extract_info(search_query, download=False)

                    entries = search_results.get("entries", [])
                    if not entries:
                        return results

                    for entry in entries:
                        if entry is None:
                            continue

                        video_id = entry.get("id") or entry.get("display_id")
                        if not video_id:
                            continue

                        upload_date = entry.get("upload_date")
                        if upload_date:
                            try:
                                upload_date_obj = datetime.strptime(upload_date, "%Y%m%d")
                                upload_date = upload_date_obj.strftime("%Y-%m-%d")
                            except (ValueError, TypeError):
                                pass

                        video_data = {
                            "id": video_id,
                            "video_id": video_id,
                            "title": entry.get("title", "Unknown"),
                            "channel": entry.get("channel", entry.get("uploader", "Unknown")),
                            "channel_id": entry.get("channel_id"),
                            "url": entry.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}"),
                            "link": entry.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}"),
                            "link_suffix": f"/watch?v={video_id}",
                            "duration": entry.get("duration"),
                            "views": entry.get("view_count"),
                            "likes": entry.get("like_count"),
                            "comments": entry.get("comment_count"),
                            "upload_date": upload_date,
                            "description": entry.get("description", ""),
                            "thumbnail": entry.get(
                                "thumbnail",
                                entry.get("thumbnails", [{}])[0].get("url", "")
                                if entry.get("thumbnails")
                                else "",
                            ),
                            "channel_url": entry.get("channel_url", ""),
                            "uploader": entry.get("uploader", ""),
                            "uploader_id": entry.get("uploader_id", ""),
                        }
                        results.append(video_data)

                return results

            results = await asyncio.to_thread(search_with_ytdlp)
            results.sort(key=lambda x: x.get("likes") or 0, reverse=True)
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_transcript_safe(
        self, video_id: str, language: str = "en", max_retries: int = 0
    ) -> dict:
        """Get transcript using Apify YouTube Transcript Scraper with error handling."""
        if not self.apify_client:
            return {
                "success": False,
                "video_id": video_id,
                "error": "Apify client not initialized",
            }

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        for attempt in range(max_retries + 1):
            try:
                run = await asyncio.to_thread(
                    lambda: self.apify_client.actor(
                        "pintostudio/youtube-transcript-scraper"
                    ).call(run_input={"videoUrl": video_url})
                )

                def get_dataset_items():
                    items = []
                    for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                        items.append(item)
                    return items

                dataset_items = await asyncio.to_thread(get_dataset_items)

                if not dataset_items:
                    raise Exception("No transcript data returned from Apify")

                result = dataset_items[0]
                transcript_segments = result.get("data", [])

                if not isinstance(transcript_segments, list):
                    if isinstance(result, list):
                        transcript_segments = result
                    else:
                        for key, value in result.items():
                            if isinstance(value, list) and len(value) > 0:
                                if isinstance(value[0], dict) and "text" in value[0]:
                                    transcript_segments = value
                                    break

                if not transcript_segments or not isinstance(transcript_segments, list):
                    raise Exception("No transcript segments found in Apify response")

                text_parts = []
                for segment in transcript_segments:
                    if isinstance(segment, dict):
                        text = segment.get("text", "").strip()
                        if text:
                            text_parts.append(text)
                    elif isinstance(segment, str):
                        text_parts.append(segment.strip())

                transcript_text = " ".join(text_parts)

                if not transcript_text:
                    raise Exception("Could not extract text from transcript segments")

                return {
                    "success": True,
                    "video_id": video_id,
                    "transcript": transcript_text,
                    "is_generated": None,
                    "language": language,
                }

            except Exception as e:
                if attempt == max_retries:
                    error_msg = str(e)
                    if "No transcript" in error_msg or "not available" in error_msg.lower():
                        error_msg = "No subtitles available for this video"
                    elif "API token" in error_msg or "authentication" in error_msg.lower():
                        error_msg = "Apify API authentication failed. Check your API token."
                    elif len(error_msg) > 200:
                        error_msg = error_msg[:200] + "..."

                    return {
                        "success": False,
                        "video_id": video_id,
                        "error": error_msg,
                    }
                wait_time = self.delay * (2 ** attempt)
                await asyncio.sleep(wait_time)

        return {"success": False, "video_id": video_id, "error": "Unknown error"}

    async def search_and_get_transcripts(
        self, query: str, num_videos: int | None = None
    ) -> list:
        """
        Search for videos and retrieve their transcripts.
        Checks database cache before fetching transcripts.

        Args:
            query: Search topic
            num_videos: Number of videos to process (defaults to config value)

        Returns:
            List of results with video info and transcripts
        """
        settings = get_app_settings()
        if num_videos is None:
            num_videos = settings.youtube.num_videos

        logger.info(f"Searching for: '{query}'")
        videos = await self.search_videos(query, max_results=num_videos)

        if not videos:
            logger.warning("No videos found")
            return []

        db_manager = get_db_manager()

        video_ids = []
        for video in videos:
            video_id = (
                video.get("id")
                or video.get("video_id")
                or video.get("link_suffix", "").lstrip("/watch?v=")
            )
            if video_id:
                video_ids.append(video_id)

        cached_transcripts = await asyncio.to_thread(
            db_manager.batch_check_transcripts, video_ids
        )

        results = []
        for i, video in enumerate(videos, 1):
            video_id = (
                video.get("id")
                or video.get("video_id")
                or video.get("link_suffix", "").lstrip("/watch?v=")
            )

            if not video_id:
                logger.warning("Skipping video: Could not find video ID")
                continue

            transcript_result = None
            if cached_transcripts.get(video_id, False):
                logger.info(f"Loading transcript from cache for video {video_id}")
                cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
                if cached_video:
                    transcript_result = {
                        "success": cached_video.transcript_success,
                        "video_id": video_id,
                        "transcript": cached_video.transcript,
                        "transcript_length": cached_video.transcript_length,
                        "is_generated": cached_video.is_auto_generated,
                        "language": cached_video.language,
                        "error": cached_video.error,
                    }

            if transcript_result is None:
                logger.info(f"Fetching transcript from API for video {video_id}")
                transcript_result = await self.get_transcript_safe(video_id)

                if transcript_result.get("transcript"):
                    transcript_result["transcript_length"] = len(
                        transcript_result["transcript"]
                    )
                else:
                    transcript_result["transcript_length"] = 0

            video_url = (
                video.get("url")
                or video.get("link")
                or video.get("link_suffix")
                or f"https://www.youtube.com/watch?v={video_id}"
            )

            channel = (
                video.get("channel")
                or video.get("channel_name")
                or video.get("channelTitle")
                or video.get("uploader", "Unknown")
            )

            transcript_text = transcript_result.get("transcript", "")
            transcript_length = len(transcript_text) if transcript_text else 0

            combined = {
                "title": video.get("title", "Unknown"),
                "channel": channel,
                "channel_id": video.get("channel_id"),
                "channel_url": video.get("channel_url"),
                "video_url": video_url,
                "video_id": video_id,
                "duration": video.get("duration"),
                "views": video.get("views"),
                "likes": video.get("likes"),
                "comments": video.get("comments"),
                "upload_date": video.get("upload_date"),
                "description": video.get("description", ""),
                "thumbnail": video.get("thumbnail"),
                "transcript_success": transcript_result["success"],
                "transcript": transcript_text,
                "transcript_length": transcript_length,
                "error": transcript_result.get("error", None),
                "is_auto_generated": transcript_result.get("is_generated", None),
                "language": transcript_result.get("language", None),
            }
            results.append(combined)

            video_data = {
                "video_id": video_id,
                "title": combined["title"],
                "channel": combined["channel"],
                "channel_id": combined["channel_id"],
                "channel_url": combined["channel_url"],
                "video_url": combined["video_url"],
                "duration": combined["duration"],
                "views": combined["views"],
                "likes": combined["likes"],
                "comments": combined["comments"],
                "upload_date": combined["upload_date"],
                "description": combined["description"],
                "thumbnail": combined["thumbnail"],
                "transcript_success": combined["transcript_success"],
                "transcript": combined["transcript"],
                "transcript_length": combined["transcript_length"],
                "error": combined["error"],
                "is_auto_generated": combined["is_auto_generated"],
                "language": combined["language"],
            }
            await asyncio.to_thread(db_manager.save_video, video_data)

            if not cached_transcripts.get(video_id, False) and i < len(videos):
                await asyncio.sleep(self.delay)

        return results

    async def extract_transcripts_for_video_ids(self, video_ids: list) -> list:
        """
        Extract transcripts for a given list of video IDs.
        Checks database cache before fetching transcripts.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            List of results with video info and transcripts
        """
        if not video_ids:
            logger.warning("No video IDs provided")
            return []

        logger.info(f"Extracting transcripts for {len(video_ids)} video IDs")

        db_manager = get_db_manager()
        cached_transcripts = await asyncio.to_thread(
            db_manager.batch_check_transcripts, video_ids
        )

        results = []
        for i, video_id in enumerate(video_ids, 1):
            transcript_result = None
            cached_video = None

            if cached_transcripts.get(video_id, False):
                logger.info(f"Loading transcript from cache for video {video_id}")
                cached_video = await asyncio.to_thread(db_manager.get_video, video_id)
                if cached_video:
                    transcript_result = {
                        "success": cached_video.transcript_success,
                        "video_id": video_id,
                        "transcript": cached_video.transcript,
                        "transcript_length": cached_video.transcript_length,
                        "is_generated": cached_video.is_auto_generated,
                        "language": cached_video.language,
                        "error": cached_video.error,
                    }

            if transcript_result is None:
                logger.info(f"Fetching transcript from API for video {video_id}")
                transcript_result = await self.get_transcript_safe(video_id)

                if transcript_result.get("transcript"):
                    transcript_result["transcript_length"] = len(
                        transcript_result["transcript"]
                    )
                else:
                    transcript_result["transcript_length"] = 0

            if cached_video:
                combined = {
                    "title": cached_video.title or "Unknown",
                    "channel": cached_video.channel or "Unknown",
                    "channel_id": cached_video.channel_id,
                    "channel_url": cached_video.channel_url,
                    "video_url": cached_video.video_url
                    or f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                    "duration": cached_video.duration,
                    "views": cached_video.views,
                    "likes": cached_video.likes,
                    "comments": cached_video.comments,
                    "upload_date": cached_video.upload_date,
                    "description": cached_video.description or "",
                    "thumbnail": cached_video.thumbnail,
                    "transcript_success": transcript_result["success"],
                    "transcript": transcript_result.get("transcript", ""),
                    "transcript_length": transcript_result.get("transcript_length", 0),
                    "error": transcript_result.get("error", None),
                    "is_auto_generated": transcript_result.get("is_generated", None),
                    "language": transcript_result.get("language", None),
                }
            else:
                combined = {
                    "title": "Unknown",
                    "channel": "Unknown",
                    "channel_id": None,
                    "channel_url": None,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                    "duration": None,
                    "views": None,
                    "likes": None,
                    "comments": None,
                    "upload_date": None,
                    "description": "",
                    "thumbnail": None,
                    "transcript_success": transcript_result["success"],
                    "transcript": transcript_result.get("transcript", ""),
                    "transcript_length": transcript_result.get("transcript_length", 0),
                    "error": transcript_result.get("error", None),
                    "is_auto_generated": transcript_result.get("is_generated", None),
                    "language": transcript_result.get("language", None),
                }

            results.append(combined)

            video_data = {
                "video_id": video_id,
                "title": combined["title"],
                "channel": combined["channel"],
                "channel_id": combined["channel_id"],
                "channel_url": combined["channel_url"],
                "video_url": combined["video_url"],
                "duration": combined["duration"],
                "views": combined["views"],
                "likes": combined["likes"],
                "comments": combined["comments"],
                "upload_date": combined["upload_date"],
                "description": combined["description"],
                "thumbnail": combined["thumbnail"],
                "transcript_success": combined["transcript_success"],
                "transcript": combined["transcript"],
                "transcript_length": combined["transcript_length"],
                "error": combined["error"],
                "is_auto_generated": combined["is_auto_generated"],
                "language": combined["language"],
            }
            await asyncio.to_thread(db_manager.save_video, video_data)

            if not cached_transcripts.get(video_id, False) and i < len(video_ids):
                await asyncio.sleep(self.delay)

        return results

