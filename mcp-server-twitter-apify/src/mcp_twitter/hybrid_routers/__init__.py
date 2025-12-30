"""
This module will usually change as you decide which endpoints should be exposed both as REST routes and as MCP tools for your server.

Main responsibility: Collect hybrid (REST + MCP) FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .search import router as search_router

routers: list[APIRouter] = [
    search_router,
]

