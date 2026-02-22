"""
E2E smoke tests for REST-only API endpoints.

Test coverage:
- /api/health (free endpoint)
- /api/admin/logs (priced endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_weather.schemas import AdminLogsResponse, HealthCheckResponse

# =============================================================================
# /api/health - Free endpoint
# =============================================================================


async def test_api_health_rest(rest_client) -> None:
    """Smoke test: /api/health endpoint (always free)."""
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    # Validate response against schema
    health_data = HealthCheckResponse(**response.json())
    assert health_data.status == "ok"
    assert health_data.service == "mcp-server-weather"


# =============================================================================
# /api/admin/logs - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_api_admin_logs_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works without payment when PRICING_MODE=off."""
    config, client = rest_client
    response = await client.get("/api/admin/logs")
    assert response.status_code == 200
    # Validate response against schema
    logs_data = AdminLogsResponse(**response.json())
    assert isinstance(logs_data.logs, list)
    assert len(logs_data.logs) > 0


@pytest.mark.payment_on
async def test_api_admin_logs_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 when PRICING_MODE=on and no payment provided."""
    config, client = rest_client
    response = await client.get("/api/admin/logs")
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.payment_on
async def test_api_admin_logs_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    response = await client.get("/api/admin/logs")
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    logs_data = AdminLogsResponse(**response.json())
    assert isinstance(logs_data.logs, list)
    assert len(logs_data.logs) > 0
