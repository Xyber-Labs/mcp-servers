"""
This module will usually change as you add, remove, or reorder REST-only routers for your own API, while keeping the aggregation pattern the same.

Main responsibility: Collect REST-only FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
    admin_router,
]
