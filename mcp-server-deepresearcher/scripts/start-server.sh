#!/bin/bash
# Start MCP Deep Researcher Server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if PostgreSQL container is running
if ! docker ps | grep -q mcp-deep-research-postgres-local; then
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start-db.sh"
    echo ""
fi

echo "Starting MCP Deep Researcher Server..."
echo "Server will be available at: http://localhost:8003"
echo "API docs: http://localhost:8003/docs"
echo ""

# Start the server (using Python 3.12 to avoid compatibility issues with 3.14)
uv run --python 3.12 python -m mcp_server_deepresearcher --port 8003

