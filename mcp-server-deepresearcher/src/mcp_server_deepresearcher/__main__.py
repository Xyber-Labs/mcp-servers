"""
CLI entry point that configures logging, parses arguments, and starts the server with Uvicorn.
"""

import argparse
import logging
import os

import uvicorn

from mcp_server_deepresearcher.logging_config import LOGGING_LEVEL

# The configure_logging() call is removed from here.
# Uvicorn will handle the logging configuration.
logger = logging.getLogger(__name__)


# --- Uvicorn Runner ---
if __name__ == "__main__":
    default_host = os.getenv("MCP_DEEP_RESEARCHER_HOST", "0.0.0.0")
    default_port = int(os.getenv("MCP_DEEP_RESEARCHER_PORT", "8003"))
    default_reload = os.getenv("DEEP_RESEARCHER_HOT_RELOAD", "false").lower() in ("true", "1", "t")
    
    parser = argparse.ArgumentParser(description="Run the Deep Researcher MCP Server.")
    parser.add_argument("--host", default=default_host, help="Host to bind to.")
    parser.add_argument(
        "--port", type=int, default=default_port, help="Port to listen on."
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=default_reload,
        help="Enable hot reload.",
    )
    args = parser.parse_args()

    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(
        "mcp_server_deepresearcher.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )
