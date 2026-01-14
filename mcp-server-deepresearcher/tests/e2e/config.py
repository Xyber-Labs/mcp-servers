"""
E2E test configuration loader.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import pytest


@dataclass
class E2ETestConfig:
    """Configuration for E2E tests."""
    
    base_url: str
    timeout_seconds: int = 30
    private_key: str | None = None


def load_e2e_config() -> E2ETestConfig:
    """Load E2E test configuration from environment variables."""
    base_url = os.getenv("MCP_DEEP_RESEARCHER_E2E_BASE_URL", "http://localhost:8006")
    timeout_seconds = int(os.getenv("MCP_DEEP_RESEARCHER_E2E_TIMEOUT", "30"))
    private_key = os.getenv("MCP_DEEP_RESEARCHER_E2E_PRIVATE_KEY")
    
    return E2ETestConfig(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        private_key=private_key,
    )


def require_base_url(config: E2ETestConfig) -> None:
    """Require that base_url is configured."""
    if not config.base_url:
        pytest.skip("E2E base URL not configured (MCP_DEEP_RESEARCHER_E2E_BASE_URL)")


def require_wallet(config: E2ETestConfig) -> None:
    """Require that wallet private key is configured."""
    if not config.private_key:
        pytest.skip("Wallet private key not configured (MCP_DEEP_RESEARCHER_E2E_PRIVATE_KEY)")

