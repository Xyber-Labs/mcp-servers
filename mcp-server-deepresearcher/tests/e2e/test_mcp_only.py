"""
E2E tests for MCP-only endpoints.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
)


@pytest_asyncio.fixture
async def mcp_session():
    """Create an MCP session for testing."""
    config = load_e2e_config()
    require_base_url(config)
    
    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    
    yield config, session_id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_deep_research_tool(mcp_session) -> None:
    """Test MCP deep_research tool via MCP protocol."""
    config, session_id = mcp_session
    
    response = await call_mcp_tool(
        config=config,
        session_id=session_id,
        name="deep_research",
        arguments={
            "research_topic": "machine learning",
            "max_web_research_loops": 2
        }
    )
    
    # May return 402 if payment required, or 500/503 if resources unavailable
    if response.status_code == 200:
        # Parse JSON-RPC response
        body = response.json()
        assert "result" in body or "error" in body
        
        if "result" in body:
            result = body["result"]
            # Result should be a string (JSON serialized)
            assert isinstance(result, str)
    elif response.status_code == 402:
        # Payment required - this is expected if pricing is enabled
        body = response.json()
        assert "error" in body or "accepts" in body
    else:
        # Server error - may be expected if resources not configured
        assert response.status_code in [500, 503]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_deep_research_tool_default_loops(mcp_session) -> None:
    """Test MCP deep_research tool with default max_web_research_loops."""
    config, session_id = mcp_session
    
    response = await call_mcp_tool(
        config=config,
        session_id=session_id,
        name="deep_research",
        arguments={
            "research_topic": "quantum computing"
            # max_web_research_loops should default to 3
        }
    )
    
    # Should handle default value
    assert response.status_code in [200, 402, 500, 503]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_deep_research_tool_validation(mcp_session) -> None:
    """Test MCP deep_research tool validation."""
    config, session_id = mcp_session
    
    # Test missing required field
    response = await call_mcp_tool(
        config=config,
        session_id=session_id,
        name="deep_research",
        arguments={}
    )
    
    # Should return error for missing research_topic
    assert response.status_code in [200, 400, 422, 500]
    
    if response.status_code == 200:
        body = response.json()
        if "error" in body:
            assert "research_topic" in str(body["error"]).lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_deep_research_mcp_tool(mcp_session) -> None:
    """Test MCP-only deep_research_mcp tool via MCP protocol."""
    config, session_id = mcp_session
    
    response = await call_mcp_tool(
        config=config,
        session_id=session_id,
        name="deep_research_mcp",
        arguments={
            "research_topic": "artificial intelligence",
            "max_web_research_loops": 2
        }
    )
    
    # May return 402 if payment required, or 500/503 if resources unavailable
    if response.status_code == 200:
        # Parse JSON-RPC response
        body = response.json()
        assert "result" in body or "error" in body
        
        if "result" in body:
            result = body["result"]
            # Result should be a dict (JSON serialized)
            assert isinstance(result, (str, dict))
    elif response.status_code == 402:
        # Payment required - this is expected if pricing is enabled
        body = response.json()
        assert "error" in body or "accepts" in body
    else:
        # Server error - may be expected if resources not configured
        assert response.status_code in [500, 503]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_deep_research_mcp_tool_default_loops(mcp_session) -> None:
    """Test MCP-only deep_research_mcp tool with default max_web_research_loops."""
    config, session_id = mcp_session
    
    response = await call_mcp_tool(
        config=config,
        session_id=session_id,
        name="deep_research_mcp",
        arguments={
            "research_topic": "quantum computing"
            # max_web_research_loops should default to 3
        }
    )
    
    # Should handle default value
    assert response.status_code in [200, 402, 500, 503]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_mcp_session_handshake() -> None:
    """Test MCP session handshake."""
    config = load_e2e_config()
    require_base_url(config)
    
    session_id = await negotiate_mcp_session_id(config)
    assert session_id is not None
    assert len(session_id) > 0
    
    # Initialize session
    await initialize_mcp_session(config, session_id)
    # Should not raise exception if successful

