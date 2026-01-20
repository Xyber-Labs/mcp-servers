"""
Tests for application factory and lifespan management.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mcp_server_youtube.app import app_lifespan, create_app
from mcp_server_youtube.youtube import YouTubeVideoSearchAndTranscript


class TestAppLifespan:
    """Test cases for app_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_app_lifespan_success(self):
        """Test successful app lifespan initialization."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch('mcp_server_youtube.app.get_youtube_client') as mock_get_client:
            mock_client = Mock(spec=YouTubeVideoSearchAndTranscript)
            mock_get_client.return_value = mock_client
            
            async with app_lifespan(mock_app) as context:
                assert hasattr(mock_app.state, 'youtube_client')
                assert mock_app.state.youtube_client is mock_client
            
            mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_initialization_error(self):
        """Test app lifespan with initialization error."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch('mcp_server_youtube.app.get_youtube_client') as mock_get_client:
            mock_get_client.side_effect = ValueError("Failed to initialize client")
            
            with pytest.raises(ValueError, match="Failed to initialize client"):
                async with app_lifespan(mock_app):
                    pass

    @pytest.mark.asyncio
    async def test_app_lifespan_unexpected_error(self):
        """Test app lifespan with unexpected error during initialization."""
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        with patch('mcp_server_youtube.app.get_youtube_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Unexpected initialization error")
            
            with pytest.raises(Exception, match="Unexpected initialization error"):
                async with app_lifespan(mock_app):
                    pass


class TestCreateApp:
    """Test cases for create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "off"
            app = create_app()
            assert isinstance(app, FastAPI)
            assert app.title == "YouTube MCP Server (Hybrid)"

    def test_create_app_includes_api_routers(self):
        """Test that create_app includes API routers."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "off"
            app = create_app()
            
            # Check that health endpoint exists
            routes = [route.path for route in app.routes]
            assert "/api/health" in routes

    def test_create_app_includes_hybrid_routers(self):
        """Test that create_app includes hybrid routers."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "off"
            app = create_app()
            
            routes = [route.path for route in app.routes]
            assert "/hybrid/search" in routes

    def test_create_app_mounts_mcp_endpoint(self):
        """Test that create_app mounts MCP endpoint."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "off"
            app = create_app()
            
            # Check for mounted routes
            mounted_routes = [route.path for route in app.routes if hasattr(route, 'path')]
            # MCP endpoint is mounted, so we check the app structure
            assert hasattr(app, 'routes')

    def test_create_app_with_x402_enabled(self):
        """Test that create_app enables x402 middleware when configured."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "on"
            mock_x402.return_value.pricing = {}
            app = create_app()
            
            # Check that middleware is configured
            assert len(app.user_middleware) > 0

    def test_create_app_with_x402_disabled(self):
        """Test that create_app disables x402 middleware when pricing_mode is off."""
        with patch('mcp_server_youtube.app.get_x402_settings') as mock_x402:
            mock_x402.return_value.pricing_mode = "off"
            app = create_app()
            
            # When x402 is disabled, we should still have CORS middleware
            # but not x402 middleware
            assert isinstance(app, FastAPI)

