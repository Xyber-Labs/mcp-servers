#!/bin/bash
# Start Gitparser MCP Server in Docker (standalone)

set -e  # Exit on error

# Default values
RESTART=false
REBUILD=false
PORT=8000
CONTAINER_NAME="mcp-server-gitparser"
IMAGE_NAME="mcp-server-gitparser"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            RESTART=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --container-name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --restart              Stop the container if running and restart it"
            echo "  --rebuild              Rebuild Docker image and restart"
            echo "  --port PORT            Specify port (default: 8000)"
            echo "  --container-name NAME  Specify container name (default: mcp-server-gitparser)"
            echo "  --image-name NAME      Specify image name (default: mcp-server-gitparser)"
            echo "  --help, -h             Show this help message"
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

cd "$PROJECT_ROOT"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

is_container_running() {
    docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

remove_container() {
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "Removing container ${CONTAINER_NAME}..."
        docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        echo "Container removed."
    fi
}

if [ "$RESTART" = true ]; then
    if is_container_running; then
        echo "Stopping container ${CONTAINER_NAME}..."
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
    fi
    remove_container
    echo "Waiting 2 seconds before restarting..."
    sleep 2
else
    # Remove stopped container with same name
    if docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        if ! is_container_running; then
            echo "Found stopped container ${CONTAINER_NAME}. Removing it..."
            remove_container
        fi
    fi
fi

if [ "$REBUILD" = true ]; then
    echo "Rebuilding Docker image ${IMAGE_NAME}..."
    docker build -t "${IMAGE_NAME}" .
    echo "Image rebuilt."
    echo ""
fi

if ! docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
    echo "Docker image ${IMAGE_NAME} not found. Building it..."
    docker build -t "${IMAGE_NAME}" .
    echo ""
fi

echo "Starting Gitparser MCP Server in Docker..."
echo "Container: ${CONTAINER_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Server will be available at: http://localhost:${PORT}"
echo "API docs: http://localhost:${PORT}/docs"
echo "MCP endpoint: http://localhost:${PORT}/mcp/"
echo ""

docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${PORT}:8000" \
  -e "MCP_GITPARSER_PORT=8000" \
  --restart unless-stopped \
  "${IMAGE_NAME}"

echo ""
echo "✓ Container started successfully!"
echo ""
echo "Useful commands:"
echo "  docker logs -f ${CONTAINER_NAME}     # View logs"
echo "  docker stop ${CONTAINER_NAME}       # Stop container"
echo "  docker restart ${CONTAINER_NAME}     # Restart container"
echo "  docker exec -it ${CONTAINER_NAME} bash  # Access container shell"

