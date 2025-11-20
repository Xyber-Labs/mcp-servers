from fastapi import APIRouter
from .health import router as health_router

routers: list[APIRouter] = [
    health_router
]
