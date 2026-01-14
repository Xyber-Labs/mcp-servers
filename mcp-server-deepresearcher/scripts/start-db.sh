#!/bin/bash
# Start PostgreSQL for Deep Researcher MCP Server local development

set -e  # Exit on error

CONTAINER_NAME="mcp-deep-research-postgres-local"
DB_NAME="mcp_deep_research_postgres"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_PORT="5432"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if port 5432 is already in use by another container
PORT_IN_USE=$(docker ps --format "{{.Names}}" --filter "publish=5432" | grep -v "^$" || true)
if [ -n "$PORT_IN_USE" ] && [ "$PORT_IN_USE" != "$CONTAINER_NAME" ]; then
    echo "Found existing PostgreSQL container on port 5432: $PORT_IN_USE"
    echo "Using existing PostgreSQL container instead of creating a new one."
    echo ""
    
    # Check if the database exists
    DB_EXISTS=$(docker exec "$PORT_IN_USE" psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "")
    
    if [ "$DB_EXISTS" = "1" ]; then
        echo "✓ Database '$DB_NAME' already exists."
    else
        echo "Creating database '$DB_NAME' in existing container..."
        docker exec "$PORT_IN_USE" psql -U postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database may already exist or creation failed."
    fi
    
    # Check if user exists and has privileges
    USER_EXISTS=$(docker exec "$PORT_IN_USE" psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "")
    if [ "$USER_EXISTS" = "1" ]; then
        echo "✓ User '$DB_USER' already exists."
        # Ensure privileges are granted
        docker exec "$PORT_IN_USE" psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    else
        echo "Creating user '$DB_USER'..."
        docker exec "$PORT_IN_USE" psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "User creation skipped (may already exist)."
        docker exec "$PORT_IN_USE" psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    fi
    
    echo ""
    echo "Using existing PostgreSQL container: $PORT_IN_USE"
    echo "Connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
    echo ""
    echo "To connect via psql:"
    echo "  docker exec -it $PORT_IN_USE psql -U $DB_USER -d $DB_NAME"
    echo ""
    echo "To view logs:"
    echo "  docker logs -f $PORT_IN_USE"
    echo ""
    exit 0
fi

# Check if container exists
if ! docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Creating PostgreSQL container on port $DB_PORT..."
    docker run -d \
      --name "$CONTAINER_NAME" \
      -e POSTGRES_PASSWORD="$DB_PASSWORD" \
      -e POSTGRES_DB="$DB_NAME" \
      -e POSTGRES_USER="$DB_USER" \
      -v mcp-deep-research-postgres-data:/var/lib/postgresql/data \
      -p "$DB_PORT:5432" \
      postgres:latest
    echo "Container created. Waiting for PostgreSQL to initialize..."
    sleep 10
else
    # Check if container is already running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "PostgreSQL container is already running."
    else
        echo "Starting existing PostgreSQL container..."
        docker start "$CONTAINER_NAME"
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
fi

# Wait for PostgreSQL to be ready
echo "Checking PostgreSQL readiness..."
for i in {1..30}; do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" &> /dev/null; then
        echo "PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Warning: PostgreSQL did not become ready within 30 seconds."
        exit 1
    fi
    sleep 1
done

echo ""
echo "PostgreSQL is running!"
echo "Container: $CONTAINER_NAME"
echo "Connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
echo ""
echo "To connect via psql:"
echo "  docker exec -it $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME"
echo ""
echo "To view logs:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "To stop the database:"
echo "  docker stop $CONTAINER_NAME"
echo ""
if [ "$DB_PORT" != "5432" ]; then
    echo "Note: This container is using port $DB_PORT instead of the default 5432."
    echo "Update your DATABASE_URL in .env to use port $DB_PORT if needed."
fi

