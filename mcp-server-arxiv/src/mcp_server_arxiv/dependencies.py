from fastapi import Request

from mcp_server_arxiv.xy_arxiv import _ArxivService
from mcp_server_arxiv.xy_arxiv import get_arxiv_service as _get_arxiv_service


def get_arxiv_client(request: Request) -> _ArxivService:
    return _get_arxiv_service()

