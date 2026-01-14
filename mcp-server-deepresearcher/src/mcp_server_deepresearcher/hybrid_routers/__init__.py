"""
Collect hybrid (REST + MCP) FastAPI routers into a single list.
"""

from fastapi import APIRouter

from .deep_research import router as deep_research_router

routers: list[APIRouter] = [
    deep_research_router,
]

