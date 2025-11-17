"""
Hybrid (REST + MCP) router aggregation.

This module will usually change as you define which endpoints should be exposed
both as REST routes and as MCP tools, but the pattern of collecting them into a
single ``routers`` list for the main app will remain the same.
"""

from fastapi import APIRouter

from .current_weather import router as current_weather_router
from .forecast import router as forecast_router

routers: list[APIRouter] = [
    current_weather_router,
    forecast_router,
]
