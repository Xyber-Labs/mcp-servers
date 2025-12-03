from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables."""

    base_url: str
    timeout_seconds: int = 60
    private_key: str | None = None
    tavily_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="MCP_TAVILY_TEST_",
    )


def load_e2e_config() -> E2ETestConfig:
    config = E2ETestConfig()
    config.base_url = config.base_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    if not config.base_url:
        import pytest

        pytest.skip("Set MCP_TAVILY_TEST_BASE_URL to run E2E tests.")


def require_wallet(config: E2ETestConfig) -> None:
    if not config.private_key:
        import pytest

        pytest.skip("Set LUMIRA_WALLET to run x402 payment E2E tests.")


def require_tavily_api_key(config: E2ETestConfig) -> str:
    if not config.tavily_api_key:
        import pytest

        pytest.skip(
            "Set MCP_TAVILY_TEST_TAVILY_API_KEY to run header auth E2E tests."
        )
    return config.tavily_api_key

