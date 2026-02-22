"""
E2E smoke tests for REST-only API endpoints.

Test coverage:
- /api/health (free endpoint)
"""

from __future__ import annotations

import pytest

from mcp_server_lurky.schemas import HealthResponse

# =============================================================================
# /api/health - Free endpoint
# =============================================================================


@pytest.mark.asyncio
async def test_api_health_rest(rest_client) -> None:
    """Smoke test: /api/health endpoint (always free)."""
    config, client = rest_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    # Validate response against schema
    health_data = HealthResponse(**response.json())
    assert health_data.status
    assert health_data.version
