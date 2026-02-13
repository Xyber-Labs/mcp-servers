# Lurky MCP Server
> **General:** An MCP (Model Context Protocol) server for searching and parsing Twitter Spaces summaries using the Lurky API.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously, with integrated x402 payment support.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |
| `GET`  | `/hybrid/pricing`     | **Free**   | Returns tool pricing configuration     |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                   | Price      | Description                                      |
| :---------------------------- | :--------- | :----------------------------------------------- |
| `lurky_search_spaces`         | **Paid**   | Search for Twitter Spaces discussions by keyword |
| `lurky_get_space_details`     | **Paid**   | Get full details and summary for a Space ID      |
| `lurky_get_latest_summaries`  | **Paid**   | Fetch latest N summaries for a topic             |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

*Currently, all tools are available as hybrid endpoints.*

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **PostgreSQL** database (for caching)
- **Lurky API Key** (get one at [lurky.app](https://lurky.app))
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-lurky
    cp .env.example .env
    # Configure environment for Lurky API, database, x402, etc.
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-lurky/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_lurky

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_lurky
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-lurky/

# Start PostgreSQL first (if not already running)
./scripts/start_db.sh

# Basic run
uv run python -m mcp_server_lurky

# Or with custom port
uv run python -m mcp_server_lurky --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-lurky/
# Build the image
docker build -t mcp-server-lurky .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-lurky
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-lurky/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run integration tests (requires running server)
uv run pytest tests/test_mcp_tools.py -m integration
```

## Project Structure

```
mcp-server-lurky/
├── src/
│   └── mcp_server_lurky/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── spaces.py            # Twitter Spaces search & details
│       │   └── pricing.py           # Pricing endpoint
│       ├── mcp_routers/             # MCP-Only endpoints
│       ├── middlewares/
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       ├── db/                      # Database models & utilities
│       └── lurky/                   # Business logic layer
│           ├── client.py
│           ├── models.py
│           └── errors.py
│
├── tests/
├── scripts/
├── .env.example
├── Dockerfile
├── pyproject.toml
├── tool_pricing.yaml
└── README.md
```

## x402 Payment Integration

This server uses the x402 protocol for monetization. Pricing for each tool and endpoint is defined in `tool_pricing.yaml`.

To enable payments, configure the following in your `.env`:
```bash
MCP_LURKY_X402_PRICING_MODE=on
MCP_LURKY_X402_PAYEE_EVM_ADDRESS=your_wallet_address
MCP_LURKY_X402_CDP_API_KEY_ID=your_cdp_id
MCP_LURKY_X402_CDP_API_KEY_SECRET=your_cdp_secret
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
