import uvicorn

from mcp_server_gitparser.config import get_app_settings
from mcp_server_gitparser.logging_config import get_logging_config


def main():
    """Entry point for the MCP Gitparser server."""
    settings = get_app_settings()

    uvicorn.run(
        "mcp_server_gitparser.app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
        reload=settings.hot_reload,
        log_config=get_logging_config(),
    )


if __name__ == "__main__":
    main()

