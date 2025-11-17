from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


@pytest_asyncio.fixture
async def rest_client():
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def paid_rest_client():
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
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    assert payload.get("service") == "mcp-server-weather"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_admin_logs_requires_payment(rest_client) -> None:
    config, client = rest_client
    response = await client.get("/api/admin/logs")
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_admin_logs_succeeds_with_x402(paid_rest_client) -> None:
    config, client = paid_rest_client
    response = await client.get("/api/admin/logs")
    response.raise_for_status()
    payload = response.json()
    assert isinstance(payload.get("logs"), list)
