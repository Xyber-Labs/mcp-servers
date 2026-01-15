"""
Tests for MCP-only FastAPI routers.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_deepresearcher.mcp_routers.research_analyzer import router as mcp_router
from mcp_server_deepresearcher.dependencies import get_research_resources
from mcp_server_deepresearcher.schemas import DeepResearchRequest


@pytest_asyncio.fixture
async def mcp_client(monkeypatch) -> AsyncClient:
    """Create a test client for MCP-only routes with mocked dependencies."""
    # Mock the dependencies
    def mock_get_resources(request):
        return {
            "llm": MagicMock(),
            "llm_thinking": MagicMock(),
            "mcp_tools": [MagicMock()],
            "tools_description": []
        }
    
    app = FastAPI()
    app.include_router(mcp_router)
    app.dependency_overrides[get_research_resources] = mock_get_resources
    
    # Set app state for the dependency
    app.state.llm = MagicMock()
    app.state.llm_thinking = MagicMock()
    app.state.mcp_tools = [MagicMock()]
    app.state.tools_description = []
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_success(mcp_client: AsyncClient) -> None:
    """Test successful MCP-only deep research execution."""
    mock_result = {
        "status": "success",
        "research_topic": "quantum computing",
        "running_summary": {"result": "Research completed"},
        "report": {"title": "Report"},
        "research_loop_count": 3
    }
    
    with patch('mcp_server_deepresearcher.mcp_routers.research_analyzer.perform_deep_research') as mock_perform:
        mock_perform.return_value = mock_result
        
        response = await mcp_client.post(
            "/deep-research",
            json={
                "research_topic": "quantum computing"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["research_topic"] == "quantum computing"
        mock_perform.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_missing_resources(monkeypatch) -> None:
    """Test MCP-only deep research with missing resources returns 503."""
    def mock_get_resources(request):
        return {
            "llm": None,
            "llm_thinking": None,
            "mcp_tools": [],
            "tools_description": []
        }
    
    app = FastAPI()
    app.include_router(mcp_router)
    app.dependency_overrides[get_research_resources] = mock_get_resources
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/deep-research",
            json={
                "research_topic": "test"
            }
        )
        
        assert response.status_code == 503
        assert "Shared resources" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_missing_tools(monkeypatch) -> None:
    """Test MCP-only deep research with missing tools returns 503."""
    def mock_get_resources(request):
        return {
            "llm": MagicMock(),
            "llm_thinking": MagicMock(),
            "mcp_tools": None,
            "tools_description": []
        }
    
    app = FastAPI()
    app.include_router(mcp_router)
    app.dependency_overrides[get_research_resources] = mock_get_resources
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/deep-research",
            json={
                "research_topic": "test"
            }
        )
        
        assert response.status_code == 503
        assert "Shared resources" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_validation_error(mcp_client: AsyncClient) -> None:
    """Test MCP-only deep research with invalid input returns 422."""
    response = await mcp_client.post(
        "/deep-research",
        json={}  # Missing required field
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_default_loops(mcp_client: AsyncClient) -> None:
    """Test MCP-only deep research uses default max_web_research_loops."""
    mock_result = {
        "status": "success",
        "research_topic": "test",
        "running_summary": {},
        "report": {},
        "research_loop_count": 3
    }
    
    with patch('mcp_server_deepresearcher.mcp_routers.research_analyzer.perform_deep_research') as mock_perform:
        mock_perform.return_value = mock_result
        
        response = await mcp_client.post(
            "/deep-research",
            json={
                "research_topic": "test"
                # max_web_research_loops should default to 3
            }
        )
        
        assert response.status_code == 200
        # Verify default value was used
        call_args = mock_perform.call_args
        request_arg = call_args[0][0]
        assert request_arg.max_web_research_loops == 3



@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_error_handling(mcp_client: AsyncClient) -> None:
    """Test MCP-only deep research error handling."""
    with patch('mcp_server_deepresearcher.mcp_routers.research_analyzer.perform_deep_research') as mock_perform:
        mock_perform.side_effect = Exception("Research failed")
        
        response = await mcp_client.post(
            "/deep-research",
            json={
                "research_topic": "test"
            }
        )
        
        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_uses_llm_thinking_fallback(mcp_client: AsyncClient) -> None:
    """Test MCP-only deep research uses llm as fallback when llm_thinking is None."""
    def mock_get_resources(request):
        return {
            "llm": MagicMock(),
            "llm_thinking": None,  # Missing thinking LLM
            "mcp_tools": [MagicMock()],
            "tools_description": []
        }
    
    app = FastAPI()
    app.include_router(mcp_router)
    app.dependency_overrides[get_research_resources] = mock_get_resources
    
    mock_result = {
        "status": "success",
        "research_topic": "test",
        "running_summary": {},
        "report": {},
        "research_loop_count": 3
    }
    
    with patch('mcp_server_deepresearcher.mcp_routers.research_analyzer.perform_deep_research') as mock_perform:
        mock_perform.return_value = mock_result
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/deep-research",
                json={
                    "research_topic": "test"
                }
            )
            
            assert response.status_code == 200
            # Verify that llm was used as fallback for llm_thinking
            call_args = mock_perform.call_args
            assert call_args[0][2] == call_args[0][1]  # llm_thinking == llm

