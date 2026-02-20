import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_twitter.api_routers import routers as api_routers
from mcp_twitter.dependencies import DependencyContainer
from mcp_twitter.hybrid_routers import routers as hybrid_routers
from mcp_twitter.middlewares import X402WrapperMiddleware
from mcp_twitter.x402_integration import get_x402_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Manages application resources: database engine, dependencies."""
    from mcp_twitter.config import AppSettings

    settings = AppSettings()
    engine = None
    database = None

    # Initialize database if configured
    if settings.database.is_configured:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            from mcp_twitter.db import CacheRepository

            engine = create_engine(
                settings.database.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
            )
            database = CacheRepository(sessionmaker(bind=engine))
            logger.info("Database cache enabled")
        except Exception as e:
            logger.warning(f"Database cache not available: {e}")
    else:
        logger.info("Database not configured - running without cache.")

    DependencyContainer.create(
        apify_token=settings.apify.apify_token,
        actor_name=settings.apify.actor_name,
        database=database,
    )
    logger.info(f"Lifespan: Initialized with actor: {settings.apify.actor_name}")

    yield

    DependencyContainer.clear()
    if engine is not None:
        engine.dispose()
        logger.info("Database engine disposed.")
    logger.info("Lifespan: Shutdown complete.")


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
    # Create a FastAPI app containing hybrid endpoints (exposed as both REST and MCP tools)
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/", stateless_http=True)

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
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

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # First, validate that pricing_mode is consistent with pricing config
    # This will fail fast if pricing_mode='on' but no config exists
    x402_settings = get_x402_settings()
    x402_settings.validate_pricing_mode()

    # Then validate that all priced endpoints actually exist
    # and warn about any misconfiguration
    all_routes = app.routes + mcp_source_app.routes
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app
