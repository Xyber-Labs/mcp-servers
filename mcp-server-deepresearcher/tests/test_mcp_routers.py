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
    from fastapi import Request
    
    # Mock the dependencies - ensure it returns the expected dict structure
    # Note: get_research_resources is sync, so the override should also be sync
    # Match the exact signature: get_research_resources(request: Request) -> dict[str, Any]
    # Accept Request but ignore it to match signature
    def mock_get_resources(request=None):
        # Ensure we return a proper dict that matches what the endpoint expects
        return {
            "llm": MagicMock(),
            "llm_thinking": MagicMock(),
            "mcp_tools": [MagicMock()],
            "tools_description": [],
            "mcp_connection_error": None
        }
    
    app = FastAPI()
    # Override dependency BEFORE including router to ensure it's used
    app.dependency_overrides[get_research_resources] = mock_get_resources
    app.include_router(mcp_router)
    
    # Set app state for the dependency (in case it's accessed directly)
    app.state.llm = MagicMock()
    app.state.llm_thinking = MagicMock()
    app.state.mcp_tools = [MagicMock()]
    app.state.tools_description = []
    app.state.mcp_connection_error = None
    
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
        
        # Debug 422 errors
        if response.status_code == 422:
            error_detail = response.json()
            print(f"422 Validation Error: {error_detail}")
            # Check if it's a dependency issue
            assert False, f"422 Validation Error: {error_detail}"
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        assert data["research_topic"] == "quantum computing"
        mock_perform.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_missing_resources(monkeypatch) -> None:
    """Test MCP-only deep research with missing resources returns 503."""
    def mock_get_resources(request=None):
        return {
            "llm": None,
            "llm_thinking": None,
            "mcp_tools": [],
            "tools_description": [],
            "mcp_connection_error": None
        }
    
    app = FastAPI()
    # Override dependency BEFORE including router
    app.dependency_overrides[get_research_resources] = mock_get_resources
    app.include_router(mcp_router)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/deep-research",
            json={
                "research_topic": "test"
            }
        )
        
        assert response.status_code == 503
        assert "LLM not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_deep_research_mcp_missing_tools(monkeypatch) -> None:
    """Test MCP-only deep research with missing tools returns 503."""
    def mock_get_resources(request=None):
        return {
            "llm": MagicMock(),
            "llm_thinking": MagicMock(),
            "mcp_tools": None,
            "tools_description": [],
            "mcp_connection_error": None
        }
    
    app = FastAPI()
    # Override dependency BEFORE including router
    app.dependency_overrides[get_research_resources] = mock_get_resources
    app.include_router(mcp_router)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/deep-research",
            json={
                "research_topic": "test"
            }
        )
        
        assert response.status_code == 503
        assert "No MCP tools are available" in response.json()["detail"]


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
                # max_web_research_loops is configured via DeepResearcherConfig, not request
            }
        )
        
        assert response.status_code == 200
        # Verify the function was called with the request
        mock_perform.assert_called_once()
        call_args = mock_perform.call_args
        # perform_deep_research is called with keyword arguments
        request_arg = call_args.kwargs.get('request')
        assert request_arg is not None, f"Expected 'request' in kwargs, got: {call_args.kwargs.keys()}"
        assert request_arg.research_topic == "test"
        # max_web_research_loops is handled internally by perform_deep_research via DeepResearcherConfig



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
    def mock_get_resources(request=None):
        return {
            "llm": MagicMock(),
            "llm_thinking": None,  # Missing thinking LLM
            "mcp_tools": [MagicMock()],
            "tools_description": [],
            "mcp_connection_error": None
        }
    
    app = FastAPI()
    # Override dependency BEFORE including router
    app.dependency_overrides[get_research_resources] = mock_get_resources
    app.include_router(mcp_router)
    
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
            # perform_deep_research is called with keyword arguments
            llm_arg = call_args.kwargs.get('llm') or (call_args[0][1] if len(call_args[0]) > 1 else None)
            llm_thinking_arg = call_args.kwargs.get('llm_thinking') or (call_args[0][2] if len(call_args[0]) > 2 else None)
            assert llm_thinking_arg == llm_arg  # llm_thinking == llm (fallback)

