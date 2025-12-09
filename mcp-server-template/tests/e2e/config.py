from __future__ import annotations
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_path() -> Path | str:
    """Find the .env file recursively from current directory up to root."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return ".env"


class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables."""

    base_url: str = "http://localhost:8006"
    timeout_seconds: int = 60
    private_key: str | None = None
    weather_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=get_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="MCP_WEATHER_TEST_",
    )


def load_e2e_config() -> E2ETestConfig:
    config = E2ETestConfig()
    # Normalise base_url to avoid trailing slashes inconsistencies.
    config.base_url = config.base_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    if not config.base_url:
        import pytest

        pytest.skip("Set MCP_WEATHER_E2E_BASE_URL to run E2E tests.")


def require_wallet(config: E2ETestConfig) -> None:
    if not config.private_key:
        import pytest
       
        pytest.skip("Set MCP_WEATHER_TEST_PRIVATE_KEY to run x402 payment E2E tests.")


def require_weather_api_key(config: E2ETestConfig) -> str:
    if not config.weather_api_key:
        import pytest

        pytest.skip(
            "Set MCP_WEATHER_TEST_WEATHER_API_KEY to run header auth E2E tests."
        )
    return config.weather_api_key
