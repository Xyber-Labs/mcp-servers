"""
API routers - REST-only endpoints.
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
    admin_router,
]

