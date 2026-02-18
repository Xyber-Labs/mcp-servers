"""
Hybrid endpoint (REST + MCP) for performing deep research on topics.
"""

import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.runnables import RunnableConfig

from mcp_server_deepresearcher.deepresearcher.config import (
    get_langfuse_config,
    get_researcher_config,
)
from mcp_server_deepresearcher.deepresearcher.graph import DeepResearcher
from mcp_server_deepresearcher.deepresearcher.utils import filter_mcp_tools_for_deepresearcher
from mcp_server_deepresearcher.dependencies import DependencyContainer, get_database, get_research_resources
from mcp_server_deepresearcher.schemas import DeepResearchRequest

# Langfuse
# Configure OpenTelemetry BEFORE importing Langfuse to handle errors gracefully
# Set OpenTelemetry timeout environment variables to fail fast if Langfuse is not available
os.environ.setdefault(
    "OTEL_EXPORTER_OTLP_TIMEOUT", "5"
)  # Reduced timeout for faster failure
os.environ.setdefault("OTEL_BSP_EXPORT_TIMEOUT", "5000")  # 5 seconds in milliseconds
os.environ.setdefault("OTEL_BSP_SCHEDULE_DELAY", "5000")  # Delay between batch exports

# Suppress OpenTelemetry SDK error logging to prevent spam when Langfuse is not running
# Set log level to CRITICAL to suppress all OpenTelemetry SDK errors
otel_logger = logging.getLogger("opentelemetry")
otel_logger.setLevel(logging.CRITICAL)
# Suppress urllib3 connection errors from OpenTelemetry
urllib3_logger = logging.getLogger("urllib3.connectionpool")
urllib3_logger.setLevel(logging.CRITICAL)
# Suppress requests errors from OpenTelemetry
requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.CRITICAL)

from langfuse.langchain import CallbackHandler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/deep-research",
    tags=["Research"],
    operation_id="deep_research",
    response_model=dict,
)
async def deep_research(
    research_request: DeepResearchRequest,
    resources: dict = Depends(get_research_resources),
) -> dict:
    """
    Performs deep research on a topic and returns a structured report.

    This endpoint is available to both REST API consumers and AI agents via MCP.
    It conducts comprehensive research using multiple MCP tools and returns
    a detailed report with sources.
    """
    logger.info(
        f"Received request for deep_research on topic: '{research_request.research_topic}'"
    )

    llm = resources.get("llm")
    llm_thinking = resources.get("llm_thinking")
    tools_description = resources.get("tools_description", [])

    # Check for required resources
    if not llm:
        raise HTTPException(
            status_code=503,
            detail="LLM not available. The server may have failed to initialize properly.",
        )

    # Fetch MCP tools on-demand from client
    mcp_tools = await DependencyContainer.get_mcp_tools()
    mcp_tools = filter_mcp_tools_for_deepresearcher(mcp_tools)

    if not mcp_tools:
        raise HTTPException(
            status_code=503,
            detail="No MCP tools available. Check MCP_SERVERS configuration.",
        )

    if not llm_thinking:
        llm_thinking = llm

    return await perform_deep_research(
        request=research_request,
        llm=llm,
        llm_thinking=llm_thinking,
        mcp_tools=mcp_tools,
        tools_description=tools_description,
        database=get_database(),
    )


async def perform_deep_research(
    request: DeepResearchRequest,
    llm: Any,
    llm_thinking: Any,
    mcp_tools: list[Any],
    tools_description: list[Any],
    database: Any | None = None,
) -> dict[str, Any]:
    """
    Core research logic.
    """
    # Get configuration for deep researcher
    researcher_config = get_researcher_config()

    # Create a new, stateless agent for each request
    agent = DeepResearcher(
        LLM=llm,
        LLM_THINKING=llm_thinking,
        tools=mcp_tools,
        research_topic=request.research_topic,
        research_loop_max=researcher_config.max_web_research_loops,
        tools_description=tools_description,
        database=database,
    )
    logger.info("Created new stateless agent for this request.")

    # Create Langfuse handler for this run
    langfuse_handler = None
    runnable_config = None

    # Generate unique IDs for this run
    run_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Get Langfuse configuration
    langfuse_config = get_langfuse_config()

    # Check if Langfuse is configured
    logger.debug(
        f"Langfuse config check - API_KEY: {bool(langfuse_config.api_key)}, SECRET_KEY: {bool(langfuse_config.secret_key)}, HOST: {langfuse_config.host}"
    )

    if langfuse_config.is_configured:
        try:
            logger.info("Initializing Langfuse tracking...")

            os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_config.api_key
            os.environ["LANGFUSE_SECRET_KEY"] = langfuse_config.secret_key
            if langfuse_config.host:
                os.environ["LANGFUSE_HOST"] = langfuse_config.host

            logger.info(
                f"Langfuse env vars set - PUBLIC_KEY: {langfuse_config.api_key[:10]}..., HOST: {langfuse_config.host}"
            )

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
                    "max_web_research_loops": researcher_config.max_web_research_loops,
                },
            }

            logger.info(f"Created Langfuse handler for research run {run_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to create Langfuse handler for this run: {e}")
            logger.exception(e)
            # Ensure runnable_config is None if creation failed
            runnable_config = None
            langfuse_handler = None
    else:
        logger.warning("Langfuse not configured - missing API_KEY or SECRET_KEY")

    try:
        # Build config with configurable parameters
        configurable_params = {
            "max_web_research_loops": researcher_config.max_web_research_loops
        }

        # If runnable_config exists, merge configurable parameters with it
        # Note: RunnableConfig is a TypedDict, so we can't use dot notation or isinstance()
        if runnable_config:
            # Create a new RunnableConfig that includes both callbacks and configurable params
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
                trace_id = None
                if hasattr(langfuse_handler, "trace_id"):
                    trace_id = langfuse_handler.trace_id
                    logger.info(f"Langfuse trace ID for this research run: {trace_id}")
                elif hasattr(langfuse_handler, "get_trace_id"):
                    trace_id = langfuse_handler.get_trace_id()
                    logger.info(f"Langfuse trace ID: {trace_id}")
                else:
                    logger.info(
                        "Langfuse handler created, trace will be available in Langfuse UI"
                    )

                if hasattr(langfuse_handler, "flush"):
                    langfuse_handler.flush()
                    logger.info("Langfuse handler flushed - data sent to Langfuse")
                elif hasattr(langfuse_handler, "shutdown"):
                    langfuse_handler.shutdown()
                    logger.info("Langfuse handler shut down - data sent to Langfuse")

                try:
                    from langfuse import get_client

                    client = get_client()
                    if client and hasattr(client, "flush"):
                        client.flush()
                        logger.info("Langfuse client flushed")
                except Exception as e:
                    logger.debug(f"Could not flush Langfuse client: {e}")

            except Exception as e:
                logger.warning(f"Could not retrieve trace ID or flush handler: {e}")
                logger.exception(e)

        # Extract data from result_dict (ResearchState)
        # The state uses 'summary' not 'running_summary'
        running_summary = result_dict.get("summary") or result_dict.get(
            "running_summary"
        )
        report_data = result_dict.get("report")

        # Convert summary to dict format if it's a string
        if isinstance(running_summary, str):
            final_report = {"content": running_summary}
        elif isinstance(running_summary, dict):
            final_report = running_summary
        else:
            final_report = {}

        logger.info("Successfully completed deep research.")
        logger.debug(f"Result keys: {result_dict.keys()}")
        logger.debug(f"Report data type: {type(report_data)}, value: {report_data}")
        logger.debug(
            f"Summary type: {type(running_summary)}, value: {running_summary[:100] if isinstance(running_summary, str) else running_summary}"
        )

        # Return comprehensive result
        return {
            "status": "success",
            "research_topic": request.research_topic,
            "running_summary": final_report,
            "report": report_data,
            "research_loop_count": result_dict.get("research_loop_count", 0),
        }

    except Exception as e:
        logger.error(
            f"An unexpected error occurred during deep research: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred during research: {e}"
        ) from e
    finally:
        # Clean up handler reference
        langfuse_handler = None
        runnable_config = None
