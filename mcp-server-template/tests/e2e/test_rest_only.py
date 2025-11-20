from __future__ import annotations

import pytest


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
async def test_admin_logs_succeeds_with_x402(paid_client) -> None:
    config, client = paid_client
    response = await client.get("/api/admin/logs")
    response.raise_for_status()
    payload = response.json()
    assert isinstance(payload.get("logs"), list)
