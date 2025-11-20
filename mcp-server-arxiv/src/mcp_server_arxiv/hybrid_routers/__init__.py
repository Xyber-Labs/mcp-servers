from fastapi import APIRouter
from .search import router as search_router

routers: list[APIRouter] = [
    search_router
]

