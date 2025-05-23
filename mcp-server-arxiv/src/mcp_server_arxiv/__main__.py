# This template file mostly will stay the same for all MCP servers
# It is responsible for launching a uvicorn server with the given MCP server

import argparse
import logging
import os
import uvicorn
from fastapi import FastAPI

from mcp_server_arxiv.logging_config import (configure_logging,
                                           LOGGING_CONFIG)

from mcp_server_arxiv.server import mcp_server

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #

def create_app() -> FastAPI:
    """Create a FastAPI application that can serve the provided mcp server with SSE."""
    # Create the MCP ASGI app
    mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http")
    
    # Create FastAPI app
    app = FastAPI(
        title="ArXiv MCP Server",
        description="MCP server for searching and retrieving papers from ArXiv",
        version="1.0.0",
        lifespan=mcp_app.router.lifespan_context
    )   
    
    # Mount MCP server
    app.mount("/mcp-server", mcp_app)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ArXiv MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_ARXIV_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_ARXIV_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_ARXIV_PORT", "8006")), # Default port 8006 for ArXiv
        help="Port to listen on (Default: MCP_ARXIV_PORT or 8006)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_ARXIV_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: MCP_ARXIV_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting ArXiv MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_arxiv.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=LOGGING_CONFIG.get("root", {}).get("level", "info").lower(),
        factory=True
    )