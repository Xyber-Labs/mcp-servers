"""
This module will usually change as you add, remove, or reorder MCP-only routers used as tools for AI agents.

Main responsibility: Collect MCP-only FastAPI routers into a single list for inclusion in the MCP source application.
"""

from fastapi import APIRouter

# Import MCP-only routers here when you create them
# from .example_mcp_tool import router as example_mcp_tool_router

routers: list[APIRouter] = [
    # Add MCP-only routers here
    # example_mcp_tool_router,
]

