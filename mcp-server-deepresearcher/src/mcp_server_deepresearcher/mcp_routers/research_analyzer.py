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
    request: DeepResearchRequest,
    resources: dict = Depends(get_research_resources),
) -> dict:
    """
    Performs deep research on a topic and returns a structured report.

    This MCP-only endpoint conducts comprehensive research using multiple MCP tools
    and returns a detailed report with sources. It is designed specifically for
    AI agents via the MCP protocol and is not exposed as a REST endpoint.

    This premium tool requires x402 payment and is optimized for LLM reasoning
    and decision-making during research workflows.
    """
    logger.info(f"Received MCP-only request for deep_research on topic: '{request.research_topic}'")

    llm = resources.get("llm")
    llm_thinking = resources.get("llm_thinking")
    mcp_tools = resources.get("mcp_tools")
    tools_description = resources.get("tools_description", [])

    if not llm or not mcp_tools:
        raise HTTPException(
            status_code=503,
            detail="Shared resources (LLM, tools) not available. The server may have failed to initialize properly."
        )
    
    if not llm_thinking:
        llm_thinking = llm

    return await perform_deep_research(
        request=request,
        llm=llm,
        llm_thinking=llm_thinking,
        mcp_tools=mcp_tools,
        tools_description=tools_description,
    )

