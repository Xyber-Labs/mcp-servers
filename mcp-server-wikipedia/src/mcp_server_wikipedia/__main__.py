import argparse
import logging
import os

import uvicorn

from mcp_server_wikipedia.logging_config import configure_logging, logging_level

configure_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Wikipedia MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_WIKIPEDIA_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_WIKIPEDIA_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_WIKIPEDIA_PORT", "8006")),
        help="Port to listen on (Default: MCP_WIKIPEDIA_PORT or 8006)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("WIKIPEDIA_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: WIKIPEDIA_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Wikipedia MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_wikipedia.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )
