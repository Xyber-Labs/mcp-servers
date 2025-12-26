# YouTube MCP Server

A production-ready MCP (Model Context Protocol) server for searching YouTube videos and extracting transcripts, with optional x402 payment integration.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients.

| Method | Endpoint                    | Price    | Description                                    |
| :----- | :-------------------------- | :------- | :--------------------------------------------- |
| `GET`  | `/api/health`               | **Free** | Health check                                   |
| `POST` | `/api/search`               | **Free** | Search YouTube videos only                     |
| `POST` | `/api/search-transcripts`   | **Free** | Search videos and extract transcripts          |
| `POST` | `/api/extract-transcripts`  | **Free** | Extract transcripts from video IDs             |
| `GET`  | `/api/extract-transcript`   | **Free** | Extract transcript for a single video ID       |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools.

| Method/Tool              | Price    | Description                         |
| :----------------------- | :------- | :---------------------------------- |
| `POST /hybrid/search`    | **Free** | Search YouTube videos (REST + MCP)  |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents via the `/mcp` endpoint.

| Tool                            | Price    | Description                                    |
| :------------------------------ | :------- | :--------------------------------------------- |
| `mcp_search_youtube_videos`     | **Free** | Search YouTube videos without transcript extraction |
| `search_and_extract_transcripts`| **Free** | Search videos and extract transcripts          |
| `extract_transcripts`           | **Free** | Extract transcripts from video IDs             |

## API Documentation

Once the server is running, access the interactive API docs:

- **Swagger UI**: [http://localhost:8002/docs](http://localhost:8002/docs)
- **ReDoc**: [http://localhost:8002/redoc](http://localhost:8002/redoc)
- **OpenAPI JSON**: [http://localhost:8002/openapi.json](http://localhost:8002/openapi.json)

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **PostgreSQL** (required for caching - must be running externally)
- **Apify API token** (optional, for transcript extraction via `APIFY_TOKEN` env var)
- **Docker** (optional, for containerization)

## Setup

1. **Clone & Configure**
   ```bash
   cd mcp-server-youtube-v2
   cp .env.example .env
   # Edit .env and set your APIFY_TOKEN (required for transcript extraction)
   ```
   
   **Required Environment Variables:**
   - `APIFY_TOKEN` - Get from https://console.apify.com/account/integrations (optional, for transcript extraction)
   - `DB_NAME` - PostgreSQL database name (default: `mcp_youtube`)
   - `DB_USER` - PostgreSQL username (default: `postgres`)
   - `DB_PASSWORD` - PostgreSQL password (default: `postgres`)
   - `DB_HOST` - PostgreSQL host (default: `localhost`)
   - `DB_PORT` - PostgreSQL port (default: `5432`)
   
   **Optional Environment Variables:**
   - `MCP_YOUTUBE_PORT` - Server port (default: `8002`)
   - `MCP_YOUTUBE__YOUTUBE__DELAY_BETWEEN_REQUESTS` - Delay between requests (default: `1.0`)
   - `MCP_YOUTUBE__LOGGING__LOG_LEVEL` - Log level (default: `INFO`)
   - See `.env.example` for all available options
   
   **Note:** The server will connect to PostgreSQL using the `DATABASE_URL` constructed from the `DB_*` environment variables. Ensure PostgreSQL is running and accessible before starting the server.

2. **Install Dependencies**
   ```bash
   uv sync
   ```

3. **Setup PostgreSQL Database**
   
   The server requires PostgreSQL for caching video metadata and transcripts. You can use a local PostgreSQL instance or a managed service.
   
   **Local PostgreSQL (using Docker):**
   ```bash
   # Run PostgreSQL in a container
   docker run --rm -d \
     --name postgres-youtube \
     -e POSTGRES_DB=mcp_youtube \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     postgres:15
   
   # Verify connection
   psql -h localhost -U postgres -d mcp_youtube -c "SELECT version();"
   ```
   
   **Kubernetes Deployment:**
   
   For Kubernetes deployments, use a managed PostgreSQL service or a StatefulSet with persistent volumes:
   
   ```yaml
   # Example: Using a managed PostgreSQL service
   # Set DB_HOST to your PostgreSQL service endpoint
   # DB_HOST: postgres-service.default.svc.cluster.local
   ```
   
   **Important:** Ensure your PostgreSQL instance has persistent storage configured. In Kubernetes, use PersistentVolumes or a managed database service to prevent data loss on pod restarts.

## Running the Server

### Locally

```bash
# Basic run
uv run python -m mcp_server_youtube --port 8002

# With custom port and hot reload
uv run python -m mcp_server_youtube --port 8002 --reload
```

### Using Docker

#### Quick Start (Production)

```bash
# Build the production image
docker build --target prod -t mcp-server-youtube:latest .

# Run the container (ensure PostgreSQL is accessible from container)
docker run --rm -d \
  --name mcp-youtube \
  -p 8002:8002 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  mcp-server-youtube:latest
```

**Database:** The server connects to an external PostgreSQL database. Ensure your PostgreSQL instance is accessible from the container (use `DB_HOST` to specify the host, or use Docker networking for container-to-container communication).

#### Step-by-Step Guide

**1. Build the Docker Image**

```bash
cd mcp-server-youtube-v2

# Build production image (recommended)
docker build --target prod -t mcp-server-youtube:latest .

# Or build dev image (for development/debugging)
docker build --target dev -t mcp-server-youtube:dev .
```

**2. Run with Named Volumes (Docker-Managed Storage)**

```bash
# Create named volume for logs
docker volume create youtube-logs

# Run container with volumes (using .env file)
docker run --rm -d \
  --name mcp-youtube \
  -p 8002:8002 \
  --env-file .env \
  -v youtube-logs:/app/logs \
  mcp-server-youtube:latest
```

**3. Run with External PostgreSQL**

```bash
# Ensure PostgreSQL is running and accessible
# Set DB_* environment variables in .env or pass them directly

# Run container (PostgreSQL must be accessible from container)
docker run --rm -d \
  --name mcp-youtube \
  -p 8002:8002 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  mcp-server-youtube:latest
```

**PostgreSQL Setup:**
- ✅ Use an external PostgreSQL instance (recommended for production)
- ✅ For Docker Compose, ensure PostgreSQL service is accessible via network
- ✅ For Kubernetes, use a managed PostgreSQL service or StatefulSet with persistent volumes
- ✅ Data persists in PostgreSQL, not in container filesystem
- ✅ Can inspect database with PostgreSQL tools (`psql`, pgAdmin, etc.)

**4. Alternative: Manual Environment Variables**

If you prefer to specify environment variables manually instead of using `.env`:

```bash
docker run --rm -d \
  --name mcp-youtube \
  -p 8002:8002 \
  -e APIFY_TOKEN=your-token-here \
  -e MCP_YOUTUBE_PORT=8002 \
  -v youtube-logs:/app/logs \
  mcp-server-youtube:latest
```

**Note:** All examples above use `--env-file .env` to automatically load your `.env` file. Make sure your `.env` file exists in the same directory where you run the `docker run` command.

#### Docker Commands Reference

```bash
# View logs
docker logs -f mcp-youtube

# Stop the container
docker stop mcp-youtube

# Start a stopped container
docker start mcp-youtube

# Restart the container
docker restart mcp-youtube

# Remove the container
docker rm -f mcp-youtube

# Execute commands inside container
docker exec -it mcp-youtube bash

# View container status
docker ps | grep mcp-youtube
```

#### Testing Database Persistence

To verify that videos are stored in PostgreSQL and persist across container restarts:

```bash
# 1. Process some videos (search and extract transcripts)
curl -X POST http://localhost:8002/api/search-transcripts \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "num_videos": 2}'

# 2. Query PostgreSQL to see stored videos
psql -h localhost -U postgres -d mcp_youtube -c "SELECT video_id, title, transcript_success FROM youtube_videos LIMIT 5;"

# 3. Count total videos in database
psql -h localhost -U postgres -d mcp_youtube -c "SELECT COUNT(*) FROM youtube_videos;"

# 4. Stop the container
docker stop mcp-youtube

# 5. Restart the container
docker start mcp-youtube
# OR recreate it:
docker run --rm -d \
  --name mcp-youtube \
  -p 8002:8002 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  mcp-server-youtube:latest

# 6. Query database again - videos should still be there!
psql -h localhost -U postgres -d mcp_youtube -c "SELECT video_id, title, transcript_success FROM youtube_videos LIMIT 5;"

# 7. Test that cached videos are used (should be faster, no re-fetching)
curl -X POST http://localhost:8002/api/search-transcripts \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "num_videos": 2}'
# Check logs - you should see cached transcripts being used
```

**Note:** Replace `localhost`, `postgres`, and `mcp_youtube` with your actual PostgreSQL connection details from your `.env` file.

#### Development Mode

For development with hot reload and debugging:

```bash
# Build dev image
docker build --target dev -t mcp-server-youtube:dev .

# Run in interactive mode (using .env file)
docker run --rm -it \
  --name mcp-youtube-dev \
  -p 8002:8002 \
  --env-file .env \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/logs:/app/logs \
  mcp-server-youtube:dev \
  python -m mcp_server_youtube --port 8002 --reload
```

#### Testing the Docker Container

```bash
# Health check
curl http://localhost:8002/api/health

# Check logs
docker logs mcp-youtube

# Run tests against Docker container
# (from host machine, ensure server is running)
uv run python -m pytest tests/test_mcp_tools.py -v
```

**Note:** 
- The PostgreSQL database is external and must be accessible from the container
- Logs are stored in `/app/logs` inside the container (mounted as volume)
- Ensure `DB_*` environment variables are set correctly for PostgreSQL connection
- The production image uses port 8002 by default
- Use `--target prod` for production builds (smaller, optimized)
- Use `--target dev` for development (includes dev tools)

## Testing

### Running Tests

```bash
# Run all tests
uv run python -m pytest

# Run with verbose output
uv run python -m pytest -v

# Run specific test file
uv run python -m pytest tests/test_api_routers.py

# Run with coverage
uv run python -m pytest --cov=mcp_server_youtube --cov-report=html

# Run specific test
uv run python -m pytest tests/test_app.py::TestAppLifespan::test_app_lifespan_success
```

**Note:** Use `uv run python -m pytest` instead of `uv run pytest` to ensure the correct Python environment is used.

### Testing REST Endpoints

```bash
# Health check
curl http://localhost:8002/api/health

# Search videos
curl -X POST http://localhost:8002/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "max_results": 3}'

# Extract transcript for single video
curl "http://localhost:8002/api/extract-transcript?video_id=dQw4w9WgXcQ"

# Extract transcripts for multiple videos
curl -X POST http://localhost:8002/api/extract-transcripts \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["dQw4w9WgXcQ"]}'
```

### Testing MCP Tools

MCP tools use the StreamableHTTP transport protocol, which requires session negotiation.

#### Option 1: Using pytest (Recommended)

```bash
# Run MCP E2E tests with pytest (requires running server)
uv run python -m pytest tests/test_mcp_tools.py -v

# Run all tests including MCP E2E tests
uv run python -m pytest

# Skip integration tests (faster, unit tests only)
uv run python -m pytest -m "not integration"
```

#### Option 2: Standalone Script

```bash
# Run the test script directly (for manual testing)
uv run python tests/test_mcp_tools.py
```

#### Option 2: Using Bash Script

```bash
# Run the bash test script
./test_mcp.sh
```

#### Option 3: Manual curl Commands

**Step 1: Negotiate Session ID**
```bash
SESSION_ID=$(curl -s -X GET http://localhost:8002/mcp/ \
  -H "Accept: text/event-stream" \
  -i | grep -i "mcp-session-id" | cut -d' ' -f2 | tr -d '\r\n')
echo "Session ID: $SESSION_ID"
```

**Step 2: Initialize Session**
```bash
curl -X POST http://localhost:8002/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
  }'
```

**Step 3: List Available Tools**
```bash
curl -X POST http://localhost:8002/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**Step 4: Call a Tool**
```bash
curl -X POST http://localhost:8002/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "mcp_search_youtube_videos",
      "arguments": {
        "query": "python tutorial",
        "max_results": 3
      }
    }
  }'
```

**Note:** Responses come in Server-Sent Events (SSE) format. Parse the `data:` lines to extract JSON:
```bash
# Extract JSON from SSE response
curl ... | grep "^data:" | sed 's/^data: //' | jq '.'
```

### Using MCP Client Libraries

For production use, consider using MCP client libraries like:
- `mcp` Python SDK
- `@modelcontextprotocol/sdk` (TypeScript/JavaScript)
- `langchain-mcp-adapters` (for LangChain integration)

Example with Python MCP SDK:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to HTTP MCP server
# (implementation depends on your MCP client library)
```

## Project Structure

```
mcp-server-youtube-v2/
├── src/
│   └── mcp_server_youtube/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with nested configs
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── health.py
│       │   ├── admin.py
│       │   └── youtube.py
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   └── search.py
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── transcripts.py
│       │   └── search.py
│       ├── middlewares/
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── youtube/                 # Business logic layer
│           ├── __init__.py
│           ├── models.py            # SQLAlchemy models
│           ├── methods.py           # Database methods
│           └── client.py            # YouTube search & transcript extraction
│
├── tests/
│   ├── test_mcp_tools.py            # Python test script for MCP tools
│   ├── test_api_routers.py
│   ├── test_app.py
│   └── test_youtube_client.py
├── test_mcp.sh                      # Bash test script for MCP tools
├── tool_pricing.yaml                # x402 pricing configuration
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Environment Variables

- `APIFY_TOKEN`: Apify API token for transcript extraction (optional)
- `DELAY_BETWEEN_REQUESTS`: Delay between YouTube API requests (default: 1.0)
- `MAX_RESULTS`: Maximum search results (default: 10)
- `NUM_VIDEOS`: Number of videos to process (default: 5)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: logs/mcp_youtube.log)

## License

MIT

