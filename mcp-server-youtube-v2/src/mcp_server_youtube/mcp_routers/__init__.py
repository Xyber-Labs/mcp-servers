"""
MCP-only routers - available only via MCP.
"""

from fastapi import APIRouter

from .transcripts import router as transcripts_router

routers: list[APIRouter] = [
    transcripts_router,
]

