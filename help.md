# Start Postgres 15 Alpine with persistent volume and auto-create databases
# The init-db.sh script will run automatically on first startup only
docker run -d \
  --name mcp-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mcpdb \
  -p 5432:5432 \
  -v mcp-postgres-data:/var/lib/postgresql/data \
  -v $(pwd)/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro \
  postgres:15-alpine

# Note: Databases are created automatically on first startup via init-db.sh
# If you need to recreate them, stop and remove the container and volume:
# docker stop mcp-postgres && docker rm mcp-postgres && docker volume rm mcp-postgres-data

# Start only arxiv MCP service (for testing)
docker-compose -f docker-compose-dev.yml up -d mcp_server_arxiv

# Start only tavily MCP service
docker-compose -f docker-compose-dev.yml up -d mcp_server_tavily

# Start all services
docker-compose -f docker-compose-dev.yml up -d

# View logs
docker-compose -f docker-compose-dev.yml logs -f

# View logs for specific service
docker-compose -f docker-compose-dev.yml logs -f mcp_server_arxiv

# Test Arxiv MCP Service
# 1. Check Swagger UI (API documentation)
open http://localhost:8100/docs

# 2. Check service health
curl http://localhost:8100/mcp/

# 3. Test via MCP client (requires proper session handling)
# The MCP endpoint is at: http://localhost:8100/mcp/
# Use an MCP client or Cursor's built-in MCP support to test
# Tool name: arxiv_search
# Parameters: query (required), max_results (optional), max_text_length (optional)

# Example test query via logs (watch logs while using MCP client):
docker-compose -f docker-compose-dev.yml logs -f mcp_server_arxiv | grep -E "arxiv_search|CallToolRequest|ERROR"