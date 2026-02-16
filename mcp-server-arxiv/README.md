# MCP Arxiv Server

> **General:** This repository provides an MCP (Model Context Protocol) server for searching and retrieving papers from the Arxiv preprint repository.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price          | Description                                                    |
| :-------------------------- | :------------- | :------------------------------------------------------------- |
| `GET /hybrid/pricing`       | **Free**       | Returns tool pricing configuration                             |
| `arxiv_search`              | **$0.01**      | Searches Arxiv for papers, downloads PDFs, and extracts text   |

**`arxiv_search` Tool Details:**
- **Input:**
    - `query` (required): The search query.
    - `max_results` (optional): Maximum number of papers to return.
    - `max_text_length` (optional): Maximum number of characters of text to extract from each paper.
- **Output:** A formatted string containing the title, authors, summary, and extracted text for each paper found.

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## Pricing Configuration

This server uses two separate pricing files to support different deployment environments:

### Development Pricing (`tool_pricing.dev.yaml`)
- **Used in**: Development Docker stage (`dev`)
- **Price**: $0.00001 per search (100x cheaper than production)
- **Purpose**: Low-cost testing and development
- **Networks**: Base, Polygon, Avalanche, SKALE Base, BNB Chain, Sei Network, Solana

### Production Pricing (`tool_pricing.yaml`)
- **Used in**: Production Docker stage (`prod`)
- **Price**: $0.01 per search
- **Purpose**: Live deployments
- **Networks**: Base, Polygon, Avalanche, SKALE Base, BNB Chain, Sei Network, Solana

The pricing format uses `price_usd` which is automatically converted to token amounts based on token decimals. All supported stablecoins use 6 decimals (USDC/USDT).

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/mcp](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-arxiv
    cp .env.example .env
    # Configure environment for x402, logging, etc. (see .env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-arxiv/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_arxiv

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_arxiv
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Basic run
uv run python -m mcp_server_arxiv

# Or with custom port and host
uv run python -m mcp_server_arxiv --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Build the image
docker build -t mcp-server-arxiv .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-arxiv
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-arxiv/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-arxiv/
├── src/
│   └── mcp_server_arxiv/
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   ├── pricing.py           # Pricing information
│       │   └── search.py            # Arxiv search functionality
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       ├── x402_integration/        # x402 payment integration
│       │   ├── __init__.py          # Public API exports
│       │   ├── config.py            # x402 configuration & pricing
│       │   └── accepted_assets.py   # Blockchain constants & utilities
│       │
│       └── xy_arxiv/                # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           ├── module.py
│           └── errors.py
│
├── tests/
│   ├── e2e/
│   │   ├── conftest.py              # E2E test fixtures
│   │   ├── config.py                # E2E test configuration
│   │   ├── utils.py                 # E2E test utilities
│   │   ├── test_api_routers.py      # API-only endpoint tests
│   │   └── test_hybrid_routers.py   # Hybrid endpoint tests
│   └── unit/                        # Unit tests
├── .env.example
├── Dockerfile
├── tool_pricing.yaml                # Production pricing
├── tool_pricing.dev.yaml            # Development pricing
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
