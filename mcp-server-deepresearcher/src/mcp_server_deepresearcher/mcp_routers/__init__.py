"""
This module will usually change as you add, remove, or reorder MCP-only routers used as tools for AI agents.

Main responsibility: Collect MCP-only FastAPI routers into a single list for inclusion in the MCP source application.
"""

from fastapi import APIRouter

from .research_analyzer import router as research_analyzer_router

routers: list[APIRouter] = [
    research_analyzer_router,
]

