from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_twitter.db import CacheRepository
from mcp_twitter.db.models import Base
from mcp_twitter.dependencies import DependencyContainer, get_scraper
from mcp_twitter.twitter import TwitterScraper


@pytest.fixture
def mock_database() -> CacheRepository:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return CacheRepository(session_factory)


@pytest.fixture(autouse=True)
def cleanup_container():
    """Ensure container is cleared before and after each test."""
    DependencyContainer.clear()
    yield
    DependencyContainer.clear()


class TestDependencyContainer:
    """Tests for DependencyContainer class."""

    def test_create_without_database(self):
        """DependencyContainer.create works without database."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="test_actor",
            database=None,
        )

        scraper = DependencyContainer.get_scraper()
        assert scraper is not None
        assert isinstance(scraper, TwitterScraper)
        assert scraper.use_cache is False
        assert scraper._db is None

    def test_create_with_database(self, mock_database):
        """DependencyContainer.create stores database reference."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="test_actor",
            database=mock_database,
        )

        scraper = DependencyContainer.get_scraper()
        assert scraper is not None
        assert scraper.use_cache is True
        assert scraper._db is mock_database

    def test_clear_removes_dependencies(self):
        """DependencyContainer.clear removes all stored dependencies."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="test_actor",
        )

        # Verify scraper exists
        scraper = DependencyContainer.get_scraper()
        assert scraper is not None

        # Clear and verify
        DependencyContainer.clear()
        assert DependencyContainer._scraper is None
        assert DependencyContainer._database is None

    def test_get_scraper_raises_when_not_created(self):
        """get_scraper raises RuntimeError when container not created."""
        with pytest.raises(RuntimeError) as exc_info:
            DependencyContainer.get_scraper()

        assert "DependencyContainer not created" in str(exc_info.value)

    def test_get_scraper_alias(self):
        """get_scraper module-level alias works correctly."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="test_actor",
        )

        # Test the alias
        scraper = get_scraper()
        assert scraper is not None
        assert isinstance(scraper, TwitterScraper)

    def test_scraper_has_correct_apify_token(self):
        """Scraper stores the provided apify_token."""
        DependencyContainer.create(
            apify_token="my_secret_token",
            actor_name="test_actor",
        )

        scraper = DependencyContainer.get_scraper()
        assert scraper.apify_token == "my_secret_token"

    def test_scraper_has_correct_actor_name(self):
        """Scraper stores the provided actor_name."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="custom/my-actor",
        )

        scraper = DependencyContainer.get_scraper()
        assert scraper.actor_id == "custom/my-actor"

    def test_create_sets_default_output_format(self):
        """Scraper is created with 'min' output format by default."""
        DependencyContainer.create(
            apify_token="test_token",
            actor_name="test_actor",
        )

        scraper = DependencyContainer.get_scraper()
        assert scraper.output_format == "min"
