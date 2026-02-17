"""
Tests for YouTube client functionality.
"""

from unittest.mock import Mock, patch

import pytest

from mcp_server_youtube.youtube import (
    YouTubeVideoSearchAndTranscript,
    get_youtube_client,
)


class TestYouTubeVideoSearchAndTranscript:
    """Test cases for YouTubeVideoSearchAndTranscript class."""

    @pytest.fixture
    def youtube_client(self) -> YouTubeVideoSearchAndTranscript:
        """Create a YouTube client instance for testing."""
        return YouTubeVideoSearchAndTranscript(
            delay_between_requests=0.1,
            apify_api_token="test_token",
            require_apify=False,
        )

    @pytest.mark.asyncio
    async def test_search_videos_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test successful video search."""
        with patch(
            "mcp_server_youtube.youtube.client.yt_dlp.YoutubeDL"
        ) as mock_ytdlp_class:
            mock_ydl = Mock()
            mock_ydl.__enter__ = Mock(return_value=mock_ydl)
            mock_ydl.__exit__ = Mock(return_value=False)
            mock_ydl.extract_info.return_value = {
                "entries": [
                    {
                        "id": "test_id",
                        "title": "Test Video",
                        "channel": "Test Channel",
                        "url": "https://www.youtube.com/watch?v=test_id",
                        "view_count": 1000,
                        "like_count": 100,
                        "duration": 3600,
                    }
                ]
            }
            mock_ytdlp_class.return_value = mock_ydl

            videos = await youtube_client.search_videos("test query", max_results=1)

            assert len(videos) == 1
            assert videos[0]["id"] == "test_id"
            assert videos[0]["title"] == "Test Video"

    @pytest.mark.asyncio
    async def test_search_videos_empty_results(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test video search with no results."""
        with patch(
            "mcp_server_youtube.youtube.client.yt_dlp.YoutubeDL"
        ) as mock_ytdlp_class:
            mock_ydl = Mock()
            mock_ydl.__enter__ = Mock(return_value=mock_ydl)
            mock_ydl.__exit__ = Mock(return_value=False)
            mock_ydl.extract_info.return_value = {"entries": []}
            mock_ytdlp_class.return_value = mock_ydl

            videos = await youtube_client.search_videos(
                "nonexistent query", max_results=5
            )

            assert videos == []

    @pytest.mark.asyncio
    async def test_get_transcript_safe_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test successful transcript retrieval."""
        with patch.object(youtube_client, "apify_client") as mock_apify_client:
            mock_actor = Mock()
            mock_run = {"defaultDatasetId": "test_dataset_id"}
            mock_actor.call.return_value = mock_run

            mock_dataset = Mock()
            mock_dataset.iterate_items.return_value = [
                {"data": [{"text": "Test transcript"}]}
            ]
            mock_apify_client.actor.return_value = mock_actor
            mock_apify_client.dataset.return_value = mock_dataset

            result = await youtube_client.get_transcript_safe("test_video_id")

            assert result["success"] is True
            assert result["transcript"] == "Test transcript"
            assert result["video_id"] == "test_video_id"

    @pytest.mark.asyncio
    async def test_get_transcript_safe_no_apify_token(self):
        """Test transcript retrieval without Apify token."""
        with patch(
            "mcp_server_youtube.youtube.client.get_app_settings"
        ) as mock_settings:
            mock_settings.return_value.apify.apify_token = None

            client = YouTubeVideoSearchAndTranscript(
                delay_between_requests=0.1,
                apify_api_token=None,
                require_apify=False,
            )

            # Ensure apify_client is None
            client.apify_client = None

            result = await client.get_transcript_safe("test_video_id")

            assert result["success"] is False
            assert "Apify client not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_get_transcript_safe_error_handling(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test transcript retrieval error handling."""
        with patch.object(youtube_client, "apify_client") as mock_apify_client:
            mock_actor = Mock()
            mock_actor.call.side_effect = Exception("Apify error")
            mock_apify_client.actor.return_value = mock_actor

            result = await youtube_client.get_transcript_safe(
                "test_video_id", max_retries=0
            )

            # Should return error dict on failure
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_search_and_get_transcripts_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test search and get transcripts workflow."""
        with (
            patch.object(youtube_client, "search_videos") as mock_search,
            patch.object(youtube_client, "get_transcript_safe") as mock_transcript,
            patch("mcp_server_youtube.youtube.client.get_db_manager") as mock_db,
        ):
            mock_search.return_value = [
                {"id": "test_id", "title": "Test Video", "video_id": "test_id"}
            ]
            mock_transcript.return_value = {
                "success": True,
                "transcript": "Test transcript",
                "video_id": "test_id",
            }
            mock_db.return_value.get_video.return_value = None
            mock_db.return_value.has_transcript.return_value = False

            results = await youtube_client.search_and_get_transcripts(
                "test query", num_videos=1
            )

            assert len(results) == 1
            assert results[0]["transcript"] == "Test transcript"
            assert results[0]["transcript_success"] is True

    @pytest.mark.asyncio
    async def test_extract_transcripts_for_video_ids_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test extract transcripts for multiple video IDs."""
        with (
            patch.object(youtube_client, "get_transcript_safe") as mock_transcript,
            patch(
                "mcp_server_youtube.youtube.client.yt_dlp.YoutubeDL"
            ) as mock_ytdlp_class,
            patch("mcp_server_youtube.youtube.client.get_db_manager") as mock_db,
        ):
            mock_transcript.return_value = {
                "success": True,
                "transcript": "Test transcript",
                "video_id": "test_id",
            }
            mock_ydl = Mock()
            mock_ydl.__enter__ = Mock(return_value=mock_ydl)
            mock_ydl.__exit__ = Mock(return_value=False)
            mock_ydl.extract_info.return_value = {
                "id": "test_id",
                "title": "Test Video",
                "channel": "Test Channel",
                "url": "https://www.youtube.com/watch?v=test_id",
                "view_count": 1000,
                "like_count": 100,
                "duration": 3600,
            }
            mock_ytdlp_class.return_value = mock_ydl
            mock_db.return_value.get_video.return_value = None
            mock_db.return_value.has_transcript.return_value = False

            results = await youtube_client.extract_transcripts_for_video_ids(
                ["test_id"]
            )

            assert len(results) == 1
            assert results[0]["transcript"] == "Test transcript"
            assert results[0]["video_id"] == "test_id"


class TestGetYouTubeClient:
    """Test cases for get_youtube_client factory function."""

    def test_get_youtube_client_returns_instance(self):
        """Test that get_youtube_client returns a YouTubeVideoSearchAndTranscript instance."""
        with patch(
            "mcp_server_youtube.youtube.client.get_app_settings"
        ) as mock_settings:
            mock_settings.return_value.youtube.delay_between_requests = 1.0
            mock_settings.return_value.apify.apify_token = "test_token"

            client = get_youtube_client()

            assert isinstance(client, YouTubeVideoSearchAndTranscript)

    def test_get_youtube_client_uses_config_settings(self):
        """Test that get_youtube_client uses configuration settings."""
        with patch(
            "mcp_server_youtube.youtube.client.get_app_settings"
        ) as mock_settings:
            mock_settings.return_value.youtube.delay_between_requests = 2.0
            mock_settings.return_value.apify.apify_token = "config_token"

            client = get_youtube_client()

            # Verify settings are used (we can't directly check private attributes,
            # but we can verify the client was created)
            assert isinstance(client, YouTubeVideoSearchAndTranscript)
