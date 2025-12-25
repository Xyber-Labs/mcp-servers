"""
MCP routers - available via MCP and also accessible via REST API.
"""

from fastapi import APIRouter

from .search import router as search_router
from .transcripts import router as transcripts_router

routers: list[APIRouter] = [
    search_router,
    transcripts_router,
]

