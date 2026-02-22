from __future__ import annotations

from mcp_server_together_imgen.schemas import HealthCheckResponse


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
    assert health_data.service == "mcp-server-together-imgen"
