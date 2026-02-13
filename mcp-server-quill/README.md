# Quill MCP Server
> **General:** An MCP (Model Context Protocol) server for Quill Shield AI security audits.
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

| Method/Tool                | Price      | Description                                              |
| :------------------------- | :--------- | :------------------------------------------------------- |
| `search_token_address`     | **Free**   | Search for token contract address by name/symbol         |
| `get_evm_token_info`       | **Paid**   | Security analysis for EVM tokens (Ethereum, BSC, etc.)   |
| `get_solana_token_info`    | **Paid**   | Security analysis for Solana tokens                      |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

*Currently, all tools are available as hybrid endpoints.*

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8001/docs](http://localhost:8001/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8001/mcp](http://localhost:8001/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **Quill API Key** (get one from Quill Audits)
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-quill
    cp .env.example .env
    # Configure environment for Quill API, x402, etc.
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-quill/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_quill

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_quill
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-quill/

# Basic run
uv run python -m mcp_server_quill

# Or with custom port
uv run python -m mcp_server_quill --port 8001 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-quill/
# Build the image
docker build -t mcp-server-quill .

# Run the container
docker run --rm -it -p 8001:8001 --env-file .env mcp-server-quill
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-quill/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test files
uv run pytest tests/hybrid_routers/test_security.py
```

## Project Structure

```
mcp-server-quill/
├── src/
│   └── mcp_server_quill/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings with lru_cache factories
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── search.py            # Token search endpoint
│       │   ├── security.py          # Security analysis endpoints
│       │   └── pricing.py           # Pricing endpoint
│       ├── mcp_routers/             # MCP-Only endpoints
│       ├── middlewares/
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── quill/                   # Business logic layer
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
MCP_QUILL_X402_PRICING_MODE=on
MCP_QUILL_X402_PAYEE_EVM_ADDRESS=your_wallet_address
MCP_QUILL_X402_CDP_API_KEY_ID=your_cdp_id
MCP_QUILL_X402_CDP_API_KEY_SECRET=your_cdp_secret
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
