"""
FastAPI dependencies for accessing shared resources from app state.
"""

from typing import Any

from fastapi import Request


def get_research_resources(request: Request) -> dict[str, Any]:
    """
    Dependency function to get research resources from FastAPI app state.
    """
    app_state = request.app.state
    return {
        "llm": getattr(app_state, "llm", None),
        "llm_thinking": getattr(app_state, "llm_thinking", None),
        "mcp_tools": getattr(app_state, "mcp_tools", []),
        "tools_description": getattr(app_state, "tools_description", []),
    }

