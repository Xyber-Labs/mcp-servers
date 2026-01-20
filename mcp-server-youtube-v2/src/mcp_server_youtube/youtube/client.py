"""
YouTube client for searching videos and retrieving transcripts.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from datetime import datetime

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

from mcp_server_youtube.config import get_app_settings
from mcp_server_youtube.youtube.api_models import YouTubeSearchResult, ApifyTranscriptResult

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
                          Note: Search now requires Apify, so this only affects transcript extraction.
        """
        settings = get_app_settings()
        self.delay = delay_between_requests or settings.youtube.delay_between_requests
        
        # Rely on Pydantic BaseSettings - no hidden logic
        if apify_api_token is not None:
            self.apify_api_token = apify_api_token
        else:
            self.apify_api_token = settings.apify.apify_token

        if require_apify and not self.apify_api_token:
            # Keep initialization non-fatal so the server can still run for
            # request validation (422) isn't masked by dependency resolution errors in tests.
            logger.warning(
                "Apify API token is not configured. Search and transcript features will be unavailable. "
                "Set APIFY_TOKEN in your environment to enable YouTube search and transcript extraction."
            )

        if self.apify_api_token:
            self.apify_client = ApifyClient(self.apify_api_token)
        else:
            self.apify_client = None

        logger.info("YouTubeVideoSearchAndTranscript initialized")

    def _video_id_from(self, video) -> str | None:
        if isinstance(video, dict):
            return video.get("video_id") or video.get("id") or video.get("display_id")
        return getattr(video, "video_id", None) or getattr(video, "id", None) or getattr(video, "display_id", None)

    def _video_field(self, video, field: str, default=None):
        if isinstance(video, dict):
            return video.get(field, default)
        return getattr(video, field, default)

    def _transcript_field(self, transcript_result, field: str, default=None):
        if isinstance(transcript_result, dict):
            return transcript_result.get(field, default)
        # ApifyTranscriptResult is made dict-like in api_models.py, so __getitem__ works too.
        return getattr(transcript_result, field, default)

    async def search_videos(
        self,
        query: str,
        max_results: int | None = None,
        exclude_shorts: bool = False,
        shorts_only: bool = False,
        upload_date_filter: str = "",
        sort_by: str = "relevance",
        sleep_interval: int = 2,
        max_retries: int = 3,
    ) -> list[YouTubeSearchResult]:
        """
        Search YouTube for videos matching a query using Apify YouTube Search actor.

        Args:
            query: Search topic (e.g., "quantum computing")
            max_results: Number of videos to return (defaults to config value)
            exclude_shorts: Exclude YouTube Shorts from results
            shorts_only: Return only YouTube Shorts
            upload_date_filter: Filter by upload date (e.g., 'today', 'week', 'month', 'year')
            sort_by: Sort order: 'relevance', 'rating', 'upload_date', 'view_count'
            sleep_interval: Sleep interval between requests (seconds)
            max_retries: Maximum number of retries for failed requests

        Returns:
            List of YouTubeSearchResult BaseModels
        """
        settings = get_app_settings()
        if max_results is None:
            max_results = settings.youtube.max_results

        if not self.apify_client:
            logger.error("❌ Apify client not initialized. APIFY_TOKEN is required for search.")
            return []

        actor_id = "qoA27OkGHoMSJGBtf"
        logger.info(f"🔍 Searching YouTube for: '{query}' (max_results: {max_results})")
        logger.info(f"📡 Using Apify Actor: {actor_id} (maged120/youtube-search)")

        try:
            # Prepare the Actor input
            run_input = {
                "query": query,
                "max_results": max_results,
                "shorts_only": shorts_only,
                "exclude_shorts": exclude_shorts,
                "upload_date_filter": upload_date_filter,
                "sort_by": sort_by,
                "sleep_interval": sleep_interval,
                "max_retries": max_retries,
            }
            logger.debug(f"📤 Actor input: {run_input}")

            # Run the Actor and wait for it to finish
            def run_apify_search():
                logger.info(f"🚀 Calling Apify Actor: {actor_id}")
                run = self.apify_client.actor(actor_id).call(run_input=run_input)
                
                # Fetch Actor results from the run's dataset
                items = []
                for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)
                return items

            dataset_items = await asyncio.to_thread(run_apify_search)

            if not dataset_items:
                logger.warning("No video entries found in search results")
                return []

            logger.info(f"Found {len(dataset_items)} video entries, processing...")

            results = []
            for item in dataset_items:
                if not item:
                    continue

                # Map Apify response fields to YouTubeSearchResult format
                # Apify response format may vary, so we handle multiple possible field names
                video_id = item.get("videoId") or item.get("video_id") or item.get("id")
                if not video_id:
                    continue

                # Extract video URL
                video_url = item.get("url") or item.get("videoUrl") or f"https://www.youtube.com/watch?v={video_id}"

                # Normalize upload_date format if present
                upload_date = item.get("uploadDate") or item.get("upload_date") or item.get("publishedAt") or item.get("published_at")
                if upload_date and isinstance(upload_date, str):
                    # Try to parse various date formats
                    try:
                        if "T" in upload_date:
                            upload_date_obj = datetime.fromisoformat(upload_date.replace("Z", "+00:00"))
                            upload_date = upload_date_obj.strftime("%Y-%m-%d")
                        elif len(upload_date) == 8 and upload_date.isdigit():
                            upload_date_obj = datetime.strptime(upload_date, "%Y%m%d")
                            upload_date = upload_date_obj.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        pass

                # Build normalized entry dict
                entry = {
                    "id": video_id,
                    "video_id": video_id,
                    "display_id": video_id,
                    "title": item.get("title", "Unknown"),
                    "channel": item.get("channelName") or item.get("channel") or item.get("channel_name") or "Unknown",
                    "channel_id": item.get("channelId") or item.get("channel_id"),
                    "channel_url": item.get("channelUrl") or item.get("channel_url"),
                    "uploader": item.get("channelName") or item.get("channel") or item.get("channel_name"),
                    "uploader_id": item.get("channelId") or item.get("channel_id"),
                    "webpage_url": video_url,
                    "url": video_url,
                    "link": video_url,
                    "link_suffix": f"/watch?v={video_id}",
                    "duration": item.get("duration") or item.get("durationSeconds"),
                    "view_count": item.get("viewCount") or item.get("views") or item.get("view_count"),
                    "views": item.get("viewCount") or item.get("views") or item.get("view_count"),
                    "like_count": item.get("likeCount") or item.get("likes") or item.get("like_count"),
                    "likes": item.get("likeCount") or item.get("likes") or item.get("like_count"),
                    "comment_count": item.get("commentCount") or item.get("comments") or item.get("comment_count"),
                    "comments": item.get("commentCount") or item.get("comments") or item.get("comment_count"),
                    "upload_date": upload_date,
                    "description": item.get("description", ""),
                    "thumbnail": item.get("thumbnailUrl") or item.get("thumbnail") or item.get("thumbnail_url"),
                }

                result = YouTubeSearchResult.from_dict(entry)
                results.append(result)

            # Sort by likes (descending)
            results.sort(key=lambda x: (x.likes or 0), reverse=True)
            logger.info(f"✅ Search completed: {len(results)} videos found (sorted by likes)")
            if results:
                logger.debug(f"Top result: {results[0].title or 'Unknown'} - {results[0].likes or 0} likes")
            return results
        except ApifyApiError as e:
            error_msg = str(e)
            actor_id = "qoA27OkGHoMSJGBtf"
            logger.error(f"❌ Apify API error from Actor {actor_id} (maged120/youtube-search): {error_msg}")
            
            if "Monthly usage hard limit exceeded" in error_msg or "usage limit" in error_msg.lower():
                logger.error(f"🚫 Actor {actor_id} blocked: Monthly usage limit exceeded. Please upgrade your Apify plan or wait for the limit to reset.")
                raise RuntimeError(f"Apify Actor {actor_id} (maged120/youtube-search) monthly usage limit exceeded. Please upgrade your Apify plan or wait for the limit to reset.")
            elif "authentication" in error_msg.lower() or "token" in error_msg.lower() or "unauthorized" in error_msg.lower():
                logger.error(f"🔐 Actor {actor_id} authentication error: {error_msg}")
                raise RuntimeError(f"Apify Actor {actor_id} (maged120/youtube-search) authentication failed: {error_msg}. Please check your APIFY_TOKEN.")
            else:
                logger.error(f"❌ Actor {actor_id} error: {error_msg}", exc_info=True)
                raise RuntimeError(f"Apify Actor {actor_id} (maged120/youtube-search) error: {error_msg}")
        except Exception as e:
            logger.error(f"❌ Search error: {e}", exc_info=True)
            raise RuntimeError(f"Search failed: {str(e)}")

    async def get_transcript_safe(
        self, video_id: str, language: str = "en", max_retries: int = 0
    ) -> ApifyTranscriptResult:
        """Get transcript using Apify YouTube Transcript Scraper with error handling."""
        if not self.apify_client:
            return ApifyTranscriptResult(
                success=False,
                video_id=video_id,
                error="Apify client not initialized",
            )

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

                result = ApifyTranscriptResult.from_apify_response(video_id, dataset_items)
                if result.success:
                    result.language = language
                    return result
                else:
                    # Retry on failure
                    if attempt < max_retries:
                        wait_time = self.delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Normalize error message
                        error_msg = result.error or "Unknown error"
                        if "No transcript" in error_msg or "not available" in error_msg.lower():
                            error_msg = "No subtitles available for this video"
                        elif "API token" in error_msg or "authentication" in error_msg.lower():
                            error_msg = "Apify API authentication failed. Check your API token."
                        elif len(error_msg) > 200:
                            error_msg = error_msg[:200] + "..."
                        return ApifyTranscriptResult(
                            success=False,
                            video_id=video_id,
                            error=error_msg,
                        )

            except Exception as e:
                if attempt == max_retries:
                    error_msg = str(e)
                    if "No transcript" in error_msg or "not available" in error_msg.lower():
                        error_msg = "No subtitles available for this video"
                    elif "API token" in error_msg or "authentication" in error_msg.lower():
                        error_msg = "Apify API authentication failed. Check your API token."
                    elif len(error_msg) > 200:
                        error_msg = error_msg[:200] + "..."

                    return ApifyTranscriptResult(
                        success=False,
                        video_id=video_id,
                        error=error_msg,
                    )
                wait_time = self.delay * (2 ** attempt)
                await asyncio.sleep(wait_time)

        return ApifyTranscriptResult(
            success=False,
            video_id=video_id,
            error="Unknown error"
        )

    async def search_and_get_transcripts(
        self, query: str, num_videos: int | None = None
    ) -> list[dict]:
        """
        Search for videos and retrieve their transcripts.
        Pure API call - no caching logic.

        Args:
            query: Search topic
            num_videos: Number of videos to process (defaults to config value)

        Returns:
            List of dictionaries with video info and transcripts
        """
        settings = get_app_settings()
        if num_videos is None:
            num_videos = settings.youtube.num_videos

        logger.info(f"🔍 Searching for: '{query}' (num_videos: {num_videos})")
        videos = await self.search_videos(query, max_results=num_videos)

        if not videos:
            logger.warning("❌ No videos found")
            return []
        
        logger.info(f"📊 Found {len(videos)} videos (sorted by likes)")

        results = []
        for i, video in enumerate(videos, 1):
            video_id = self._video_id_from(video)
            if not video_id:
                logger.warning("Skipping video: Could not find video ID")
                continue

            logger.info(f"🌐 Fetching transcript from API for video {video_id}")
            transcript_result = await self.get_transcript_safe(video_id)
            
            transcript_text = self._transcript_field(transcript_result, "transcript", "") or ""
            transcript_length = len(transcript_text) if transcript_text else 0

            video_url = (
                self._video_field(video, "url")
                or self._video_field(video, "link")
                or self._video_field(video, "webpage_url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )

            channel = self._video_field(video, "channel") or self._video_field(video, "uploader") or "Unknown"

            combined = {
                "title": self._video_field(video, "title") or "Unknown",
                "channel": channel,
                "channel_id": self._video_field(video, "channel_id"),
                "channel_url": self._video_field(video, "channel_url"),
                "video_url": video_url,
                "video_id": video_id,
                "duration": self._video_field(video, "duration"),
                "views": self._video_field(video, "views"),
                "likes": self._video_field(video, "likes"),
                "comments": self._video_field(video, "comments"),
                "upload_date": self._video_field(video, "upload_date"),
                "description": self._video_field(video, "description") or "",
                "thumbnail": self._video_field(video, "thumbnail"),
                "transcript_success": bool(self._transcript_field(transcript_result, "success", False)),
                "transcript": transcript_text,
                "transcript_length": transcript_length,
                "error": self._transcript_field(transcript_result, "error"),
                "is_auto_generated": self._transcript_field(transcript_result, "is_generated"),
                "language": self._transcript_field(transcript_result, "language"),
            }
            results.append(combined)

            if i < len(videos):
                await asyncio.sleep(self.delay)

        return results

    async def extract_transcripts_for_video_ids(self, video_ids: list[str]) -> list[dict]:
        """
        Extract transcripts for a given list of video IDs.
        Pure API call - no caching logic.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            List of dictionaries with video info and transcripts
        """
        if not video_ids:
            logger.warning("No video IDs provided")
            return []

        logger.info(f"📝 Extracting transcripts for {len(video_ids)} video IDs")

        results = []
        for i, video_id in enumerate(video_ids, 1):
            logger.info(f"\n[{i}/{len(video_ids)}] Processing video ID: {video_id}")
            
            logger.info(f"🌐 Fetching transcript from API for video {video_id}")
            transcript_result = await self.get_transcript_safe(video_id)
            
            transcript_text = self._transcript_field(transcript_result, "transcript", "") or ""
            transcript_length = len(transcript_text) if transcript_text else 0

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
                "transcript_success": bool(self._transcript_field(transcript_result, "success", False)),
                "transcript": transcript_text,
                "transcript_length": transcript_length,
                "error": self._transcript_field(transcript_result, "error"),
                "is_auto_generated": self._transcript_field(transcript_result, "is_generated"),
                "language": self._transcript_field(transcript_result, "language"),
            }

            results.append(combined)

            if i < len(video_ids):
                await asyncio.sleep(self.delay)

        return results


# Exposed for test patching (`tests/test_youtube_client.py` patches this symbol)
def get_db_manager():
    # Delegate to the shared DB manager which can fall back to a no-op manager
    # if Postgres is unavailable.
    from mcp_server_youtube.youtube.methods import get_db_manager as _get_db_manager

    return _get_db_manager()

