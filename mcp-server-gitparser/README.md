# Gitparser MCP Server
> **General:** An MCP (Model Context Protocol) server for parsing **GitBook** documentation sites and **GitHub** repositories into a single Markdown file optimized for LLM parsing.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

| Method | Endpoint       | Description               |
| :----- | :------------- | :------------------------ |
| `GET`  | `/api/health`  | Health check              |

### 2. **Hybrid Endpoints** (`/hybrid`)

These are exposed as both REST endpoints and MCP tools.

| Method/Tool                | Description                                  |
| :------------------------- | :------------------------------------------- |
| `gitparser_parse_gitbook`  | Convert a GitBook site into Markdown         |
| `gitparser_parse_github`   | Convert a GitHub repo into Markdown (gitingest) |

## API Documentation

Once the server is running:

- **Swagger UI**: `http://localhost:8000/docs`
- **MCP endpoint**: `http://localhost:8000/mcp`

## Requirements

- **Python 3.12+**
- **UV** (dependency management)
- **Docker** (optional)

## Setup

```bash
# path: ./mcp-servers/mcp-server-gitparser/
uv sync
```

## Running the Server

### Locally

```bash
# Basic run
uv run --python 3.12 python -m mcp_server_gitparser

# Or use the helper script
./scripts/start-server.sh
```

### Using Docker (Standalone)

```bash
# Build the image
docker build -t mcp-server-gitparser .

# Run the container
docker run --rm -it -p 8000:8000 mcp-server-gitparser

# Or use the helper script
./scripts/start-docker.sh --rebuild
```

## Project Structure

```
mcp-server-gitparser/
├── src/
│   └── mcp_server_gitparser/
│       ├── __main__.py              # Entry point (uvicorn)
│       ├── app.py                   # Application factory (REST + MCP)
│       ├── config.py                # Settings (.env support)
│       ├── logging_config.py        # Uvicorn logging configuration
│       ├── schemas.py               # Pydantic request/response models
│       ├── api_routers/             # API-only routes (REST)
│       ├── hybrid_routers/          # Hybrid routes (REST + MCP)
│       ├── mcp_routers/             # MCP-only routes (optional)
│       └── gitparser/               # Business logic layer
├── scripts/
├── docs/
├── tests/
├── Dockerfile
├── pyproject.toml
├── tool_pricing.yaml
└── uv.lock
```
