"""
Tests for REST-only API endpoints.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_deepresearcher.api_routers import health


@pytest_asyncio.fixture
async def api_client() -> AsyncClient:
    """Create a test client for API-only routes."""
    app = FastAPI()
    app.include_router(health.router, prefix="/api")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(api_client: AsyncClient) -> None:
    """Test that the health endpoint returns 200 with correct structure."""
    response = await api_client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "mcp-server-deep-researcher"


@pytest.mark.asyncio
async def test_health_endpoint_structure(api_client: AsyncClient) -> None:
    """Test that health endpoint returns expected fields."""
    response = await api_client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "status" in payload
    assert "service" in payload


@pytest.mark.asyncio
async def test_health_endpoint_methods(api_client: AsyncClient) -> None:
    """Test that health endpoint only accepts GET requests."""
    # POST should fail
    response = await api_client.post("/api/health")
    assert response.status_code == 405  # Method Not Allowed
    
    # PUT should fail
    response = await api_client.put("/api/health")
    assert response.status_code == 405
    
    # DELETE should fail
    response = await api_client.delete("/api/health")
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_health_endpoint_no_auth_required(api_client: AsyncClient) -> None:
    """Test that health endpoint doesn't require authentication."""
    response = await api_client.get("/api/health")
    assert response.status_code == 200
    # Should succeed without any auth headers


@pytest.mark.asyncio
async def test_health_endpoint_content_type(api_client: AsyncClient) -> None:
    """Test that health endpoint returns JSON content type."""
    response = await api_client.get("/api/health")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")

