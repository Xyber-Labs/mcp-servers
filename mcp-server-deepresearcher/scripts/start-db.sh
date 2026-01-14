#!/bin/bash
# Start PostgreSQL for Deep Researcher MCP Server local development

if ! docker ps -a | grep -q mcp-deep-research-postgres-local; then
    echo "Creating PostgreSQL container..."
    docker run -d \
      --name mcp-deep-research-postgres-local \
      -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=mcp_deep_research_postgres \
      -e POSTGRES_USER=postgres \
      -v mcp-deep-research-postgres-data:/var/lib/postgresql \
      -p 5432:5432 \
      postgres:latest
else
    echo "Starting existing PostgreSQL container..."
    docker start mcp-deep-research-postgres-local
fi

echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo "PostgreSQL is running!"
echo "Connection: postgresql://postgres:postgres@localhost:5432/mcp_deep_research_postgres"
echo ""
echo "To connect: docker exec -it mcp-deep-research-postgres-local psql -U postgres -d mcp_deep_research_postgres"

