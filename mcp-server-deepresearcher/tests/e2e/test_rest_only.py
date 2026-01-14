"""
E2E tests for REST-only endpoints.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


@pytest_asyncio.fixture
async def rest_client():
    """Create a REST client for E2E tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def paid_rest_client():
    """Create a paid REST client with x402 support."""
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    async with x402HttpxClient(
        account=account,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        yield config, client


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_health_endpoint_available(rest_client) -> None:
    """Test that health endpoint is available."""
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    assert payload.get("service") == "mcp-server-deep-researcher"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_health_endpoint_structure(rest_client) -> None:
    """Test health endpoint response structure."""
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "status" in payload
    assert "service" in payload

