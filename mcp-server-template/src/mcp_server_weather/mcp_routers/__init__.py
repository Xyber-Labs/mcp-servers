"""
This module will mostly stay the same for all MCP servers
This module contains the FastAPI application factory and resource lifecycle management.
"""

from fastapi import APIRouter

from .analysis import router as analysis_router
from .geolocation import router as geolocation_router

routers: list[APIRouter] = [
    geolocation_router,
    analysis_router,
]
