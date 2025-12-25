"""
Main application factory for the MCP YouTube server.

Main responsibility: Compose the FastAPI/MCP application and manage its lifecycle,
including startup/shutdown, middleware, and router mounting.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from mcp_server_youtube.api_routers import routers as api_routers
from mcp_server_youtube.config import get_x402_settings
from mcp_server_youtube.hybrid_routers import routers as hybrid_routers
from mcp_server_youtube.mcp_routers import routers as mcp_routers
from mcp_server_youtube.middlewares import X402WrapperMiddleware
from mcp_server_youtube.youtube import get_youtube_client, YouTubeVideoSearchAndTranscript

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Currently manages:
    - YouTubeVideoSearchAndTranscript client for API calls
    """
    logger.info("Lifespan: Initializing application services...")

    # Initialize YouTube client
    youtube_client: YouTubeVideoSearchAndTranscript = get_youtube_client()
    app.state.youtube_client = youtube_client

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")

    logger.info("Lifespan: Services shut down gracefully.")


def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates an MCP server from hybrid and MCP-only routers
    2. Combines lifespans for proper resource management
    3. Configures API routes with appropriate prefixes
    4. Sets up x402 payment middleware
    5. Validates pricing configuration against available routes

    Returns:
        Configured FastAPI application ready to serve requests
    """
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="YouTube MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
        version="2.0.0",
        lifespan=combined_lifespan,
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc alternative
        openapi_url="/openapi.json",  # OpenAPI schema
    )

    # --- CORS Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/v1/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api/v1")

    # Hybrid routes: accessible via /hybrid/* (REST) and /mcp (MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # MCP-only routes: NOT mounted as REST endpoints
    # They're only accessible through the /mcp endpoint below

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    all_routes = app.routes + mcp_source_app.routes
    x402_settings = get_x402_settings()
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        app.add_middleware(
            X402WrapperMiddleware, tool_pricing=x402_settings.pricing
        )
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app

