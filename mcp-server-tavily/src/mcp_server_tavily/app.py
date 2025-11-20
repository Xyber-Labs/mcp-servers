import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_tavily.api_routers import routers as api_routers
from mcp_server_tavily.config import get_x402_settings
from mcp_server_tavily.hybrid_routers import routers as hybrid_routers
from mcp_server_tavily.middlewares import X402WrapperMiddleware
from mcp_server_tavily.tavily import _TavilyService
from mcp_server_tavily.tavily import get_tavily_service as create_tavily_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info("Lifespan: Initializing application services...")

    tavily_service: _TavilyService = create_tavily_service()
    app.state.tavily_service = tavily_service

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")

    logger.info("Lifespan: Services shut down gracefully.")


def create_app() -> FastAPI:
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)

    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/")

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    app = FastAPI(
        title="Tavily MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
        version="2.0.0",
        lifespan=combined_lifespan,
    )

    for router in api_routers:
        app.include_router(router, prefix="/api")

    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    app.mount("/mcp", mcp_app)

    all_routes = app.routes + mcp_source_app.routes
    x402_settings = get_x402_settings()
    x402_settings.validate_against_routes(all_routes)

    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app

