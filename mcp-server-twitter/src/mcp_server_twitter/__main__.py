import argparse
import logging
import os

import uvicorn

from .logging_config import configure_logging, logging_level
from .server import app

configure_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Twitter MCP server with FastAPI")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TWITTER_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TWITTER_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TWITTER_PORT", "8000")),
        help="Port to listen on (Default: MCP_TWITTER_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("TWITTER_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TWITTER_HOT_RELOAD)",
    )

    args = parser.parse_args()
    
    logger.info("Starting Twitter MCP server with FastAPI", extra={
        "operation": "server_startup",
        "status": "START",
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "log_level": logging_level
    })

    uvicorn.run(
        "mcp_server_twitter.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
    )