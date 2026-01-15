import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.runnables import RunnableConfig
from mcp_server_deepresearcher.deepresearcher.config import LLM_Config, SearchMCP_Config, LangfuseConfig, DeepResearcherConfig
from mcp_server_deepresearcher.deepresearcher.graph import DeepResearcher
from mcp_server_deepresearcher.deepresearcher.utils import (
    load_mcp_servers_config,
    setup_llm,
    setup_spare_llm,
    initialize_llm,
    construct_tools_description_yaml,
    parse_tools_description_from_yaml,
)
from mcp_server_deepresearcher.deepresearcher.state import ToolDescription
from mcp_server_deepresearcher.schemas import DeepResearchRequest

# Langfuse 
# Set OpenTelemetry timeout environment variables BEFORE importing Langfuse
# This ensures they're applied before OpenTelemetry initializes
os.environ.setdefault("OTEL_EXPORTER_OTLP_TIMEOUT", "30")
os.environ.setdefault("OTEL_BSP_EXPORT_TIMEOUT", "30000")  # 30 seconds in milliseconds
os.environ.setdefault("OTEL_BSP_SCHEDULE_DELAY", "5000")  # Delay between batch exports

from langfuse.langchain import CallbackHandler

logger = logging.getLogger(__name__)


# --- Lifespan Management --- #
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """
    Manage server startup/shutdown.
    Initializes shared resources like LLMs and MCP tools once at startup.
    """
    logger.info("Lifespan: Initializing shared resources...")

    try:
        # Load configurations
        llm_config = LLM_Config()
        search_mcp_config = SearchMCP_Config()
        deep_researcher_config = DeepResearcherConfig()
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
        mcp_tools = await client.get_tools()
        logger.info(
            f"Successfully fetched {len(mcp_tools)} tools for the agent to use."
        )
        
        # Construct tools_description from mcp_tools
        tools_description_yaml = construct_tools_description_yaml(mcp_tools)
        tools_description_dicts = parse_tools_description_from_yaml(tools_description_yaml)
        tools_description_objects = [ToolDescription(**tool_dict) for tool_dict in tools_description_dicts]

        # Yield shared resources to the server context
        yield {
            "llm": llm_with_fallbacks,
            "llm_thinking": llm_thinking,
            "mcp_tools": mcp_tools,
            "tools_description": tools_description_objects,
        }

    except Exception as startup_err:
        logger.error(
            f"FATAL: Unexpected error during lifespan initialization: {startup_err}",
            exc_info=True,
        )
        # Re-raise the error to prevent the server from starting in a bad state
        raise startup_err

    finally:
        logger.info("Lifespan: Shutdown cleanup completed.")


# --- MCP Server Initialization --- #
mcp_server = FastMCP(name="deep_researcher", lifespan=app_lifespan)


# --- Tool Definitions --- #
@mcp_server.tool()
async def deep_research(
    ctx: Context, request: DeepResearchRequest
) -> str:
    """Performs deep research on a topic and returns a structured report."""
    logger.info(f"Received request for deep_research on topic: '{request.research_topic}'")

    # Retrieve shared resources from lifespan context
    lifespan_ctx = ctx.request_context.lifespan_context
    llm = lifespan_ctx.get("llm")
    llm_thinking = lifespan_ctx.get("llm_thinking")
    mcp_tools = lifespan_ctx.get("mcp_tools")
    tools_description = lifespan_ctx.get("tools_description", [])

    if not llm or not mcp_tools:
        raise ToolError(
            "Shared resources (LLM, tools) not available. The server may have failed to initialize properly."
        )
    
    if not llm_thinking:
        llm_thinking = llm

    # Get configuration for deep researcher
    deep_researcher_config = DeepResearcherConfig()

    # Create a new, stateless agent for each request
    agent = DeepResearcher(
        LLM=llm,
        LLM_THINKING=llm_thinking,
        tools=mcp_tools,
        research_topic=request.research_topic,
        research_loop_max=deep_researcher_config.MAX_WEB_RESEARCH_LOOPS,
        tools_description=tools_description,
    )
    logger.info("Created new stateless agent for this request.")

    # Create Langfuse handler for this run
    # CRITICAL: Following Langfuse best practices - create a NEW CallbackHandler() 
    # for each graph invocation to ensure separate traces
    # See: https://langfuse.com/docs/sdk/python/langchain
    langfuse_handler = None
    runnable_config = None
    
    # Generate unique IDs for this run
    run_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Get Langfuse configuration
    langfuse_config = LangfuseConfig()
    
    # Check if Langfuse is configured (v3 doesn't require project, but we check for API key)
    logger.debug(f"Langfuse config check - API_KEY: {bool(langfuse_config.LANGFUSE_API_KEY)}, SECRET_KEY: {bool(langfuse_config.LANGFUSE_SECRET_KEY)}, HOST: {langfuse_config.LANGFUSE_HOST}")
    
    if langfuse_config.LANGFUSE_API_KEY and langfuse_config.LANGFUSE_SECRET_KEY:
        try:
            logger.info("Initializing Langfuse tracking...")
            
            # Create a NEW CallbackHandler instance - each handler automatically generates a new trace ID
            # Note: Langfuse v3 - CallbackHandler() reads all config from environment variables
            # Set environment variables for Langfuse configuration (v3 uses LANGFUSE_PUBLIC_KEY)
            os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_config.LANGFUSE_API_KEY
            os.environ["LANGFUSE_SECRET_KEY"] = langfuse_config.LANGFUSE_SECRET_KEY
            if langfuse_config.LANGFUSE_HOST:
                os.environ["LANGFUSE_HOST"] = langfuse_config.LANGFUSE_HOST
            
            logger.info(f"Langfuse env vars set - PUBLIC_KEY: {langfuse_config.LANGFUSE_API_KEY[:10]}..., HOST: {langfuse_config.LANGFUSE_HOST}")
            
            # CallbackHandler reads all config from environment variables (no arguments needed in v3)
            # Note: Project parameter was removed in v3 - projects are managed at account level in UI
            langfuse_handler = CallbackHandler()
            logger.info("Langfuse CallbackHandler created successfully")
            
            runnable_config: RunnableConfig = {
                "callbacks": [langfuse_handler],
            "metadata": {
                "agent_type": "deep_researcher",
                "agent_name": "DeepResearcher",
                "session_id": session_id,
                "run_id": run_id,
                "research_topic": request.research_topic,
                "max_web_research_loops": deep_researcher_config.MAX_WEB_RESEARCH_LOOPS,
            }
            }
            
            logger.info(f"Created Langfuse handler for research run {run_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to create Langfuse handler for this run: {e}")
            logger.exception(e)
    else:
        logger.warning("Langfuse not configured - missing API_KEY or SECRET_KEY")

    try:
        # Build config with configurable parameters
        configurable_params = {"max_web_research_loops": deep_researcher_config.MAX_WEB_RESEARCH_LOOPS}
        
        # If runnable_config exists, merge configurable parameters with it
        if runnable_config:
            # Create a new RunnableConfig that includes both callbacks and configurable params
            # Note: RunnableConfig is a TypedDict, so we use dictionary access
            config: RunnableConfig = {
                "callbacks": runnable_config.get("callbacks"),
                "configurable": configurable_params,
                "metadata": runnable_config.get("metadata"),
            }
            logger.info("Starting graph execution...")
            logger.info("Executing graph with Langfuse tracking enabled")
        else:
            # No Langfuse, just use configurable parameters
            config = {"configurable": configurable_params}
            logger.info("Starting graph execution...")
            logger.info("Executing graph without Langfuse tracking")
        
        result_dict = await agent.graph.ainvoke(
            {"research_topic": request.research_topic}, config=config
        )
        
        # Log trace ID and flush Langfuse data (if handler was created)
        if langfuse_handler:
            try:
                # Try to get trace ID from handler
                trace_id = None
                if hasattr(langfuse_handler, 'trace_id'):
                    trace_id = langfuse_handler.trace_id
                    logger.info(f"Langfuse trace ID for this research run: {trace_id}")
                elif hasattr(langfuse_handler, 'get_trace_id'):
                    trace_id = langfuse_handler.get_trace_id()
                    logger.info(f"Langfuse trace ID: {trace_id}")
                else:
                    logger.info("Langfuse handler created, trace will be available in Langfuse UI")
                
                # Flush the handler to ensure data is sent to Langfuse
                # Langfuse v3 uses async batching, so we need to flush explicitly
                if hasattr(langfuse_handler, 'flush'):
                    langfuse_handler.flush()
                    logger.info("Langfuse handler flushed - data sent to Langfuse")
                elif hasattr(langfuse_handler, 'shutdown'):
                    langfuse_handler.shutdown()
                    logger.info("Langfuse handler shut down - data sent to Langfuse")
                
                # Also try to flush via the Langfuse client if available
                try:
                    from langfuse import get_client
                    client = get_client()
                    if client and hasattr(client, 'flush'):
                        client.flush()
                        logger.info("Langfuse client flushed")
                except Exception as e:
                    logger.debug(f"Could not flush Langfuse client: {e}")
                    
            except Exception as e:
                logger.warning(f"Could not retrieve trace ID or flush handler: {e}")
                logger.exception(e)

        final_report = json.dumps(result_dict.get("running_summary", {}), indent=2)
        logger.info("Successfully completed deep research.")
        return final_report

    except Exception as e:
        logger.error(
            f"An unexpected error occurred during deep research: {e}", exc_info=True
        )
        raise ToolError(f"An unexpected error occurred during research: {e}") from e
    finally:
        # Clean up handler reference
        # This ensures next iteration gets a completely fresh handler
        langfuse_handler = None
        runnable_config = None
