import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from mcp_server_together_imgen.api_router import router as api_router
from mcp_server_together_imgen.logging_config import configure_logging, logging_level

configure_logging()
logger = logging.getLogger(__name__)


# --- Application Factory --- #
def create_app() -> FastAPI:
    """Create a FastAPI application that serves the API and MCP server."""
    # Create FastAPI app
    app = FastAPI(
        title="Together Image Generation MCP Server",
        description="MCP server for generating images using Together AI",
        version="0.1.0",
    )

    # Mount API router - this is our single source of truth for the logic
    app.include_router(api_router, prefix="/api", tags=["api"])

    mcp_server = FastApiMCP(app)
    mcp_server.mount_http()

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Together Image Generation MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TOGETHER_IMGEN_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TOGETHER_IMGEN_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TOGETHER_IMGEN_PORT", "8000")),
        help="Port to listen on (Default: MCP_TOGETHER_IMGEN_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_TOGETHER_IMGEN_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: MCP_TOGETHER_IMGEN_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(
        f"Starting Together Image Generation MCP server on {args.host}:{args.port}"
    )

    uvicorn.run(
        "mcp_server_together_imgen.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )
