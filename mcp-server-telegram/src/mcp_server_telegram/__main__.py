### src/mcp_server_telegram/__main__.py
import argparse
import logging
import os

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from mcp_server_telegram.logging_config import configure_logging, LOGGING_LEVEL
from mcp_server_telegram.server import server 
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

# Apply logging configuration at the earliest
configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #

def create_starlette_app() -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE."""

    sse_transport = SseServerTransport("/messages/") 
    mcp_server_instance: Server = server 

    async def handle_sse(request: Request) -> None:
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server_instance.run(
                read_stream,
                write_stream,
                mcp_server_instance.create_initialization_options(),
            )

    return Starlette(
        debug=(LOGGING_LEVEL == "DEBUG"), # Use LOGGING_LEVEL from logging_config
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse_transport.handle_post_message),
        ],
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run MCP Starlette server for Telegram')
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TELEGRAM_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TELEGRAM_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TELEGRAM_PORT", "8002")), # Default port 8002 for Telegram
        help="Port to listen on (Default: MCP_TELEGRAM_PORT or 8002)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("TELEGRAM_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TELEGRAM_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting MCP Telegram Server on http://{args.host}:{args.port}")
    logger.info(f"Logging level set to: {LOGGING_LEVEL}")
    if args.reload:
        logger.info("Hot reload enabled.")
    
    # Run Uvicorn server
    uvicorn.run(
        "mcp_server_telegram.__main__:create_starlette_app", # Path to the app factory
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=LOGGING_LEVEL.lower(), # uvicorn log level
        factory=True
    )