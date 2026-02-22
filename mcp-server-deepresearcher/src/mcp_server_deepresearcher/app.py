import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP
from xyber_sdk.mcp_client import McpClient, get_mcp_client_config
from xyber_sdk.model_registry import SupportedModels, get_model

from mcp_server_deepresearcher.api_routers import routers as api_routers
from mcp_server_deepresearcher.db.database import Database
from mcp_server_deepresearcher.deepresearcher.config import (
    get_database_config,
    get_llm_config,
)
from mcp_server_deepresearcher.deepresearcher.state import ToolDescription
from mcp_server_deepresearcher.deepresearcher.utils import (
    construct_tools_description_yaml,
    filter_mcp_tools_for_deepresearcher,
    parse_tools_description_from_yaml,
)
from mcp_server_deepresearcher.dependencies import DependencyContainer
from mcp_server_deepresearcher.hybrid_routers import routers as hybrid_routers
from mcp_server_deepresearcher.logging_config import configure_logging
from mcp_server_deepresearcher.middlewares import X402WrapperMiddleware
from mcp_server_deepresearcher.x402_integration import get_x402_settings

logger = logging.getLogger(__name__)


configure_logging()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Application lifespan - initializes LLMs, MCP client, and dependencies."""
    logger.info("Lifespan: Initializing application services...")

    try:
        # --- Initialize LLMs ---
        llm_config = get_llm_config()

        main_model = SupportedModels[llm_config.llm_main]
        llm = get_model(main_model)
        logger.info(f"Main LLM initialized: {llm_config.llm_main}")

        # Add spare LLM as fallback if configured
        if llm_config.llm_spare:
            spare_model = SupportedModels[llm_config.llm_spare]
            llm_spare = get_model(spare_model)
            llm = llm.with_fallbacks([llm_spare])
            logger.info(f"Spare LLM configured: {llm_config.llm_spare}")

        # Thinking LLM (falls back to main)
        if llm_config.llm_thinking:
            thinking_model = SupportedModels[llm_config.llm_thinking]
            llm_thinking = get_model(thinking_model)
            logger.info(f"Thinking LLM initialized: {llm_config.llm_thinking}")
        else:
            llm_thinking = llm
            logger.info("Thinking LLM: using main LLM")

        # --- Initialize MCP Client ---
        mcp_config = get_mcp_client_config()
        mcp_client = McpClient.from_config(mcp_config)

        if mcp_config.servers:
            logger.info(
                f"MCP client initialized with {len(mcp_config.servers)} server(s): {list(mcp_config.servers.keys())}"
            )
        else:
            logger.warning("No MCP servers configured. Set MCP_SERVERS env var.")

        # --- Build tools description ---
        mcp_tools = await mcp_client.get_all_tools()
        mcp_tools = filter_mcp_tools_for_deepresearcher(mcp_tools)

        tools_description_yaml = construct_tools_description_yaml(mcp_tools, {})
        tools_description_dicts = parse_tools_description_from_yaml(
            tools_description_yaml
        )
        tools_description = [ToolDescription(**d) for d in tools_description_dicts]

        logger.info(f"Tools description built: {len(tools_description)} tools")

        # --- Initialize Database (optional) ---
        db_config = get_database_config()
        database: Database | None = None
        if db_config.is_configured:
            try:
                database = Database(db_url=db_config.url)
                logger.info("Database initialized successfully.")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to database: {e}. Reports will not be persisted"
                )
        else:
            logger.info("Database not configured. Reports API will be unavailable.")

        # --- Create DependencyContainer ---
        DependencyContainer.create(
            llm=llm,
            llm_thinking=llm_thinking,
            mcp_client=mcp_client,
            tools_description=tools_description,
            database=database,
        )

        logger.info("Lifespan: Services initialized successfully.")
        yield

    except Exception as e:
        logger.error(f"FATAL: Error during lifespan initialization: {e}", exc_info=True)
        raise

    finally:
        logger.info("Lifespan: Shutting down...")
        DependencyContainer.clear()
        logger.info("Lifespan: Shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the main FastAPI application."""
    # --- MCP Server Generation ---
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)

    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="deep_researcher")
    mcp_app = mcp_server.http_app(path="/", stateless_http=True)

    # --- Combined Lifespan ---
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
    for router in api_routers:
        app.include_router(router, prefix="/api")

    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    app.mount("/mcp", mcp_app)

    # --- x402 Middleware ---
    x402_settings = get_x402_settings()
    x402_settings.validate_pricing_mode()

    all_routes = app.routes + mcp_source_app.routes
    x402_settings.validate_against_routes(all_routes)

    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled.")

    logger.info("Application setup complete.")
    return app


def get_mcp_server() -> FastMCP:
    """Get the MCP server instance for testing purposes."""
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)

    return FastMCP.from_fastapi(app=mcp_source_app, name="deep_researcher")
