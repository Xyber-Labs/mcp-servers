#!/bin/bash
# Start PostgreSQL for MCP servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if mcp-postgres container is already running
if docker ps | grep -q mcp-postgres; then
    echo "PostgreSQL container (mcp-postgres) is already running!"
elif docker ps -a | grep -q mcp-postgres; then
    echo "Starting existing PostgreSQL container..."
    if ! docker start mcp-postgres 2>/dev/null; then
        echo "Error: Failed to start container. Port 5432 may be in use by another service."
        echo ""
        echo "Checking what's using port 5432..."
        if command -v lsof >/dev/null 2>&1; then
            lsof -i :5432 || echo "  (lsof not available, cannot check)"
        elif command -v netstat >/dev/null 2>&1; then
            netstat -tuln | grep :5432 || echo "  (netstat not available, cannot check)"
        fi
        echo ""
        echo "If another PostgreSQL instance is running, you can either:"
        echo "  1. Stop it: docker stop <container-name>"
        echo "  2. Use a different port by modifying this script"
        exit 1
    fi
else
    echo "Creating PostgreSQL container..."
    
    # Check if port 5432 is already in use
    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :5432 >/dev/null 2>&1; then
            echo "Error: Port 5432 is already in use!"
            echo ""
            echo "What's using port 5432:"
            lsof -i :5432
            echo ""
            echo "Please stop the service using port 5432 or use a different port."
            exit 1
        fi
    fi
    
    # Check if init-db.sh exists
    if [ ! -f "$PROJECT_ROOT/init-db.sh" ]; then
        echo "Warning: init-db.sh not found at $PROJECT_ROOT/init-db.sh"
        echo "Databases will need to be created manually."
        INIT_DB_MOUNT=""
    else
        INIT_DB_MOUNT="-v $PROJECT_ROOT/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro"
    fi
    
    if ! docker run -d \
      --name mcp-postgres \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=mcpdb \
      -p 5432:5432 \
      -v mcp-postgres-data:/var/lib/postgresql/data \
      $INIT_DB_MOUNT \
      postgres:15-alpine 2>&1; then
        echo ""
        echo "Error: Failed to create PostgreSQL container. Port 5432 may be in use."
        exit 1
    fi
fi

echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Verify connection
if docker exec mcp-postgres psql -U postgres -d mcpdb -c "SELECT version();" > /dev/null 2>&1; then
    echo "PostgreSQL is running!"
    echo ""
    echo "Connection: postgresql://postgres:postgres@localhost:5432/mcpdb"
    echo ""
    echo "Available databases:"
    echo "  - mcpdb (default)"
    echo "  - mcp_youtube (for YouTube service)"
    echo "  - mcp_twitter_apify (for Twitter service)"
    echo ""
    echo "To connect: docker exec -it mcp-postgres psql -U postgres -d mcpdb"
else
    echo "Warning: PostgreSQL container started but connection test failed."
    echo "Check logs with: docker logs mcp-postgres"
    echo ""
    echo "If port 5432 is already in use by another PostgreSQL instance,"
    echo "you may need to stop it first or use a different port."
fi

