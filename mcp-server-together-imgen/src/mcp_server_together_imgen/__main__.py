import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from mcp_server_together_imgen.api_router import router as api_router
from mcp_server_together_imgen.logging_config import configure_logging, logging_level

configure_logging()
logger = logging.getLogger(__name__)


# --- Application Factory --- #
def create_app() -> FastAPI:
    """Create a FastAPI application that serves the API and MCP server."""
    # Create FastAPI app
    app = FastAPI(
        title="Together Image Generation MCP Server",
        description="MCP server for generating images using Together AI",
        version="0.1.0",
    )

    # Mount API router - this is our single source of truth for the logic
    app.include_router(api_router, prefix="/api", tags=["api"])

    mcp_server = FastApiMCP(app)
    mcp_server.mount_http()

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Together Image Generation MCP server")
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_TOGETHER_IMGEN_HOST", "0.0.0.0"),
        help="Host to bind to (Default: MCP_TOGETHER_IMGEN_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_TOGETHER_IMGEN_PORT", "8000")),
        help="Port to listen on (Default: MCP_TOGETHER_IMGEN_PORT or 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("MCP_TOGETHER_IMGEN_HOT_RELOAD", "false").lower()
        in ("true", "1", "t", "yes"),
        help="Enable hot reload (env: MCP_TOGETHER_IMGEN_HOT_RELOAD)",
    )

    args = parser.parse_args()
    logger.info(
        f"Starting Together Image Generation MCP server on {args.host}:{args.port}"
    )
    
    # Log important URLs
    # Note: When running in Docker, the external port may differ (check docker-compose.yml)
    # Default external port is 8016, but internal is 8000
    base_url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}"
    external_port = os.getenv("MCP_TOGETHER_IMGEN_EXTERNAL_PORT", "8016")
    external_url = f"http://localhost:{external_port}"
    
    logger.info("=" * 70)
    logger.info("Available Endpoints:")
    logger.info("=" * 70)
    logger.info(f"  📚 Swagger UI (API Documentation): {external_url}/docs")
    logger.info(f"     ⚠️  Note: Swagger is at /docs (NOT /api/images/docs)")
    logger.info("")
    logger.info(f"  🖼️  Generate Image (POST):{external_url}/api/images")
    logger.info(f"  📋 List Models (GET):{external_url}/api/models")
    logger.info(f"  🔌 MCP Endpoint (POST):{external_url}/mcp")
    logger.info("")
    logger.info(f"  🔧 Internal URL:{base_url}")
    logger.info("=" * 70)

    uvicorn.run(
        "mcp_server_together_imgen.__main__:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=logging_level.lower(),
        factory=True,
    )
