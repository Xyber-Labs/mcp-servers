from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from mcp_server_lurky.lurky.models import Discussion, SearchResponse, SpaceDetails
from mcp_server_lurky.lurky.module import LurkyClient

# Patch DatabaseManager and get_db_manager globally before any imports that might use it
_mock_db_manager = MagicMock()
_mock_db_manager.get_space = Mock(return_value=None)
_mock_db_manager.save_space = Mock(return_value=True)

# Patch both DatabaseManager (to prevent instantiation) and get_db_manager (to return mock)
_db_manager_class_patcher = None
_db_manager_func_patcher = None


def pytest_configure(config):
    """Configure pytest - patch database manager before any tests run."""
    global _db_manager_class_patcher, _db_manager_func_patcher

    # Clear any existing cache
    from mcp_server_lurky.dependencies import get_db

    if hasattr(get_db, "cache_clear"):
        get_db.cache_clear()

    # Patch DatabaseManager class to return mock instance
    _db_manager_class_patcher = patch(
        "mcp_server_lurky.db.database.DatabaseManager", return_value=_mock_db_manager
    )
    _db_manager_func_patcher = patch(
        "mcp_server_lurky.dependencies.get_db", return_value=_mock_db_manager
    )
    _db_manager_class_patcher.start()
    _db_manager_func_patcher.start()


def pytest_unconfigure(config):
    """Cleanup after tests."""
    global _db_manager_class_patcher, _db_manager_func_patcher
    if _db_manager_class_patcher:
        _db_manager_class_patcher.stop()
    if _db_manager_func_patcher:
        _db_manager_func_patcher.stop()


@pytest.fixture
def mock_lurky_client() -> Mock:
    """Create a mock Lurky client."""
    client = Mock(spec=LurkyClient)
    client.search_discussions = AsyncMock(
        return_value=SearchResponse(discussions=[], total=0, page=0, limit=10)
    )
    client.get_space_details = AsyncMock(
        return_value=SpaceDetails(
            id="test_space_id", title="Test Space", summary="Test summary"
        )
    )
    client.get_space_discussions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def sample_discussion() -> Discussion:
    """Sample discussion data for testing."""
    return Discussion(
        id="test_discussion_id",
        space_id="test_space_id",
        title="Test Discussion",
        summary="Test discussion summary",
        timestamp=1234567890,
        coins=[],
        categories=["Test"],
    )


@pytest.fixture
def sample_space_details() -> SpaceDetails:
    """Sample space details data for testing."""
    return SpaceDetails(
        id="test_space_id",
        creator_id="test_creator_id",
        creator_handle="test_creator",
        title="Test Space Title",
        summary="Test space summary",
        minimized_summary="Test minimized summary",
        state="analyzed",
        language="en",
        overall_sentiment="positive",
        participant_count=100,
        subscriber_count=50,
        likes=25,
        categories=["Test", "Crypto"],
        created_at=1234567890000,
        started_at=1234567900000,
        ended_at=1234568000000,
        analyzed_at=1234568100000,
        discussions=[],
    )


@pytest.fixture
def sample_search_response(sample_discussion: Discussion) -> SearchResponse:
    """Sample search response for testing."""
    return SearchResponse(discussions=[sample_discussion], total=1, page=0, limit=10)


@pytest.fixture(autouse=True)
def set_test_database_url(monkeypatch):
    """Set test database URL for all tests."""
    # Set individual DB env vars for DatabaseConfig
    monkeypatch.setenv("DB_NAME", "lurky_test")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset config cache before each test."""
    from mcp_server_lurky.config import get_app_settings
    from mcp_server_lurky.x402_integration import get_x402_settings

    # Clear LRU cache if available
    if hasattr(get_app_settings, "cache_clear"):
        get_app_settings.cache_clear()
    if hasattr(get_x402_settings, "cache_clear"):
        get_x402_settings.cache_clear()

    yield

    # Clear after test too
    if hasattr(get_app_settings, "cache_clear"):
        get_app_settings.cache_clear()
    if hasattr(get_x402_settings, "cache_clear"):
        get_x402_settings.cache_clear()
