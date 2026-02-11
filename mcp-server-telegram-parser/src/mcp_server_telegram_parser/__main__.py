import argparse
import logging
import os

import uvicorn

from mcp_server_telegram_parser.app import create_app
from mcp_server_telegram_parser.logging_config import LOGGING_LEVEL as logging_level
from mcp_server_telegram_parser.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

# Re-export for ASGI loaders that expect create_app in __main__
__all__ = ["create_app"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Telegram Parser MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TELEGRAM_PARSER_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TELEGRAM_PARSER_PORT", "8012")),
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_TELEGRAM_PARSER_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
    )

    args = parser.parse_args()
    logger.info(f"Starting Telegram Parser MCP server on {args.host}:{args.port}")

    uvicorn.run(
        "mcp_server_telegram_parser.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )
