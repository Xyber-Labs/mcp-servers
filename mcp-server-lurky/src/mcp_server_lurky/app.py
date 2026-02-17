import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_lurky.api_routers import routers as api_routers
from mcp_server_lurky.dependencies import DependencyContainer
from mcp_server_lurky.hybrid_routers import routers as hybrid_routers
from mcp_server_lurky.mcp_routers import routers as mcp_routers
from mcp_server_lurky.middlewares.x402_wrapper import X402WrapperMiddleware
from mcp_server_lurky.x402_integration import get_x402_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info("Lifespan: Initializing application services...")

    DependencyContainer.initialize()

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")

    await DependencyContainer.shutdown()

    logger.info("Lifespan: Services shut down gracefully.")


def create_app() -> FastAPI:
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    # Include hybrid routers in MCP source
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    # Include MCP-only routers in MCP source
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="Lurky")
    mcp_app = mcp_server.http_app(path="/", stateless_http=True)

    # --- Combined Lifespan ---
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Lurky MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes
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
