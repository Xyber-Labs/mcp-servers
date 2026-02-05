#!/bin/bash
# Start Gitparser MCP Server

set -e

echo "Starting Gitparser MCP Server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "MCP endpoint: http://localhost:8000/mcp/"
echo ""

# Use Python 3.12 for consistency with other MCP servers
uv run --python 3.12 python -m mcp_server_gitparser

