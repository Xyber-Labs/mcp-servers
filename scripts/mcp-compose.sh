#!/bin/bash
# Helper script to run docker-compose commands for MCP servers
# Usage: ./mcp-compose.sh [docker-compose arguments]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose-dev.yml"

# Check if docker-compose-dev.yml exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: docker-compose-dev.yml not found at $COMPOSE_FILE"
    exit 1
fi

# Run docker-compose with the correct file path
docker-compose -f "$COMPOSE_FILE" "$@"

