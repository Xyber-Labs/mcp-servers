"""
This module will usually change as you add, remove, or reorder MCP-only routers used as tools for AI agents.

Main responsibility: Collect MCP-only FastAPI routers into a single list for inclusion in the MCP source application.
"""

from fastapi import APIRouter

from .analysis import router as analysis_router
from .geolocation import router as geolocation_router

routers: list[APIRouter] = [
    geolocation_router,
    analysis_router,
]
