"""
FastAPI dependencies for accessing shared resources from app state.
"""

from typing import Any

from fastapi import Request


def get_research_resources(request: Request) -> dict[str, Any]:
    """
    Dependency function to get research resources from FastAPI app state.
    
    This function checks the current app's state first, and if resources are not
    available, it tries to access them from the main app (for MCP-only routers
    that are called via FastMCP's internal HTTP mechanism).
    """
    app_state = request.app.state
    
    # Try to get resources from current app state
    llm = getattr(app_state, "llm", None)
    llm_thinking = getattr(app_state, "llm_thinking", None)
    mcp_tools = getattr(app_state, "mcp_tools", [])
    tools_description = getattr(app_state, "tools_description", [])
    mcp_connection_error = getattr(app_state, "mcp_connection_error", None)
    
    # If resources are not available, try to get them from the main app
    # This handles the case where FastMCP calls mcp_source_app internally
    if not llm or not mcp_tools:
        # Try to access the main app through the request's app reference
        # The main app might be stored in the app's extra state or we can access it via the mounted app
        try:
            # Check if there's a reference to the main app
            main_app = getattr(request.app, "_main_app", None)
            if main_app:
                main_app_state = main_app.state
                if not llm:
                    llm = getattr(main_app_state, "llm", None)
                if not llm_thinking:
                    llm_thinking = getattr(main_app_state, "llm_thinking", None)
                if not mcp_tools:
                    mcp_tools = getattr(main_app_state, "mcp_tools", [])
                if not tools_description:
                    tools_description = getattr(main_app_state, "tools_description", [])
                if not mcp_connection_error:
                    mcp_connection_error = getattr(main_app_state, "mcp_connection_error", None)
        except Exception:
            # If we can't access the main app, just use what we have
            pass
    
    return {
        "llm": llm,
        "llm_thinking": llm_thinking,
        "mcp_tools": mcp_tools,
        "tools_description": tools_description,
        "mcp_connection_error": mcp_connection_error,
    }

