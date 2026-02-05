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
    filter_mcp_tools_for_deepresearcher,
    load_mcp_servers_config,
    parse_tools_description_from_yaml,
    setup_llm,
    setup_spare_llm,
    initialize_llm,
)
from mcp_server_deepresearcher.deepresearcher.state import ToolDescription
from mcp_server_deepresearcher.hybrid_routers import routers as hybrid_routers
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
        llm = setup_llm()
        llm_spare = setup_spare_llm()
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

        logger.info("Connecting to dependent MCPs to fetch tools...")
        mcp_tools = []
        failed_servers = []
        successful_servers = []
        mcp_connection_errors = []
        
        # Connect to each MCP server individually for better error handling
        # This allows us to collect tools from servers that succeed even if others fail
        for server_name, server_config in mcp_servers_config.items():
            try:
                url = server_config.get('url', 'No URL')
                logger.info(f"Connecting to {server_name} MCP server at {url}...")
                
                # Create a single-server client for this server
                single_server_config = {server_name: server_config}
                single_client = MultiServerMCPClient(single_server_config)
                
                # Try to get tools from this specific server with timeout
                server_tools = await asyncio.wait_for(
                    single_client.get_tools(),
                    timeout=30.0  # 30 second timeout per server
                )
                
                if server_tools:
                    # Optionally filter tools immediately (helps avoid duplicate capabilities like YouTube).
                    # This also ensures per-server log messages reflect what the agent will actually see.
                    before_server_count = len(server_tools)
                    server_tools = filter_mcp_tools_for_deepresearcher(server_tools)
                    removed_server = before_server_count - len(server_tools)

                    mcp_tools.extend(server_tools)
                    successful_servers.append(server_name)
                    logger.info(
                        f"✓ Successfully connected to {server_name} and fetched {before_server_count} tools"
                        + (f" ({removed_server} filtered, {len(server_tools)} kept)" if removed_server else "")
                    )
                else:
                    successful_servers.append(server_name)
                    logger.warning(f"✓ Connected to {server_name} but no tools returned")
                    
            except asyncio.TimeoutError:
                error_msg = f"Timeout connecting to {server_name} MCP server after 30 seconds"
                logger.error(f"✗ {error_msg}")
                failed_servers.append(server_name)
                mcp_connection_errors.append(f"{server_name}: {error_msg}")
                continue
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                # Extract more details from exception groups if available
                if hasattr(e, '__cause__') and e.__cause__:
                    error_msg = f"{error_msg} (caused by: {str(e.__cause__)})"
                
                # Extract underlying connection error if available
                if hasattr(e, 'exceptions') and e.exceptions:
                    # ExceptionGroup - extract first exception details
                    first_exc = e.exceptions[0] if e.exceptions else None
                    if first_exc:
                        if hasattr(first_exc, '__cause__') and first_exc.__cause__:
                            underlying_error = str(first_exc.__cause__)
                            if "ConnectError" in underlying_error or "TLS" in underlying_error:
                                error_msg = f"Connection failed: {underlying_error}"
                
                full_error_msg = f"{server_name}: {error_type} - {error_msg}"
                logger.error(f"✗ Failed to connect to {server_name}: {full_error_msg}", exc_info=False)
                failed_servers.append(server_name)
                mcp_connection_errors.append(full_error_msg)
                continue
        
        # Log summary
        if successful_servers:
            logger.info(
                f"Successfully connected to {len(successful_servers)} MCP server(s): {', '.join(successful_servers)}"
            )
            logger.info(f"Total tools fetched: {len(mcp_tools)}")
        
        if failed_servers:
            logger.warning(
                f"Failed to connect to {len(failed_servers)} MCP server(s): {', '.join(failed_servers)}"
            )
            mcp_connection_error = (
                f"Failed to connect to {len(failed_servers)} MCP server(s): {', '.join(failed_servers)}. "
                f"Errors: {'; '.join(mcp_connection_errors)}. "
                f"Research functionality may be limited. "
                f"Please verify that MCP server URLs are correct and servers are running."
            )
        else:
            mcp_connection_error = None
        
        # Only fail completely if no tools were fetched at all
        if not mcp_tools:
            error_summary = (
                "No MCP tools available. All MCP servers failed to connect. "
                "Research functionality requires at least one MCP server to be available. "
            )
            if mcp_connection_errors:
                error_summary += f"Connection errors: {'; '.join(mcp_connection_errors)}"
            logger.error(error_summary)
            if not mcp_connection_error:
                mcp_connection_error = error_summary

        # Reduce duplicate/overlapping tools (notably YouTube) to simplify agent tool selection.
        before_count = len(mcp_tools)
        mcp_tools = filter_mcp_tools_for_deepresearcher(mcp_tools)
        removed = before_count - len(mcp_tools)
        if removed > 0:
            logger.info(f"Filtered MCP tools for agent: removed {removed} tool(s), now {len(mcp_tools)} total.")
        
        # Construct tools_description from mcp_tools
        tools_description_yaml = construct_tools_description_yaml(mcp_tools)
        tools_description_dicts = parse_tools_description_from_yaml(tools_description_yaml)
        tools_description_objects = [ToolDescription(**tool_dict) for tool_dict in tools_description_dicts]

        # Store resources in app state
        app.state.llm = llm_with_fallbacks
        app.state.llm_thinking = llm_thinking
        app.state.mcp_tools = mcp_tools
        app.state.tools_description = tools_description_objects
        app.state.mcp_connection_error = mcp_connection_error  # Store error for better error messages

        if mcp_connection_error:
            logger.warning(
                "MCP tools unavailable. Research requests will fail until MCP servers are connected."
            )
        else:
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
    
    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="deep_researcher")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app) as _:
            # Share app state with mcp_source_app so hybrid routers can access resources
            # FastMCP makes internal HTTP calls to mcp_source_app, so it needs the same state
            mcp_source_app.state.llm = app.state.llm
            mcp_source_app.state.llm_thinking = app.state.llm_thinking
            mcp_source_app.state.mcp_tools = app.state.mcp_tools
            mcp_source_app.state.tools_description = app.state.tools_description
            mcp_source_app.state.mcp_connection_error = getattr(app.state, "mcp_connection_error", None)
            
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

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # First, validate that pricing_mode is consistent with pricing config
    # This will fail fast if pricing_mode='on' but no config exists
    x402_settings = get_x402_settings()
    x402_settings.validate_pricing_mode()

    # Then validate that all priced endpoints actually exist
    all_routes = app.routes + mcp_source_app.routes
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app


def get_mcp_server() -> FastMCP:
    """
    Get the MCP server instance for testing purposes.

    This creates a standalone MCP server without the full FastAPI app.
    """
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)

    return FastMCP.from_fastapi(app=mcp_source_app, name="deep_researcher")
