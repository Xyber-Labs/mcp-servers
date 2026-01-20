"""
Tests for MCP-only endpoints.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import Context
from fastmcp.exceptions import ToolError

from mcp_server_deepresearcher.app import get_mcp_server
from mcp_server_deepresearcher.schemas import DeepResearchRequest


_mcp_server = None

async def get_deep_research_func():
    """Get the deep_research function from mcp_server tools."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = get_mcp_server()
    tools = await _mcp_server.get_tools()
    if 'deep_research' in tools:
        return tools['deep_research'].fn
    raise ValueError("deep_research tool not found")


@pytest.fixture
def mock_mcp_context():
    """Create a mock MCP context with required resources."""
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        "llm": MagicMock(),
        "llm_thinking": MagicMock(),
        "mcp_tools": [MagicMock(name="tool1"), MagicMock(name="tool2")],
        "tools_description": []
    }
    return ctx


@pytest.mark.asyncio
async def test_mcp_deep_research_success(mock_mcp_context):
    """Test successful MCP deep research execution."""
    request = DeepResearchRequest(
        research_topic="machine learning"
    )
    
    mock_result = {
        "running_summary": {
            "result": "ML research completed",
            "sources": ["source1.com"],
            "query_count": 2
        }
    }
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        deep_research_func = await get_deep_research_func()
        result = await deep_research_func(mock_mcp_context, request)
        
        # Result should be JSON string
        import json
        parsed_result = json.loads(result)
        assert parsed_result == mock_result["running_summary"]
        mock_agent.graph.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_deep_research_missing_llm():
    """Test MCP deep research with missing LLM raises ToolError."""
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        "llm": None,
        "mcp_tools": [MagicMock()]
    }
    
    request = DeepResearchRequest(research_topic="test")
    
    deep_research_func = await get_deep_research_func()
    with pytest.raises(ToolError) as exc_info:
        await deep_research_func(ctx, request)
    
    assert "Shared resources" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mcp_deep_research_missing_tools():
    """Test MCP deep research with missing tools raises ToolError."""
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        "llm": MagicMock(),
        "mcp_tools": None
    }
    
    request = DeepResearchRequest(research_topic="test")
    
    deep_research_func = await get_deep_research_func()
    with pytest.raises(ToolError) as exc_info:
        await deep_research_func(ctx, request)
    
    assert "Shared resources" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mcp_deep_research_agent_error(mock_mcp_context):
    """Test MCP deep research handles agent errors."""
    request = DeepResearchRequest(research_topic="test")
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.graph.ainvoke = AsyncMock(side_effect=Exception("Agent error"))
        mock_agent_class.return_value = mock_agent
        
        deep_research_func = await get_deep_research_func()
        with pytest.raises(ToolError) as exc_info:
            await deep_research_func(mock_mcp_context, request)
        
        assert "unexpected error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_mcp_deep_research_default_loops(mock_mcp_context):
    """Test MCP deep research uses default max_web_research_loops."""
    request = DeepResearchRequest(research_topic="test")
    # max_web_research_loops defaults to 3
    
    mock_result = {"running_summary": {}}
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        deep_research_func = await get_deep_research_func()
        await deep_research_func(mock_mcp_context, request)
        
        call_args = mock_agent.graph.ainvoke.call_args
        config = call_args[1].get("config", {})
        configurable = config.get("configurable", {})
        assert configurable.get("max_web_research_loops") == 3



@pytest.mark.asyncio
async def test_mcp_deep_research_empty_summary(mock_mcp_context):
    """Test MCP deep research handles empty running_summary."""
    request = DeepResearchRequest(research_topic="test")
    
    mock_result = {
        "running_summary": {},
        "report": {}
    }
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        deep_research_func = await get_deep_research_func()
        result = await deep_research_func(mock_mcp_context, request)
        
        import json
        parsed_result = json.loads(result)
        # Should handle None gracefully
        assert isinstance(parsed_result, dict)


@pytest.mark.asyncio
async def test_mcp_deep_research_langfuse_integration(mock_mcp_context, monkeypatch):
    """Test MCP deep research with Langfuse tracking."""
    request = DeepResearchRequest(research_topic="test")
    
    mock_result = {"running_summary": {}}
    
    # Mock Langfuse config
    mock_langfuse_config = MagicMock()
    mock_langfuse_config.LANGFUSE_API_KEY = "test-key"
    mock_langfuse_config.LANGFUSE_SECRET_KEY = "test-secret"
    mock_langfuse_config.LANGFUSE_HOST = "https://test.langfuse.com"
    
    monkeypatch.setattr(
        'mcp_server_deepresearcher.server.LangfuseConfig',
        lambda: mock_langfuse_config
    )
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher') as mock_agent_class, \
         patch('mcp_server_deepresearcher.server.CallbackHandler') as mock_handler_class:
        mock_agent = MagicMock()
        mock_agent.graph.ainvoke = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent
        
        mock_handler = MagicMock()
        mock_handler.flush = MagicMock()
        mock_handler_class.return_value = mock_handler
        
        deep_research_func = await get_deep_research_func()
        await deep_research_func(mock_mcp_context, request)
        
        # Verify Langfuse handler was created
        mock_handler_class.assert_called_once()

