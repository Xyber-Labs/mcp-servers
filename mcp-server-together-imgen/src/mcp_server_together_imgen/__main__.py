import argparse
import logging

import uvicorn

from mcp_server_together_imgen.config import get_app_settings
from mcp_server_together_imgen.logging_config import get_logging_config

logger = logging.getLogger(__name__)


# --- Uvicorn Runner ---
if __name__ == "__main__":
    settings = get_app_settings()
    parser = argparse.ArgumentParser(
        description="Run the Together Image Generation MCP Server."
    )
    parser.add_argument("--host", default=settings.host, help="Host to bind to.")
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
        "mcp_server_together_imgen.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        # Use our logging config so every worker / reload process is consistent
        log_config=get_logging_config(),
        factory=True,
    )
