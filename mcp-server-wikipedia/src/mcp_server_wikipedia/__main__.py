import argparse
import logging

import uvicorn

from mcp_server_wikipedia.config import get_app_settings
from mcp_server_wikipedia.logging_config import configure_logging, logging_level

configure_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    settings = get_app_settings()

    parser = argparse.ArgumentParser(description="Run Wikipedia MCP server")
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (Default: {settings.host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to listen on (Default: {settings.port})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.hot_reload,
        help=f"Enable hot reload (Default: {settings.hot_reload})",
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
