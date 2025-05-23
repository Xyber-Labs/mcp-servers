### src/mcp_server_telegram/__main__.py
import argparse
import logging
import os
import uvicorn
from fastapi import FastAPI

from mcp_server_telegram.logging_config import (configure_logging,
                                              LOGGING_LEVEL as logging_level)

from mcp_server_telegram.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #

def create_app() -> FastAPI:
    """Create a FastAPI application that can serve the provided mcp server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    
    # Create FastAPI app
    app = FastAPI(
        title="Telegram MCP Server",
        description="MCP server for sending messages to Telegram channels",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context
    )   
    
    # Mount MCP server
    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Telegram MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TELEGRAM_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TELEGRAM_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TELEGRAM_PORT", "8002")), # Default port 8002 for Telegram
        help="Port to listen on (Default: MCP_TELEGRAM_PORT or 8002)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("TELEGRAM_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TELEGRAM_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Telegram MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_telegram.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True
    )