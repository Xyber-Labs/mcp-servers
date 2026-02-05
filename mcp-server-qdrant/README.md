# Qdrant MCP Server

A Model Context Protocol (MCP) server that provides semantic search, document storage, and collection management capabilities for Qdrant vector database with advanced multi-tenant filtering.

## Capabilities

This server exposes Qdrant vector database functionality through both REST API and MCP protocols. It includes advanced features like multi-tenant data isolation, configurable payload indexes, and optimized HNSW settings for high-performance semantic search.

### API-Only Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check endpoint |

### Hybrid Endpoints (REST + MCP)

| Endpoint | Method | Operation ID | Description |
|----------|--------|--------------|-------------|
| `/hybrid/pricing` | GET | `qdrant_get_pricing` | Get tool pricing configuration |
| `/hybrid/store` | POST | `qdrant_store` | Store information with metadata in collections |
| `/hybrid/find` | POST | `qdrant_find` | Search documents with semantic similarity and optional filtering |
| `/hybrid/get_collections` | POST | `qdrant_get_collections` | List all available collections |
| `/hybrid/get_collection_info` | POST | `qdrant_get_collection_info` | Get detailed collection configuration including payload schema |

### MCP Tools

All hybrid endpoints are also accessible via MCP protocol at `/mcp`:

1. `qdrant_store`
   - Store information with metadata in Qdrant collections
   - Input: `information` (required), `collection_name` (required), `metadata` (optional)
   - Output: Confirmation string with storage details

2. `qdrant_find`
   - Search documents with semantic similarity and optional filtering
   - Input: `query` (required), `collection_name` (required), `search_limit` (optional, default: 10), `filters` (optional)
   - Output: List of scored points with content and metadata

3. `qdrant_get_collections`
   - List all available collections
   - Input: None
   - Output: List of collection names

4. `qdrant_get_collection_info`
   - Get detailed collection configuration including payload schema
   - Input: `collection_name` (required)
   - Output: Collection information with configuration details

5. `qdrant_get_pricing`
   - Get tool pricing configuration
   - Input: None
   - Output: Pricing configuration object

## API Documentation

When the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Requirements

- Python 3.12+
- UV (for dependency management)
- Docker (optional, for containerization)
- Qdrant instance (local or cloud)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-qdrant/`.
   ```dotenv
   # Basic Connection
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_API_KEY="your_api_key"

   # Embedding Configuration
   EMBEDDING_PROVIDER=fastembed
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-qdrant/
   # Using UV (recommended)
   uv sync
   
   # Or install for development
   uv sync --group dev
   ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_qdrant

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_qdrant
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Basic run
uv run python -m mcp_server_qdrant

# Or with custom port and host
uv run python -m mcp_server_qdrant --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Build the image
docker build -t mcp-server-qdrant .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-qdrant
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-qdrant/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-qdrant/
├── src/
│   └── mcp_server_qdrant/
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── schemas.py               # Pydantic request/response models
│       ├── exceptions.py            # Custom exception definitions
│       ├── logging_config.py        # Logging configuration
│       ├── middleware.py            # Middleware configuration
│       ├── x402_config.py           # x402 payment configuration
│       ├── tools.py                 # Tool definitions
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py           # Pricing information
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   └── qdrant_tools.py      # Qdrant MCP tools
│       │
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       └── qdrant/                  # Business logic layer
│           ├── __init__.py
│           ├── config.py            # Qdrant configuration
│           ├── module.py            # Core Qdrant operations
│           └── embeddings/          # Embedding providers
│               ├── __init__.py
│               ├── base.py          # Base embedding interface
│               ├── factory.py       # Embedding factory
│               ├── fastembed.py     # FastEmbed implementation
│               └── types.py         # Type definitions
│
├── tests/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
