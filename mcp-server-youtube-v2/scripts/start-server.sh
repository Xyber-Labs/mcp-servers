#!/bin/bash
# Start YouTube MCP Server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if PostgreSQL container is running
if ! docker ps | grep -q youtube-postgres-local; then
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start-db.sh"
    echo ""
fi

echo "Starting YouTube MCP Server..."
echo "Server will be available at: http://localhost:8002"
echo "API docs: http://localhost:8002/docs"
echo ""

# Start the server (using Python 3.12 to avoid compatibility issues with 3.14)
uv run --python 3.12 python -m mcp_server_youtube --port 8002

