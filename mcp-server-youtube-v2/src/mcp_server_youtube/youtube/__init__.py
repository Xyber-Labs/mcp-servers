"""
YouTube service module - provides client, database, and models.
"""

from mcp_server_youtube.youtube.client import (
    YouTubeVideoSearchAndTranscript,
    get_youtube_client,
)
from mcp_server_youtube.youtube.methods import DatabaseManager, get_db_manager
from mcp_server_youtube.youtube.models import Base, YouTubeVideo

__all__ = [
    "YouTubeVideoSearchAndTranscript",
    "get_youtube_client",
    "DatabaseManager",
    "get_db_manager",
    "YouTubeVideo",
    "Base",
]

