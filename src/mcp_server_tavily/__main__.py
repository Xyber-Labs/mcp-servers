import argparse
import logging
import os

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp_server_calculator.logging_config import (configure_logging,
                                                  logging_level)
from mcp_server_calculator.server import server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

configure_logging()
logger = logging.getLogger(__name__)

# --- Application Factory --- #


def create_starlette_app() -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""

    sse = SseServerTransport("/messages/")
    mcp_server: Server = server

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=logging_level == "DEBUG",
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    # --- Command Line Argument Parsing ---
    parser = argparse.ArgumentParser(description='Run MCP Starlette server for Tavily Web Search')
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TAVILY_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TAVILY_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TAVILY_PORT", "8005")), # Default port 8005 for Tavily
        help="Port to listen on (Default: MCP_TAVILY_PORT or 8005)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("TAVILY_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: TAVILY_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting MCP Tavily Server on http://{args.host}:{args.port}")
    
    # Run Uvicorn server
    uvicorn.run(
        "mcp_server_tavily.__main__:create_starlette_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True
    )
