"""
This module will usually change as you decide which endpoints should be exposed both as REST routes and as MCP tools for your server.

Main responsibility: Collect hybrid (REST + MCP) FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .current_weather import router as current_weather_router
from .forecast import router as forecast_router

routers: list[APIRouter] = [
    current_weather_router,
    forecast_router,
]
