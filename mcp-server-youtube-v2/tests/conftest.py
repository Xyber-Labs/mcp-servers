"""
Pytest configuration and shared fixtures.
"""

import os
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_youtube.app import create_app
from mcp_server_youtube.dependencies import DependencyContainer
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript
from mcp_server_youtube.youtube.api_models import (
    ApifyTranscriptResult,
    YouTubeSearchResult,
)


@pytest.fixture(autouse=True)
def initialize_dependency_container():
    """Initialize DependencyContainer with mocks before each test."""
    # Create mock YouTube client
    mock_youtube = Mock(spec=YouTubeVideoSearchAndTranscript)
    mock_youtube.search_videos = AsyncMock(return_value=[])
    mock_youtube.get_transcript_safe = AsyncMock(return_value=None)
    mock_youtube.search_and_get_transcripts = AsyncMock(return_value=[])
    mock_youtube.extract_transcripts_for_video_ids = AsyncMock(return_value=[])

    # Create mock DB manager
    mock_db = MagicMock()
    mock_db.batch_check_transcripts = Mock(return_value={})
    mock_db.batch_check_video_exists = Mock(return_value={})
    mock_db.get_video = Mock(return_value=None)
    mock_db.has_transcript = Mock(return_value=False)
    mock_db.save_video = Mock(return_value=True)
    mock_db.batch_get_videos = Mock(return_value={})

    # Set the mocks directly on DependencyContainer
    DependencyContainer._youtube_service = mock_youtube
    DependencyContainer._db_manager = mock_db

    yield

    # Cleanup after test
    DependencyContainer._youtube_service = None
    DependencyContainer._db_manager = None


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
    """Sample video data for testing (as dict for backward compatibility)."""
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
def sample_video_model(sample_video_data: dict) -> YouTubeSearchResult:
    """Sample video as YouTubeSearchResult Pydantic model."""
    return YouTubeSearchResult.model_validate(sample_video_data)


@pytest.fixture
def sample_videos_list(sample_video_data: dict) -> list[dict]:
    """List of sample videos (as dicts for backward compatibility)."""
    video2 = sample_video_data.copy()
    video2["id"] = "test_video_id_2"
    video2["video_id"] = "test_video_id_2"
    video2["title"] = "Test Video Title 2"
    return [sample_video_data, video2]


@pytest.fixture
def sample_videos_models(sample_videos_list: list[dict]) -> list[YouTubeSearchResult]:
    """List of sample videos as YouTubeSearchResult models."""
    return [YouTubeSearchResult.model_validate(v) for v in sample_videos_list]


@pytest.fixture
def sample_transcript_result() -> ApifyTranscriptResult:
    """Sample successful transcript result."""
    return ApifyTranscriptResult(
        success=True,
        video_id="test_video_id",
        transcript="This is a test transcript.",
        is_generated=False,
        language="en",
    )


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
def set_test_database_url(monkeypatch):
    """Set test database URL for all tests."""
    # Use test database URL from env, or default to a test database
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mcp_youtube_test",
    )
    # Set individual DB env vars for AppSettings
    monkeypatch.setenv("MCP_YOUTUBE_DB_NAME", "mcp_youtube_test")
    monkeypatch.setenv("MCP_YOUTUBE_DB_USER", "postgres")
    monkeypatch.setenv("MCP_YOUTUBE_DB_PASSWORD", "postgres")
    monkeypatch.setenv("MCP_YOUTUBE_DB_HOST", "localhost")
    monkeypatch.setenv("MCP_YOUTUBE_DB_PORT", "5432")


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config cache before each test."""
    from mcp_server_youtube.config import get_app_settings
    from mcp_server_youtube.x402_integration import get_x402_settings

    # Clear LRU cache
    get_app_settings.cache_clear()
    get_x402_settings.cache_clear()

    yield

    # Clear after test too
    get_app_settings.cache_clear()
    get_x402_settings.cache_clear()
