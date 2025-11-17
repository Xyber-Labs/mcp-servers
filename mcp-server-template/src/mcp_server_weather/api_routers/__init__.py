"""
REST-only router aggregation.

This module will usually change as you add, remove, or reorder REST-only routers
for your own API, but the pattern of collecting them into a single ``routers``
list for inclusion in the main app should stay the same.
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .health import router as health_router

routers: list[APIRouter] = [
    health_router,
    admin_router,
]
