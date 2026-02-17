# Gitparser MCP Server
> **General:** An MCP (Model Context Protocol) server for parsing **GitBook** documentation sites and **GitHub** repositories into a single Markdown file optimized for LLM parsing. Supports optional x402 payment integration.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients.

| Method | Endpoint       | Price    | Description               |
| :----- | :------------- | :------- | :------------------------ |
| `GET`  | `/api/health`  | **Free** | Health check              |

### 2. **Hybrid Endpoints** (`/hybrid`)

These are exposed as both REST endpoints and MCP tools.

| Method/Tool                | Price    | Description                                  |
| :------------------------- | :------- | :------------------------------------------- |
| `GET /hybrid/pricing`      | **Free** | Returns tool pricing configuration           |
| `gitparser_parse_gitbook`  | **Paid** | Convert a GitBook site into Markdown         |
| `gitparser_parse_github`   | **Paid** | Convert a GitHub repo into Markdown (gitingest) |

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

## API Documentation

Once the server is running:

- **Swagger UI**: `http://localhost:8000/docs`
- **MCP endpoint**: `http://localhost:8000/mcp`

## Requirements

- **Python 3.12+**
- **UV** (dependency management)
- **Docker** (optional)

## Setup

1. **Environment Variables**
    ```bash
    # Copy the example environment file
    cp .env.example .env

    # Configure environment for x402, etc. (see .env.example).
    ```

2. **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-gitparser/
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
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-gitparser

# Or use the helper script
./scripts/start-docker.sh --rebuild
```

## Testing

### Unit Tests
```bash
# path: ./mcp-servers/mcp-server-gitparser/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

### E2E Tests

End-to-end tests validate the entire payment flow and API functionality. The tests are organized by pricing mode:

- `@pytest.mark.payment_off` - Tests run when `MCP_GITPARSER_X402_PRICING_MODE=off`
- `@pytest.mark.payment_on` - Tests run when `MCP_GITPARSER_X402_PRICING_MODE=on`

**Setup:**

1. Create `.env.tests` file:
   ```bash
   # Base configuration
   MCP_GITPARSER_TEST_BASE_URL=http://localhost:8110
   MCP_GITPARSER_TEST_TIMEOUT_SECONDS=60

   # For payment tests (optional)
   MCP_GITPARSER_TEST_PRIVATE_KEY=0x...  # Your test wallet private key
   ```

2. Start the server:
   ```bash
   # For payment_off tests
   MCP_GITPARSER_X402_PRICING_MODE=off uv run python -m mcp_server_gitparser --port 8110

   # For payment_on tests
   MCP_GITPARSER_X402_PRICING_MODE=on uv run python -m mcp_server_gitparser --port 8110
   ```

3. Run E2E tests:
   ```bash
   # Run all E2E tests
   uv run pytest tests/e2e/ -v -m e2e

   # Run only pricing_off tests
   uv run pytest tests/e2e/ -v -m "e2e and payment_off"

   # Run only pricing_on tests (requires wallet configuration)
   uv run pytest tests/e2e/ -v -m "e2e and payment_on"
   ```

## x402 Payment Integration

This server supports the [x402 payment protocol](https://github.com/coinbase/unibase/tree/main/x402) for monetizing API endpoints. When enabled, priced endpoints require micropayments in stablecoins (USDC/USDT) across multiple networks.

### Supported Networks

- Base (chain_id: 8453)
- Polygon (chain_id: 137)
- Avalanche (chain_id: 43114)
- SKALE Base (chain_id: 1187947933)
- BNB Chain (chain_id: 56)
- Sei Network (chain_id: 1329)
- Solana

### Configuration

Set these environment variables in your `.env` file:

```bash
# Enable/disable payment enforcement
MCP_GITPARSER_X402_PRICING_MODE=on  # or "off"

# Facilitator URLs (JSON array for multi-chain support)
MCP_GITPARSER_X402_FACILITATOR_URLS='["https://facilitator.payai.network","https://api.x402.unibase.com/v2"]'

# Wallet addresses for receiving payments
MCP_GITPARSER_X402_PAYEE_EVM_ADDRESS=0x...     # For EVM chains (Base, Polygon, etc.)
MCP_GITPARSER_X402_PAYEE_SOLANA_ADDRESS=...    # For Solana (Base58 format)

# Pricing configuration file (optional, defaults to tool_pricing.yaml)
MCP_GITPARSER_X402_PRICING_CONFIG_PATH=tool_pricing.yaml
```

### Pricing Configuration

Prices are configured in `tool_pricing.yaml` using USD amounts that are automatically converted to token amounts:

```yaml
gitparser_parse_gitbook:
  - price_usd: 0.01  # $0.01 per request
    chain_id: 8453
    token_address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
```

For development/testing, use `tool_pricing.dev.yaml` with lower prices (automatically used in Docker dev stage).

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
│       ├── middlewares/
│       │   └── x402_wrapper.py      # x402 payment middleware
│       ├── x402_integration/        # x402 payment integration
│       │   ├── __init__.py          # Public API exports
│       │   ├── config.py            # x402 configuration & pricing
│       │   └── accepted_assets.py   # Blockchain constants & utilities
│       └── gitparser/               # Business logic layer
├── scripts/
├── docs/
├── tests/
│   ├── e2e/                         # End-to-end tests
│   │   ├── config.py                # E2E test configuration
│   │   ├── conftest.py              # Pytest fixtures
│   │   ├── utils.py                 # MCP session utilities
│   │   ├── test_api_routers.py      # API endpoint tests
│   │   └── test_hybrid_routers.py   # Hybrid endpoint tests
│   └── ...                          # Unit tests
├── .env.example
├── Dockerfile
├── pyproject.toml
├── tool_pricing.yaml                # Production pricing
├── tool_pricing.dev.yaml            # Development pricing
└── uv.lock
```
