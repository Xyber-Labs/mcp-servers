from __future__ import annotations

import os

import pytest


class TestDatabaseSettings:
    """Tests for DatabaseSettings class."""

    def test_is_configured_true_when_all_fields_present(self, monkeypatch):
        """When DB_USER, DB_PASSWORD, DB_HOST are all set, is_configured returns True."""
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.setenv("DB_HOST", "localhost")

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.is_configured is True

    def test_is_configured_false_when_user_missing(self, monkeypatch):
        """When DB_USER is missing, is_configured returns False."""
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.setenv("DB_HOST", "localhost")

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.is_configured is False

    def test_is_configured_false_when_password_missing(self, monkeypatch):
        """When DB_PASSWORD is missing, is_configured returns False."""
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        monkeypatch.setenv("DB_HOST", "localhost")

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.is_configured is False

    def test_is_configured_false_when_host_missing(self, monkeypatch):
        """When DB_HOST is missing, is_configured returns False."""
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.delenv("DB_HOST", raising=False)

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.is_configured is False

    def test_database_url_format(self, monkeypatch):
        """Verify database_url builds correct postgresql+psycopg:// connection string."""
        monkeypatch.setenv("DB_USER", "myuser")
        monkeypatch.setenv("DB_PASSWORD", "mypass")
        monkeypatch.setenv("DB_HOST", "myhost")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "mydb")

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.database_url == "postgresql+psycopg://myuser:mypass@myhost:5433/mydb"

    def test_database_url_none_when_not_configured(self, monkeypatch):
        """Verify database_url returns None when not configured."""
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.database_url is None

    def test_port_validator_strips_tcp_prefix(self, monkeypatch):
        """Port validator handles tcp://host:5432 format."""
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("DB_HOST", "host")
        monkeypatch.setenv("DB_PORT", "tcp://somehost:5432")

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.db_port == "5432"

    def test_default_cache_ttl_values(self, monkeypatch):
        """Verify default TTL values are set correctly."""
        monkeypatch.delenv("CACHE_TTL_TOPIC_LATEST", raising=False)
        monkeypatch.delenv("CACHE_TTL_TOPIC_TOP", raising=False)
        monkeypatch.delenv("CACHE_TTL_PROFILE", raising=False)
        monkeypatch.delenv("CACHE_TTL_REPLIES", raising=False)

        from mcp_twitter.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.cache_ttl_topic_latest == 900  # 15 min
        assert settings.cache_ttl_topic_top == 86400  # 24 hours
        assert settings.cache_ttl_profile == 1800  # 30 min
        assert settings.cache_ttl_replies == 3600  # 1 hour


class TestAppSettings:
    """Tests for AppSettings class."""

    def test_default_values(self, monkeypatch):
        """Verify default values for AppSettings."""
        monkeypatch.setenv("APIFY_TOKEN", "test_token")

        from mcp_twitter.config import AppSettings

        settings = AppSettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8002
        assert settings.logging_level == "INFO"
        assert settings.hot_reload is False

    def test_apify_settings_computed_field(self, monkeypatch):
        """Verify apify computed field returns ApifySettings."""
        monkeypatch.setenv("APIFY_TOKEN", "my_apify_token")
        monkeypatch.setenv("ACTOR_NAME", "custom/actor")

        from mcp_twitter.config import AppSettings

        settings = AppSettings()
        assert settings.apify.apify_token == "my_apify_token"
        assert settings.apify.actor_name == "custom/actor"

    def test_database_settings_computed_field(self, monkeypatch):
        """Verify database computed field returns DatabaseSettings."""
        monkeypatch.setenv("APIFY_TOKEN", "test_token")
        monkeypatch.setenv("DB_USER", "dbuser")
        monkeypatch.setenv("DB_PASSWORD", "dbpass")
        monkeypatch.setenv("DB_HOST", "dbhost")

        from mcp_twitter.config import AppSettings

        settings = AppSettings()
        assert settings.database.is_configured is True
        assert settings.database.db_user == "dbuser"

    def test_custom_port(self, monkeypatch):
        """Verify custom port can be set via env."""
        monkeypatch.setenv("APIFY_TOKEN", "test_token")
        monkeypatch.setenv("MCP_TWITTER_PORT", "9000")

        from mcp_twitter.config import AppSettings

        settings = AppSettings()
        assert settings.port == 9000
