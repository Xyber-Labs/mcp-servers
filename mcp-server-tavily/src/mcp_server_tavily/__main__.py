import argparse
import logging

import uvicorn

from mcp_server_tavily.app import create_app
from mcp_server_tavily.config import get_app_settings
from mcp_server_tavily.logging_config import get_logging_config

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Tavily MCP Server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to.")
    parser.add_argument(
        "--port", type=int, default=8006, help="Port to listen on."
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable hot reload.",
    )
    args = parser.parse_args()

    settings = get_app_settings()
    settings.host = args.host
    settings.port = args.port
    settings.hot_reload = args.reload

    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(
        "mcp_server_tavily.app:create_app",
        host=settings.host,
        port=settings.port,
        reload=settings.hot_reload,
        log_config=get_logging_config(),
        factory=True,
    )
