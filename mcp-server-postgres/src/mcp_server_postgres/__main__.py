import argparse
import logging
import os
from mcp_server_postgres.logging_config import configure_logging, logging_level
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.requests import Request
import uvicorn
from starlette.applications import Starlette
from mcp_server_postgres.server import server


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
        debug = logging_level == "DEBUG",
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Postgres MCP server')
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_POSTGRES_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_POSTGRES_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_POSTGRES_PORT", "8000")), # Default port 8000 for Postgres
        help="Port to listen on (Default: MCP_POSTGRES_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("POSTGRES_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: POSTGRES_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(f"Starting Postgres MCP server on {args.host}:{args.port}")
    
    uvicorn.run(
        "mcp_server_postgres.__main__:create_starlette_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True
    ) 