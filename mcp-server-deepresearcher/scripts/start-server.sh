#!/bin/bash
# Start MCP Deep Researcher Server

# Don't use set -e here because we handle errors gracefully in restart/stop functions
set -u  # Exit on undefined variables

# Default values
RESTART=false
REBUILD=false
NO_RELOAD=false
PORT=8003

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            RESTART=true  # Rebuild implies restart
            shift
            ;;
        --no-reload)
            NO_RELOAD=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --restart      Stop the server if running and restart it"
            echo "  --rebuild      Rebuild dependencies (uv sync) and restart"
            echo "  --no-reload    Disable hot reload (production mode)"
            echo "  --port PORT    Specify port (default: 8003)"
            echo "  --help, -h     Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Function to check if server is running on a port
is_server_running() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -ti:$port > /dev/null 2>&1
    elif command -v netstat &> /dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":$port "
    elif command -v ss &> /dev/null; then
        ss -tuln 2>/dev/null | grep -q ":$port "
    else
        # Fallback: try to connect to the port
        timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null
    fi
}

# Function to stop server on a port
stop_server_on_port() {
    local port=$1
    echo "Stopping server on port $port..."
    
    if command -v lsof &> /dev/null; then
        local pid=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pid" ]; then
            kill -TERM "$pid" 2>/dev/null || true
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo "Server stopped gracefully."
                    return 0
                fi
                sleep 1
            done
            # Force kill if still running
            kill -KILL "$pid" 2>/dev/null || true
            echo "Server force-stopped."
        else
            echo "No server found running on port $port."
        fi
    elif command -v fuser &> /dev/null; then
        fuser -k $port/tcp 2>/dev/null || true
        echo "Server stopped."
    else
        echo "Warning: Cannot find a tool to stop the server (lsof/fuser not available)."
        echo "Please stop the server manually (Ctrl+C or kill the process)."
    fi
}

# Handle restart
if [ "$RESTART" = true ]; then
    if is_server_running $PORT; then
        stop_server_on_port $PORT
        echo "Waiting 2 seconds before restarting..."
        sleep 2
    else
        echo "No server found running on port $PORT. Starting fresh..."
    fi
fi

# Handle rebuild
if [ "$REBUILD" = true ]; then
    echo "Rebuilding dependencies..."
    if ! command -v uv &> /dev/null; then
        echo "Error: uv is not installed. Please install it first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    uv sync --python 3.12
    echo "Dependencies rebuilt."
    echo ""
fi

# Check if PostgreSQL is accessible (either our container or another on port 5432)
POSTGRES_RUNNING=false
if docker ps | grep -q mcp-deep-research-postgres-local; then
    POSTGRES_RUNNING=true
    echo "Using dedicated PostgreSQL container: mcp-deep-research-postgres-local"
elif docker ps --format "{{.Names}}" --filter "publish=5432" | grep -q .; then
    EXISTING_PG=$(docker ps --format "{{.Names}}" --filter "publish=5432" | head -n1)
    echo "Found existing PostgreSQL container on port 5432: $EXISTING_PG"
    echo "Using existing PostgreSQL (database will be set up if needed)."
    POSTGRES_RUNNING=true
fi

if [ "$POSTGRES_RUNNING" = false ]; then
    echo "PostgreSQL container is not running. Starting it..."
    "$SCRIPT_DIR/start-db.sh"
    echo ""
else
    # Ensure database exists in existing PostgreSQL
    "$SCRIPT_DIR/start-db.sh" 2>/dev/null || true
fi

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Warning: .env file not found. Some features may not work without proper configuration."
    echo "Create a .env file in the project root with required environment variables."
    echo ""
fi

echo "Starting MCP Deep Researcher Server..."
echo "Server will be available at: http://localhost:$PORT"
echo "API docs: http://localhost:$PORT/docs"
echo "MCP endpoint: http://localhost:$PORT/mcp-server/mcp"
echo ""

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Build command arguments
RELOAD_FLAG=""
if [ "$NO_RELOAD" = false ]; then
    RELOAD_FLAG="--reload"
fi

# Start the server (using Python 3.12)
echo "Starting server on port $PORT..."
if [ "$NO_RELOAD" = true ]; then
    echo "Production mode: Hot reload disabled"
else
    echo "Development mode: Hot reload enabled"
fi
echo ""

uv run --python 3.12 python -m mcp_server_deepresearcher --host 0.0.0.0 --port "$PORT" $RELOAD_FLAG

