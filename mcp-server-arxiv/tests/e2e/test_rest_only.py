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
    assert payload.get("service") == "mcp-server-arxiv"



