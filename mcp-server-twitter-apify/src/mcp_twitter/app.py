"""
This module may change slightly as you adapt routing, metadata, and middleware to your own MCP server.

Main responsibility: Compose the FastAPI/MCP application and manage its lifecycle, including startup/shutdown, middleware, and router mounting.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_twitter.api_routers import routers as api_routers
from mcp_twitter.config import get_x402_settings
from mcp_twitter.hybrid_routers import routers as hybrid_routers
from mcp_twitter.mcp_routers import routers as mcp_routers
from mcp_twitter.middlewares import X402WrapperMiddleware
from mcp_twitter.twitter import (
    QueryRegistry,
    TwitterScraper,
    build_default_registry,
)

logger = logging.getLogger(__name__)


# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Currently manages:
    - QueryRegistry for predefined queries
    - TwitterScraper for API calls

    Note: The x402 middleware manages its own HTTP client lifecycle using
    context managers, so no external resource management is needed.
    """
    logger.info("Lifespan: Initializing application services...")

    # Initialize registry
    registry: QueryRegistry = build_default_registry()
    app.state.registry = registry

    # Initialize scraper
    from mcp_twitter.config import AppSettings
    settings = AppSettings()
    token = settings.apify.apify_token
    if not token:
        raise RuntimeError("APIFY_TOKEN not configured. Set it in .env or environment.")
    
    actor_name = settings.apify.actor_name
    scraper = TwitterScraper(
        apify_token=token,
        results_dir=None,  # Disable file-based storage, use DB cache only
        actor_name=actor_name,
        output_format="min",
        use_cache=True,  # Enable database cache
    )
    app.state.scraper = scraper
    
    logger.info(f"Lifespan: Initialized with actor: {actor_name}")
    try:
        from db import get_db_instance
        db = get_db_instance()
        logger.info("Lifespan: Database cache enabled")
    except Exception as e:
        logger.warning(f"Lifespan: Database cache not available: {e}")

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")

    # Cleanup (scraper doesn't have async close, but we can clear references)
    app.state.scraper = None
    app.state.registry = None

    logger.info("Lifespan: Services shut down gracefully.")


# --- Application Factory ---
def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates an MCP server from MCP-only routers (hybrid routers are REST-only)
    2. Combines lifespans for proper resource management
    3. Configures API routes with appropriate prefixes
    4. Sets up x402 payment middleware
    5. Validates pricing configuration against available routes

    Returns:
        Configured FastAPI application ready to serve requests

    """
    # --- MCP Server Generation ---
    # Create a FastAPI app containing only MCP-exposed endpoints
    mcp_source_app = FastAPI(title="MCP Source")
    # Only include MCP-only routers (not hybrid routers which are REST + MCP)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            # Copy state from main app to mcp_source_app so MCP endpoints can access it
            # This is necessary because mcp_source_app is a separate FastAPI instance
            if hasattr(app.state, "registry"):
                mcp_source_app.state.registry = app.state.registry
            if hasattr(app.state, "scraper"):
                mcp_source_app.state.scraper = app.state.scraper
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Twitter MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
        version="2.0.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes: accessible via /hybrid/* (REST only, not exposed as MCP tools)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # MCP-only routes: NOT mounted as REST endpoints
    # They're only accessible through the /mcp endpoint below

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # This validates that all priced endpoints actually exist
    # and warns about any misconfiguration
    all_routes = app.routes + mcp_source_app.routes
    x402_settings = get_x402_settings()
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app

