from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_gitparser.api_routers import routers as api_routers
from mcp_server_gitparser.config import get_app_settings
from mcp_server_gitparser.hybrid_routers import routers as hybrid_routers
from mcp_server_gitparser.mcp_routers import routers as mcp_routers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    settings = get_app_settings()
    settings.docs_path.mkdir(parents=True, exist_ok=True)
    logger.info("Lifespan: docs directory ready at %s", settings.docs_path)
    yield


def create_app() -> FastAPI:
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="Gitparser")
    mcp_app = mcp_server.http_app(path="/")

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Gitparser MCP Server (Hybrid)",
        description="Parse GitBook sites and GitHub repositories into Markdown via REST and MCP.",
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # API-only routes
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes (REST + MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    logger.info("Application setup complete.")
    return app

