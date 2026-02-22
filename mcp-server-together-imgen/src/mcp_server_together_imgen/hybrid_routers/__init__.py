"""
Hybrid routers (accessible via both /hybrid/* REST endpoints and /mcp MCP endpoints).

Main responsibility: Collect hybrid (REST + MCP) FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .image_generation import router as image_router
from .pricing import router as pricing_router

routers: list[APIRouter] = [
    image_router,
    pricing_router,
]
