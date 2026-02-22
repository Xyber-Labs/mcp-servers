"""
API-only routers (accessible via /api/* endpoints only).

Main responsibility: Collect REST-only FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
]
