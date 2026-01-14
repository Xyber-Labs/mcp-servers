#!/bin/bash
# Start PostgreSQL for local development

if ! docker ps -a | grep -q youtube-postgres-local; then
    echo "Creating PostgreSQL container..."
    docker run -d \
      --name youtube-postgres-local \
      -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=mcp_youtube \
      -e POSTGRES_USER=postgres \
      -v youtube-postgres-data:/var/lib/postgresql \
      -p 5432:5432 \
      postgres:latest
else
    echo "Starting existing PostgreSQL container..."
    docker start youtube-postgres-local
fi

echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo "PostgreSQL is running!"
echo "Connection: postgresql://postgres:postgres@localhost:5432/mcp_youtube"
echo ""
echo "To connect: docker exec -it youtube-postgres-local psql -U postgres -d mcp_youtube"

