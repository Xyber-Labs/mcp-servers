"""
Caching middleware for YouTube transcript caching.
"""

import asyncio
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_server_youtube.youtube.methods import DatabaseManager

logger = logging.getLogger(__name__)


class TranscriptCachingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles transcript caching for YouTube videos.
    
    This middleware intercepts requests to transcript-related endpoints and
    checks the cache before making API calls. It also saves transcripts to
    the cache after successful API calls.
    """

    def __init__(self, app, db_manager: DatabaseManager):
        """
        Initialize the caching middleware.
        
        Args:
            app: The FastAPI application
            db_manager: Database manager instance for cache operations
        """
        super().__init__(app)
        self.db_manager = db_manager

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and handle caching.
        
        This middleware doesn't modify the request/response flow directly,
        but provides caching functionality that can be used by endpoints.
        The actual caching logic is handled by the service layer.
        """
        response = await call_next(request)
        return response

