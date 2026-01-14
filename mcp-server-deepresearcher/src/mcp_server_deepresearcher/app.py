"""
Main FastAPI application factory with REST API, MCP, and x402 payment support.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from mcp_server_deepresearcher.api_routers import routers as api_routers
from mcp_server_deepresearcher.deepresearcher.config import LLM_Config, SearchMCP_Config
from mcp_server_deepresearcher.deepresearcher.utils import (
    construct_tools_description_yaml,
    load_mcp_servers_config,
    parse_tools_description_from_yaml,
    setup_llm,
    setup_spare_llm,
    initialize_llm,
)
from mcp_server_deepresearcher.deepresearcher.state import ToolDescription
from mcp_server_deepresearcher.hybrid_routers import routers as hybrid_routers
from mcp_server_deepresearcher.mcp_routers import routers as mcp_routers
from mcp_server_deepresearcher.logging_config import configure_logging
from mcp_server_deepresearcher.middlewares import X402WrapperMiddleware
from mcp_server_deepresearcher.x402_config import get_x402_settings
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


# Apply logging configuration when the app module is loaded
configure_logging()


# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.
    
    Currently manages:
    - LLMs (main, thinking, spare)
    - MCP tools and client
    - Tools description
    
    Note: The x402 middleware manages its own HTTP client lifecycle using
    context managers, so no external resource management is needed.
    """
    logger.info("Lifespan: Initializing application services...")

    try:
        # Load configurations
        llm_config = LLM_Config()
        search_mcp_config = SearchMCP_Config()

        # Initialize LLMs
        llm = setup_llm(llm_config)
        llm_spare = setup_spare_llm(llm_config)
        llm_with_fallbacks = llm.with_fallbacks([llm_spare])
        
        # Initialize thinking LLM
        llm_thinking = initialize_llm(llm_type="thinking", raise_on_error=False)
        if not llm_thinking:
            llm_thinking = llm_with_fallbacks
        elif llm_spare:
            llm_thinking = llm_thinking.with_fallbacks([llm_spare])
        
        logger.info("LLMs initialized successfully.")

        # Initialize MCP client to fetch tools for the agent
        mcp_servers_config = load_mcp_servers_config(
            apify_token=search_mcp_config.APIFY_TOKEN,
            mcp_tavily_url=search_mcp_config.MCP_TAVILY_URL,
            mcp_arxiv_url=search_mcp_config.MCP_ARXIV_URL,
            mcp_twitter_url=search_mcp_config.MCP_TWITTER_APIFY_URL,
            mcp_youtube_url=search_mcp_config.MCP_YOUTUBE_APIFY_URL,
            mcp_telegram_parser_url=search_mcp_config.MCP_TELEGRAM_PARSER_URL,
        )

        client = MultiServerMCPClient(mcp_servers_config)

        logger.info("Connecting to dependent MCPs to fetch tools...")
        try:
            # Add timeout to prevent hanging if MCP servers are not available
            mcp_tools = await asyncio.wait_for(
                client.get_tools(),
                timeout=30.0  # 30 second timeout per server
            )
            logger.info(
                f"Successfully fetched {len(mcp_tools)} tools for the agent to use."
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout connecting to MCP servers. Continuing with empty tools list. "
                "Some features may not be available."
            )
            mcp_tools = []
        except Exception as e:
            logger.error(
                f"Error connecting to MCP servers: {e}. Continuing with empty tools list. "
                "Some features may not be available.",
                exc_info=True
            )
            mcp_tools = []
        
        # Construct tools_description from mcp_tools
        tools_description_yaml = construct_tools_description_yaml(mcp_tools)
        tools_description_dicts = parse_tools_description_from_yaml(tools_description_yaml)
        tools_description_objects = [ToolDescription(**tool_dict) for tool_dict in tools_description_dicts]

        # Store resources in app state
        app.state.llm = llm_with_fallbacks
        app.state.llm_thinking = llm_thinking
        app.state.mcp_tools = mcp_tools
        app.state.tools_description = tools_description_objects

        logger.info("Lifespan: Services initialized successfully.")
        yield
        
    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        raise startup_err
    
    finally:
        logger.info("Lifespan: Shutting down application services...")
        logger.info("Lifespan: Services shut down gracefully.")


# --- Application Factory ---
def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates an MCP server from hybrid routers
    2. Combines lifespans for proper resource management
    3. Configures API routes with appropriate prefixes
    4. Sets up x402 payment middleware
    5. Validates pricing configuration against available routes

    Returns:
        Configured FastAPI application ready to serve requests
    """
    # --- MCP Server Generation ---
    # Create a FastAPI app containing only MCP-exposed endpoints
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)
    
    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="deep_researcher")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Deep Researcher MCP Server (Hybrid)",
        description="A server with REST, MCP, and x402 payment capabilities.",
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes: accessible via /hybrid/* (REST) and /mcp (MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # MCP-only routes: NOT mounted as REST endpoints
    # They're only accessible through the /mcp endpoint below

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # This validates that all priced endpoints actually exist
    # and warns about any misconfiguration
    all_routes = app.routes + mcp_source_app.routes
    x402_settings = get_x402_settings()
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---    
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app

