"""
API routers - REST-only endpoints.
"""

from fastapi import APIRouter

from .health import router as health_router
from .youtube import router as youtube_router

routers: list[APIRouter] = [
    health_router,
    youtube_router,
]

