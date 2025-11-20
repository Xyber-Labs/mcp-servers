import argparse
import logging

import uvicorn

from mcp_server_arxiv.config import get_app_settings
from mcp_server_arxiv.logging_config import get_logging_config

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    settings = get_app_settings()
    parser = argparse.ArgumentParser(description="Run the ArXiv MCP Server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to.")
    parser.add_argument(
        "--port", type=int, default=settings.port, help="Port to listen on."
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.hot_reload,
        help="Enable hot reload.",
    )
    args = parser.parse_args()

    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(
        "mcp_server_arxiv.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=get_logging_config(),
        factory=True,
    )
