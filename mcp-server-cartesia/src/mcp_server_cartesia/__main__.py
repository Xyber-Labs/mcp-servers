# This template file mostly will stay the same for all MCP servers
# It is responsible for launching a uvicorn server with the given MCP server

import argparse
import logging
import os
import uvicorn
from fastapi import FastAPI

from mcp_server_cartesia.logging_config import (configure_logging,
                                              logging_level)

from mcp_server_cartesia.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #

def create_app() -> FastAPI:
    """Create a FastAPI application that can serve the provided mcp server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    
    # Create FastAPI app
    app = FastAPI(
        title="Cartesia MCP Server",
        description="MCP server for text-to-speech generation using Cartesia",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context
    )   
    
    # Mount MCP server
    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Cartesia MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_CARTESIA_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_CARTESIA_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_CARTESIA_PORT", "8005")), # Default port 8005 for Cartesia
        help="Port to listen on (Default: MCP_CARTESIA_PORT or 8005)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("CARTESIA_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: CARTESIA_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Cartesia MCP server on {args.host}:{args.port}")

    # Don't forget to change the module name to your own!
    uvicorn.run(
        "mcp_server_cartesia.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True
    ) 