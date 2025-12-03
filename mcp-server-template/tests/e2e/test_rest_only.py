from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_health_endpoint_available(rest_client) -> None:
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    assert payload.get("service") == "mcp-server-weather"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_admin_logs_requires_payment(rest_client) -> None:
    config, client = rest_client
    response = await client.get("/api/admin/logs")
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_admin_logs_succeeds_with_x402(paid_client) -> None:
    config, client = paid_client
    response = await client.get("/api/admin/logs")
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"This indicates payment flow is not working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    payload = response.json()
    assert isinstance(payload.get("logs"), list)
