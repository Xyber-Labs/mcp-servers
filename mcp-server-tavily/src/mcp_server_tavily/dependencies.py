from fastapi import Request

from mcp_server_tavily.tavily import _TavilyService
from mcp_server_tavily.tavily import get_tavily_service as _get_tavily_service


def get_tavily_client(request: Request) -> _TavilyService:
    return _get_tavily_service()

