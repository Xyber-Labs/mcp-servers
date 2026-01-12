#!/bin/bash
# Start all MCP servers using docker-compose

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
REBUILD=false
FORCE_REBUILD=false
RESTART=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build)
            REBUILD=true
            shift
            ;;
        -r|--rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -b, --build      Rebuild containers before starting"
            echo "  -r, --rebuild    Force rebuild containers without cache"
            echo "      --restart    Restart containers without rebuilding"
            echo "  -h, --help       Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if PostgreSQL container is running
if ! docker ps | grep -q mcp-postgres; then
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start-db.sh"
    echo ""
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check if docker-compose-dev.yml exists
if [ ! -f "docker-compose-dev.yml" ]; then
    echo "Error: docker-compose-dev.yml not found in $PROJECT_ROOT"
    exit 1
fi

# Restart containers if requested
if [ "$RESTART" = true ]; then
    echo "Restarting MCP servers..."
    docker-compose -f docker-compose-dev.yml restart
    echo ""
    echo "Services restarted!"
    echo ""
    echo "Available services:"
    echo "  - mcp_server_youtube_v2: http://localhost:8111"
    echo "  - mcp_server_twitter_apify: http://localhost:8109"
    echo ""
    echo "API Documentation:"
    echo "  - YouTube: http://localhost:8111/docs"
    echo "  - Twitter: http://localhost:8109/docs"
    exit 0
fi

# Rebuild containers if requested
if [ "$FORCE_REBUILD" = true ]; then
    echo "Stopping and removing existing containers..."
    docker-compose -f docker-compose-dev.yml down
    echo ""
    echo "Force rebuilding containers (no cache)..."
    docker-compose -f docker-compose-dev.yml build --no-cache
    echo ""
elif [ "$REBUILD" = true ]; then
    echo "Stopping and removing existing containers..."
    docker-compose -f docker-compose-dev.yml down
    echo ""
    echo "Rebuilding containers..."
    docker-compose -f docker-compose-dev.yml build
    echo ""
fi

echo "Starting MCP servers from docker-compose-dev.yml..."
echo ""

# Start all services (force recreate if we rebuilt)
if [ "$REBUILD" = true ] || [ "$FORCE_REBUILD" = true ]; then
    docker-compose -f docker-compose-dev.yml up -d --force-recreate
else
    docker-compose -f docker-compose-dev.yml up -d
fi

echo ""
echo "Services started!"
echo ""
echo "Available services:"
echo "  - mcp_server_youtube_v2: http://localhost:8111"
echo "  - mcp_server_twitter_apify: http://localhost:8109"
echo ""
echo "API Documentation:"
echo "  - YouTube: http://localhost:8111/docs"
echo "  - Twitter: http://localhost:8109/docs"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose-dev.yml"
echo ""
echo "Docker Compose Commands:"
echo "  Using helper script (recommended):"
echo "    $SCRIPT_DIR/mcp-compose.sh logs -f"
echo "    $SCRIPT_DIR/mcp-compose.sh logs -f mcp_server_youtube_v2"
echo "    $SCRIPT_DIR/mcp-compose.sh down"
echo ""
echo "  Or using absolute path:"
echo "    docker-compose -f \"$COMPOSE_FILE\" logs -f"
echo "    docker-compose -f \"$COMPOSE_FILE\" logs -f mcp_server_youtube_v2"
echo "    docker-compose -f \"$COMPOSE_FILE\" down"
echo ""
echo "To restart containers: $0 --restart"
echo "To rebuild containers: $0 --build"
echo "To force rebuild (no cache): $0 --rebuild"

