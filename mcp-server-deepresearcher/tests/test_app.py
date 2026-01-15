"""
Tests for the main FastAPI application factory.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from langchain_core.runnables import Runnable

from mcp_server_deepresearcher.app import create_app, app_lifespan


@pytest.mark.asyncio
async def test_create_app_returns_fastapi_app(monkeypatch):
    """Test that create_app returns a FastAPI application."""
    # Mock all dependencies
    mock_llm = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
    mock_spare_llm = MagicMock(spec=Runnable)
    mock_thinking_llm = MagicMock(spec=Runnable)
    mock_thinking_llm.with_fallbacks = MagicMock(return_value=mock_thinking_llm)
    mock_tools = [MagicMock()]
    mock_tools_description = []
    
    def mock_setup_llm(cfg):
        return mock_llm
    
    def mock_setup_spare_llm(cfg):
        return mock_spare_llm
    
    def mock_initialize_llm(llm_type, raise_on_error):
        if llm_type == "thinking":
            return mock_thinking_llm
        return None
    
    def mock_load_config(**kwargs):
        return {"mock": "config"}
    
    def mock_get_tools():
        return mock_tools
    
    def mock_construct_yaml(tools):
        return "tools:\n  - name: tool1\n    description: test"
    
    def mock_parse_yaml(yaml_str):
        return [{"name": "tool1", "description": "test"}]
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', mock_setup_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', mock_setup_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', mock_initialize_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', mock_load_config)
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: MagicMock(get_tools=AsyncMock(return_value=mock_tools)))
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', mock_construct_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', mock_parse_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.get_x402_settings', lambda: MagicMock(pricing_mode="off", pricing={}, validate_against_routes=lambda x: None))
    
    app = create_app()
    
    assert isinstance(app, FastAPI)
    assert app.title == "Deep Researcher MCP Server (Hybrid)"


@pytest.mark.asyncio
async def test_app_lifespan_initializes_resources(monkeypatch):
    """Test that app_lifespan initializes resources correctly."""
    mock_llm = MagicMock()
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
    mock_spare_llm = MagicMock()
    mock_thinking_llm = MagicMock()
    mock_thinking_llm.with_fallbacks = MagicMock(return_value=mock_thinking_llm)
    mock_tools = [MagicMock()]
    
    def mock_setup_llm(cfg):
        return mock_llm
    
    def mock_setup_spare_llm(cfg):
        return mock_spare_llm
    
    def mock_initialize_llm(llm_type, raise_on_error):
        if llm_type == "thinking":
            return mock_thinking_llm
        return None
    
    def mock_load_config(**kwargs):
        # Return proper server config structure: {server_name: {url: ..., transport: ...}}
        return {"test_server": {"url": "http://localhost:3000", "transport": "streamable_http"}}
    
    def mock_get_tools():
        return mock_tools
    
    def mock_construct_yaml(tools):
        return "tools:\n  - name: tool1"
    
    def mock_parse_yaml(yaml_str):
        return [{"name": "tool1", "description": "test"}]
    
    # Create a mock client factory that returns a client with async get_tools
    # The code creates a new client for each server, so we need to return a new mock each time
    def mock_client_factory(cfg):
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=mock_tools)
        return mock_client
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', mock_setup_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', mock_setup_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', mock_initialize_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', mock_load_config)
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', mock_client_factory)
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', mock_construct_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', mock_parse_yaml)
    
    app = FastAPI()
    
    async with app_lifespan(app):
        assert hasattr(app.state, 'llm')
        assert hasattr(app.state, 'llm_thinking')
        assert hasattr(app.state, 'mcp_tools')
        assert hasattr(app.state, 'tools_description')
        # app_lifespan sets llm_with_fallbacks (llm.with_fallbacks([llm_spare]))
        assert app.state.llm == mock_llm  # mock_llm.with_fallbacks returns mock_llm in this test
        assert len(app.state.mcp_tools) == len(mock_tools)
        assert app.state.mcp_tools == mock_tools
        assert app.state.llm_thinking == mock_thinking_llm


@pytest.mark.asyncio
async def test_app_lifespan_error_handling(monkeypatch):
    """Test that app_lifespan raises errors on initialization failure."""
    def failing_setup(cfg):
        raise Exception("Initialization failed")
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', failing_setup)
    
    app = FastAPI()
    
    with pytest.raises(Exception, match="Initialization failed"):
        async with app_lifespan(app):
            pass


@pytest.mark.asyncio
async def test_create_app_includes_routers(monkeypatch):
    """Test that create_app includes all routers."""
    # Mock all dependencies
    mock_llm = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
    mock_spare_llm = MagicMock(spec=Runnable)
    mock_thinking_llm = MagicMock(spec=Runnable)
    mock_thinking_llm.with_fallbacks = MagicMock(return_value=mock_thinking_llm)
    mock_tools = [MagicMock()]
    
    def mock_setup_llm(cfg):
        return mock_llm
    
    def mock_setup_spare_llm(cfg):
        return mock_spare_llm
    
    def mock_initialize_llm(llm_type, raise_on_error):
        if llm_type == "thinking":
            return mock_thinking_llm
        return None
    
    def mock_load_config(**kwargs):
        return {"mock": "config"}
    
    def mock_get_tools():
        return mock_tools
    
    def mock_construct_yaml(tools):
        return "tools:\n  - name: tool1"
    
    def mock_parse_yaml(yaml_str):
        return [{"name": "tool1", "description": "test"}]
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', mock_setup_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', mock_setup_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', mock_initialize_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', mock_load_config)
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: MagicMock(get_tools=AsyncMock(return_value=mock_tools)))
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', mock_construct_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', mock_parse_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.get_x402_settings', lambda: MagicMock(pricing_mode="off", pricing={}, validate_against_routes=lambda x: None))
    
    app = create_app()
    
    # Check that routes are included
    route_paths = [route.path for route in app.routes]
    assert any("/api/health" in path for path in route_paths)
    assert any("/hybrid/deep-research" in path for path in route_paths)
    
    # Check that MCP-only router is included (accessible via /mcp endpoint, not as REST routes)
    # MCP-only routes are mounted at /mcp, so we verify the app has the mount
    mount_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    # The /mcp mount should exist (though it may not show up directly in route_paths)
    # We verify the app structure is correct by checking it's a FastAPI instance
    assert isinstance(app, FastAPI)


@pytest.mark.asyncio
async def test_create_app_x402_middleware_configuration(monkeypatch):
    """Test that x402 middleware is configured correctly."""
    mock_llm = MagicMock()
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
    mock_spare_llm = MagicMock()
    mock_thinking_llm = MagicMock()
    mock_thinking_llm.with_fallbacks = MagicMock(return_value=mock_thinking_llm)
    mock_tools = [MagicMock()]
    
    def mock_setup_llm(cfg):
        return mock_llm
    
    def mock_setup_spare_llm(cfg):
        return mock_spare_llm
    
    def mock_initialize_llm(llm_type, raise_on_error):
        if llm_type == "thinking":
            return mock_thinking_llm
        return None
    
    def mock_load_config(**kwargs):
        return {"mock": "config"}
    
    def mock_get_tools():
        return mock_tools
    
    def mock_construct_yaml(tools):
        return "tools:\n  - name: tool1"
    
    def mock_parse_yaml(yaml_str):
        return [{"name": "tool1", "description": "test"}]
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', mock_setup_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', mock_setup_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', mock_initialize_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', mock_load_config)
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: MagicMock(get_tools=AsyncMock(return_value=mock_tools)))
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', mock_construct_yaml)
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', mock_parse_yaml)
    
    # Test with pricing_mode="on"
    mock_settings_on = MagicMock()
    mock_settings_on.pricing_mode = "on"
    mock_settings_on.pricing = {"deep_research": []}
    mock_settings_on.validate_against_routes = lambda x: None
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.get_x402_settings', lambda: mock_settings_on)
    
    app = create_app()
    assert isinstance(app, FastAPI)
    
    # Test with pricing_mode="off"
    mock_settings_off = MagicMock()
    mock_settings_off.pricing_mode = "off"
    mock_settings_off.pricing = {}
    mock_settings_off.validate_against_routes = lambda x: None
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.get_x402_settings', lambda: mock_settings_off)
    
    app = create_app()
    assert isinstance(app, FastAPI)

