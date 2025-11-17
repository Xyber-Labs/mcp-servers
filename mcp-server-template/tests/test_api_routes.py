from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_weather.api_routers import admin, health


@pytest_asyncio.fixture
async def api_client() -> AsyncClient:
    app = FastAPI()
    app.include_router(health.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "mcp-server-weather"


@pytest.mark.asyncio
async def test_admin_logs_returns_log_entries(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/admin/logs")
    assert response.status_code == 200
    payload = response.json()
    assert "logs" in payload
    assert isinstance(payload["logs"], list)
