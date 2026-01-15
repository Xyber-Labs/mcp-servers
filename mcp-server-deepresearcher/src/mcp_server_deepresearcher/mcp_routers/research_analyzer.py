"""
MCP-only endpoint for performing deep research on topics.

This module provides an MCP-only version of the deep research functionality,
designed specifically for AI agents via the MCP protocol. It is not exposed
as a REST endpoint because it's optimized for LLM reasoning and decision-making.

Main responsibility: Provide MCP-only deep research tool for AI agents, protected by x402 pricing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from mcp_server_deepresearcher.dependencies import get_research_resources
from mcp_server_deepresearcher.hybrid_routers.deep_research import perform_deep_research
from mcp_server_deepresearcher.schemas import DeepResearchRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/deep-research",
    tags=["Research"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `x402_config.py` to identify this
    # specific tool for payment. It must be unique across all endpoints.
    operation_id="deep_research_mcp",
    response_model=dict,
)
async def deep_research_mcp(
    research_request: DeepResearchRequest,
    resources: dict = Depends(get_research_resources),
) -> dict:
    """
    Performs deep research on a topic and returns a structured report.

    This MCP-only endpoint conducts comprehensive research using multiple MCP tools
    and returns a detailed report with sources. It is designed specifically for
    AI agents via the MCP protocol and is not exposed as a REST endpoint.

    This premium tool requires x402 payment and is optimized for LLM reasoning
    and decision-making during research workflows.
    
    Args:
        research_request: The research request containing the topic to investigate
    """
    logger.info(f"Received MCP-only request for deep_research on topic: '{research_request.research_topic}'")

    llm = resources.get("llm")
    llm_thinking = resources.get("llm_thinking")
    mcp_tools = resources.get("mcp_tools", [])
    tools_description = resources.get("tools_description", [])
    mcp_connection_error = resources.get("mcp_connection_error")

    # Check for required resources with detailed error messages
    if not llm:
        raise HTTPException(
            status_code=503,
            detail="LLM not available. The server may have failed to initialize properly. Please check server logs."
        )
    
    if not mcp_tools:
        error_detail = (
            "No MCP tools are available. "
            "Research functionality requires at least one MCP server to be connected. "
        )
        if mcp_connection_error:
            error_detail += f"Connection errors: {mcp_connection_error}"
        else:
            error_detail += "Please check that MCP servers are running and accessible."
        
        raise HTTPException(
            status_code=503,
            detail=error_detail
        )
    
    # Log warning if some servers failed but we have tools
    if mcp_connection_error and mcp_tools:
        logger.warning(
            f"Some MCP servers failed to connect, but proceeding with {len(mcp_tools)} available tools. "
            f"Failed servers: {mcp_connection_error}"
        )
    
    if not llm_thinking:
        llm_thinking = llm

    try:
        return await perform_deep_research(
            request=research_request,
            llm=llm,
            llm_thinking=llm_thinking,
            mcp_tools=mcp_tools,
            tools_description=tools_description,
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during deep research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

