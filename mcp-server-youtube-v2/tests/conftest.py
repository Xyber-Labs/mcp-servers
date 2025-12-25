"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_youtube.app import create_app
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript


@pytest.fixture
def mock_youtube_client() -> Mock:
    """Create a mock YouTube client."""
    client = Mock(spec=YouTubeVideoSearchAndTranscript)
    client.search_videos = AsyncMock(return_value=[])
    client.get_transcript_safe = AsyncMock(return_value=None)
    client.search_and_get_transcripts = AsyncMock(return_value=[])
    client.extract_transcripts_for_video_ids = AsyncMock(return_value=[])
    return client


@pytest.fixture
def sample_video_data() -> dict:
    """Sample video data for testing."""
    return {
        "id": "test_video_id",
        "video_id": "test_video_id",
        "title": "Test Video Title",
        "channel": "Test Channel",
        "channel_id": "test_channel_id",
        "channel_url": "https://www.youtube.com/channel/test_channel_id",
        "url": "https://www.youtube.com/watch?v=test_video_id",
        "video_url": "https://www.youtube.com/watch?v=test_video_id",
        "duration": 3600,
        "views": 10000,
        "likes": 500,
        "comments": 100,
        "upload_date": "2024-01-01",
        "description": "Test description",
        "thumbnail": "https://i.ytimg.com/vi/test_video_id/default.jpg",
        "transcript": "This is a test transcript.",
        "transcript_success": True,
        "transcript_length": 25,
        "is_auto_generated": False,
        "language": "en",
    }


@pytest.fixture
def sample_videos_list(sample_video_data: dict) -> list[dict]:
    """List of sample videos."""
    video2 = sample_video_data.copy()
    video2["id"] = "test_video_id_2"
    video2["video_id"] = "test_video_id_2"
    video2["title"] = "Test Video Title 2"
    return [sample_video_data, video2]


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def client_with_mock_youtube(app: FastAPI, mock_youtube_client: Mock) -> TestClient:
    """Create test client with mocked YouTube service."""
    app.state.youtube_client = mock_youtube_client
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config cache before each test."""
    from mcp_server_youtube.config import get_app_settings, get_x402_settings
    
    # Clear LRU cache
    get_app_settings.cache_clear()
    get_x402_settings.cache_clear()
    
    yield
    
    # Clear after test too
    get_app_settings.cache_clear()
    get_x402_settings.cache_clear()

