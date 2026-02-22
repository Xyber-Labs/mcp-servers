from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
import pytest


def get_env_path() -> Path | str:
    """Find the .env.tests file in the tests directory."""
    tests_dir = Path(__file__).resolve().parent.parent
    env_test = tests_dir / ".env.tests"
    if env_test.exists():
        return env_test
    else:
        pytest.skip(f".env.tests file could not be found in dir {tests_dir}")

class E2ETestConfig(BaseSettings):
    """Configuration for end-to-end tests, driven by environment variables."""

    base_url: str = "http://localhost:8120"
    timeout_seconds: int = 120  # Image generation can take a while
    private_key: str | None = None
    together_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=get_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="MCP_TOGETHER_IMGEN_TEST_",
    )


def load_e2e_config() -> E2ETestConfig:
    config = E2ETestConfig()
    # Normalise base_url to avoid trailing slashes inconsistencies.
    config.base_url = config.base_url.rstrip("/")  # type: ignore[misc]
    return config


def require_base_url(config: E2ETestConfig) -> None:
    if not config.base_url:
        import pytest

        pytest.skip("Set MCP_TOGETHER_IMGEN_TEST_BASE_URL to run E2E tests.")


def require_wallet(config: E2ETestConfig) -> None:
    if not config.private_key:
        import pytest

        pytest.skip(
            "Set MCP_TOGETHER_IMGEN_TEST_PRIVATE_KEY to run x402 payment E2E tests."
        )
