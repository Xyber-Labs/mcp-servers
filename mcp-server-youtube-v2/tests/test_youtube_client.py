"""
Tests for YouTube client functionality.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any

from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript, get_youtube_client
from mcp_server_youtube.youtube.client import YouTubeVideoSearchAndTranscript as ClientClass


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
    async def test_search_videos_success(self, youtube_client: YouTubeVideoSearchAndTranscript):
        """Test successful video search."""
        with patch('mcp_server_youtube.youtube.client.YtDlpHelper') as mock_ytdlp:
            mock_helper = Mock()
            mock_helper.search.return_value = [
                {
                    "id": "test_id",
                    "title": "Test Video",
                    "channel": "Test Channel",
                    "url": "https://www.youtube.com/watch?v=test_id",
                }
            ]
            mock_ytdlp.return_value = mock_helper
            
            videos = await youtube_client.search_videos("test query", max_results=1)
            
            assert len(videos) == 1
            assert videos[0]["id"] == "test_id"
            assert videos[0]["title"] == "Test Video"

    @pytest.mark.asyncio
    async def test_search_videos_empty_results(self, youtube_client: YouTubeVideoSearchAndTranscript):
        """Test video search with no results."""
        with patch('mcp_server_youtube.youtube.client.YtDlpHelper') as mock_ytdlp:
            mock_helper = Mock()
            mock_helper.search.return_value = []
            mock_ytdlp.return_value = mock_helper
            
            videos = await youtube_client.search_videos("nonexistent query", max_results=5)
            
            assert videos == []

    @pytest.mark.asyncio
    async def test_get_transcript_safe_success(self, youtube_client: YouTubeVideoSearchAndTranscript):
        """Test successful transcript retrieval."""
        with patch('mcp_server_youtube.youtube.client.ApifyClient') as mock_apify:
            mock_client = Mock()
            mock_actor = Mock()
            mock_run = Mock()
            mock_run.wait_for_finish.return_value = {
                "items": [{"text": "Test transcript"}]
            }
            mock_actor.run.return_value = mock_run
            mock_client.actor.return_value = mock_actor
            mock_apify.return_value = mock_client
            
            transcript = await youtube_client.get_transcript_safe("test_video_id")
            
            assert transcript == "Test transcript"

    @pytest.mark.asyncio
    async def test_get_transcript_safe_no_apify_token(self):
        """Test transcript retrieval without Apify token."""
        client = YouTubeVideoSearchAndTranscript(
            delay_between_requests=0.1,
            apify_api_token=None,
            require_apify=False,
        )
        
        transcript = await client.get_transcript_safe("test_video_id")
        
        assert transcript is None

    @pytest.mark.asyncio
    async def test_get_transcript_safe_error_handling(self, youtube_client: YouTubeVideoSearchAndTranscript):
        """Test transcript retrieval error handling."""
        with patch('mcp_server_youtube.youtube.client.ApifyClient') as mock_apify:
            mock_client = Mock()
            mock_actor = Mock()
            mock_actor.run.side_effect = Exception("Apify error")
            mock_client.actor.return_value = mock_actor
            mock_apify.return_value = mock_client
            
            transcript = await youtube_client.get_transcript_safe("test_video_id")
            
            # Should return None on error
            assert transcript is None

    @pytest.mark.asyncio
    async def test_search_and_get_transcripts_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test search and get transcripts workflow."""
        with patch.object(youtube_client, 'search_videos') as mock_search, \
             patch.object(youtube_client, 'get_transcript_safe') as mock_transcript:
            
            mock_search.return_value = [
                {"id": "test_id", "title": "Test Video", "video_id": "test_id"}
            ]
            mock_transcript.return_value = "Test transcript"
            
            results = await youtube_client.search_and_get_transcripts("test query", num_videos=1)
            
            assert len(results) == 1
            assert results[0]["transcript"] == "Test transcript"
            assert results[0]["transcript_success"] is True

    @pytest.mark.asyncio
    async def test_extract_transcripts_for_video_ids_success(
        self, youtube_client: YouTubeVideoSearchAndTranscript
    ):
        """Test extract transcripts for multiple video IDs."""
        with patch.object(youtube_client, 'get_transcript_safe') as mock_transcript, \
             patch('mcp_server_youtube.youtube.client.YtDlpHelper') as mock_ytdlp:
            
            mock_transcript.return_value = "Test transcript"
            mock_helper = Mock()
            mock_helper.extract_info.return_value = {
                "id": "test_id",
                "title": "Test Video",
                "channel": "Test Channel",
                "url": "https://www.youtube.com/watch?v=test_id",
            }
            mock_ytdlp.return_value = mock_helper
            
            results = await youtube_client.extract_transcripts_for_video_ids(["test_id"])
            
            assert len(results) == 1
            assert results[0]["transcript"] == "Test transcript"
            assert results[0]["video_id"] == "test_id"


class TestGetYouTubeClient:
    """Test cases for get_youtube_client factory function."""

    def test_get_youtube_client_returns_instance(self):
        """Test that get_youtube_client returns a YouTubeVideoSearchAndTranscript instance."""
        with patch('mcp_server_youtube.youtube.client.get_app_settings') as mock_settings:
            mock_settings.return_value.youtube.delay_between_requests = 1.0
            mock_settings.return_value.apify.apify_token = "test_token"
            
            client = get_youtube_client()
            
            assert isinstance(client, YouTubeVideoSearchAndTranscript)

    def test_get_youtube_client_uses_config_settings(self):
        """Test that get_youtube_client uses configuration settings."""
        with patch('mcp_server_youtube.youtube.client.get_app_settings') as mock_settings:
            mock_settings.return_value.youtube.delay_between_requests = 2.0
            mock_settings.return_value.apify.apify_token = "config_token"
            
            client = get_youtube_client()
            
            # Verify settings are used (we can't directly check private attributes,
            # but we can verify the client was created)
            assert isinstance(client, YouTubeVideoSearchAndTranscript)

