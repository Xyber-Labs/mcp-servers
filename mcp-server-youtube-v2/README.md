# YouTube MCP Server

A production-ready MCP (Model Context Protocol) server for searching YouTube videos and extracting transcripts, with optional x402 payment integration.

## Capabilities

### 1. **API-Only Endpoints** (`/api/v1`)

Standard REST endpoints for traditional clients.

| Method | Endpoint                    | Price    | Description                                    |
| :----- | :-------------------------- | :------- | :--------------------------------------------- |
| `GET`  | `/api/v1/health`            | **Free** | Health check                                   |
| `GET`  | `/api/v1/admin/logs`        | **Paid** | Admin logs                                     |
| `POST` | `/api/v1/search`            | **Free** | Search YouTube videos only                     |
| `POST` | `/api/v1/search-transcripts`| **Free** | Search videos and extract transcripts          |
| `POST` | `/api/v1/extract-transcripts`| **Free** | Extract transcripts from video IDs             |
| `GET`  | `/api/v1/extract-transcript`| **Free** | Extract transcript for a single video ID       |

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
   - `APIFY_TOKEN` - Get from https://console.apify.com/account/integrations
   
   **Optional Environment Variables:**
   - `DB_PATH` - SQLite database path (default: `videos.db`)
   - `MCP_YOUTUBE_PORT` - Server port (default: `8002`)
   - `MCP_YOUTUBE__YOUTUBE__DELAY_BETWEEN_REQUESTS` - Delay between requests (default: `1.0`)
   - `MCP_YOUTUBE__LOGGING__LOG_LEVEL` - Log level (default: `INFO`)
   - See `.env.example` for all available options

2. **Install Dependencies**
   ```bash
   uv sync
   ```

## Running the Server

### Locally

```bash
# Basic run
uv run python -m mcp_server_youtube --port 8002

# With custom port and hot reload
uv run python -m mcp_server_youtube --port 8002 --reload
```

### Using Docker

```bash
# Build the image
docker build -t mcp-server-youtube .

# Run the container with persistent database storage
docker run --rm -it -p 8002:8002 \
  -e APIFY_TOKEN=your-token-here \
  -v youtube-data:/data \
  -v youtube-logs:/app/logs \
  mcp-server-youtube
```

**With named volumes (recommended for persistence):**
```bash
# Create named volumes for data persistence
docker volume create youtube-data
docker volume create youtube-logs

# Run container with volumes
docker run --rm -it -p 8002:8002 \
  -e APIFY_TOKEN=your-token-here \
  -v youtube-data:/data \
  -v youtube-logs:/app/logs \
  mcp-server-youtube
```

**With bind mounts (for local access to database):**
```bash
# Run container with bind mounts to local directories
docker run --rm -it -p 8002:8002 \
  -e APIFY_TOKEN=your-token-here \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/app/logs \
  mcp-server-youtube
```

**Note:** The SQLite database (`videos.db`) is stored in `/data` inside the container, which is mounted as a volume. This ensures that cached video metadata and transcripts persist across container restarts.

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
curl http://localhost:8002/api/v1/health

# Search videos
curl -X POST http://localhost:8002/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "max_results": 3}'

# Extract transcript for single video
curl "http://localhost:8002/api/v1/extract-transcript?video_id=dQw4w9WgXcQ"

# Extract transcripts for multiple videos
curl -X POST http://localhost:8002/api/v1/extract-transcripts \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["dQw4w9WgXcQ"]}'
```

### Testing MCP Tools

MCP tools use the StreamableHTTP transport protocol, which requires session negotiation.

#### Option 1: Using Python Script (Recommended)

```bash
# Run the test script
uv run python test_mcp_tools.py
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
├── test_mcp_tools.py                # Python test script for MCP tools
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

