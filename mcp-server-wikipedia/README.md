# MCP Wikipedia Server

> **General:** This repository implements an MCP (Model Context Protocol) server for Wikipedia search and content retrieval functionality. It demonstrates a **hybrid architecture** that exposes Wikipedia functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                      | Price (Production) | Price (Dev)    | Description                                      |
| :------------------------------- | :----------------- | :------------- | :----------------------------------------------- |
| `GET /hybrid/pricing`            | **Free**           | **Free**       | Returns tool pricing configuration               |
| `search_wikipedia`               | **$0.01**          | **$0.00001**   | Searches for articles and returns list of titles |
| `get_article`                    | **$0.01**          | **$0.00001**   | Retrieves full content and metadata of an article|
| `get_summary`                    | **$0.01**          | **$0.00001**   | Fetches the summary of an article                |
| `get_sections`                   | **$0.01**          | **$0.00001**   | Lists all section titles in an article           |
| `get_links`                      | **$0.01**          | **$0.00001**   | Lists all internal links within an article       |
| `get_related_topics`             | **$0.01**          | **$0.00001**   | Finds related topics based on article's links    |

**Pricing Notes:**
- Production prices are defined in `tool_pricing.yaml`
- Development prices are defined in `tool_pricing.dev.yaml` (used in dev Docker stage)
- Pricing can be disabled by setting `MCP_WIKIPEDIA_X402_PRICING_MODE=off`
- Paid endpoints support payment on 7 blockchain networks: Base, Polygon, Avalanche, SKALE Base, BNB Chain, Sei Network, and Solana
- See [x402 Payment Configuration](#x402-payment-configuration) section for setup details

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
    cd mcp-server-wikipedia
    # Optionally create a .env file for custom configuration
    ```

2.  **Create `.env` File (Optional)**:
    Create a `.env` file inside `./mcp-server-wikipedia/`. It is highly recommended to set a descriptive `WIKIPEDIA_USER_AGENT`.
    ```dotenv
    # Wikipedia Configuration
    WIKIPEDIA_USER_AGENT="MyCoolAgent/1.0 (https://example.com; my-email@example.com)"
    WIKIPEDIA_LANGUAGE="en"
    LOGGING_LEVEL="info"

    # x402 Payment Configuration (optional)
    MCP_WIKIPEDIA_X402_PRICING_MODE=off
    # MCP_WIKIPEDIA_X402_FACILITATOR_URLS='["https://facilitator.payai.network"]'
    # MCP_WIKIPEDIA_X402_PAYEE_EVM_ADDRESS=0x...
    # MCP_WIKIPEDIA_X402_PAYEE_SOLANA_ADDRESS=...
    ```

3.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-wikipedia/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_wikipedia

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_wikipedia
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Basic run
uv run python -m mcp_server_wikipedia

# Or with custom port and host
uv run python -m mcp_server_wikipedia --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Build the image
docker build -t mcp-server-wikipedia .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-wikipedia
```

## Testing

### Unit Tests

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Run all unit tests
uv run pytest tests/unit/

# Run with verbose output
uv run pytest tests/unit/ -v
```

### E2E Tests

The E2E tests validate the complete server functionality including REST endpoints, MCP protocol, and x402 payment integration.

**Setup:**
1. Copy `tests/.env.tests.example` to `tests/.env.tests`
2. Configure test environment variables:
   ```dotenv
   MCP_WIKIPEDIA_TEST_BASE_URL=http://localhost:8110
   MCP_WIKIPEDIA_TEST_TIMEOUT_SECONDS=60
   # For payment tests (optional):
   # MCP_WIKIPEDIA_TEST_PRIVATE_KEY=0x...
   ```

**Run E2E Tests:**
```bash
# path: ./mcp-servers/mcp-server-wikipedia/

# Run all E2E tests (requires server running at TEST_BASE_URL)
uv run pytest tests/e2e/ -v

# Run only smoke tests (basic functionality, no payment)
uv run pytest tests/e2e/ -v -m "smoke"

# Run tests when pricing is OFF (default mode)
uv run pytest tests/e2e/ -v -m "payment_off"

# Run tests with payment enabled (requires private key)
uv run pytest tests/e2e/ -v -m "payment_on"

# Run tests without payment (should get 402 responses)
uv run pytest tests/e2e/ -v -m "no_payment"

# Run tests with actual x402 payments
uv run pytest tests/e2e/ -v -m "with_payment"
```

**Test Coverage:**
- API-only endpoints: `/api/health`
- Hybrid endpoints: All 6 priced Wikipedia endpoints
- Payment scenarios: pricing_off, no_payment, with_payment
- Schema validation: All responses validated against Pydantic models

## x402 Payment Configuration

This server supports the [x402 payment protocol](https://x402.org) for monetizing API endpoints. Payment can be made on multiple blockchain networks using stablecoins (USDC).

### Supported Networks

- **Base** (chain_id: 8453) - USDC
- **Polygon** (chain_id: 137) - USDC
- **Avalanche** (chain_id: 43114) - USDC
- **SKALE Base** (chain_id: 1187947933) - Bridged USDC
- **BNB Chain** (chain_id: 56) - XUSD (Wrapped USDC)
- **Sei Network** (chain_id: 1329) - Native USDC
- **Solana** - USDC (SPL Token)

### Configuration

Set these environment variables in your `.env` file:

```dotenv
# Enable/disable payment enforcement
MCP_WIKIPEDIA_X402_PRICING_MODE=on

# Facilitator URL(s) - JSON array format for multi-chain support
MCP_WIKIPEDIA_X402_FACILITATOR_URLS='["https://facilitator.payai.network","https://api.x402.unibase.com/v2"]'

# Payee addresses for receiving payments
MCP_WIKIPEDIA_X402_PAYEE_EVM_ADDRESS=0x1234...  # For EVM chains (Base, Polygon, Avalanche, SKALE, BNB, Sei)
MCP_WIKIPEDIA_X402_PAYEE_SOLANA_ADDRESS=ABC...  # For Solana

# Path to pricing configuration (default: tool_pricing.yaml)
# MCP_WIKIPEDIA_X402_PRICING_CONFIG_PATH=tool_pricing.yaml
```

### Pricing Files

- **`tool_pricing.yaml`**: Production pricing ($0.01 per request)
- **`tool_pricing.dev.yaml`**: Development pricing ($0.00001 per request)

The dev pricing file is automatically used when running the dev Docker stage.

### Testing Payments

To test x402 payments locally:

1. Set `MCP_WIKIPEDIA_X402_PRICING_MODE=on`
2. Configure facilitator URL and payee addresses
3. Use an x402-compatible client or run E2E tests with `MCP_WIKIPEDIA_TEST_PRIVATE_KEY`

## Project Structure

```
mcp-server-wikipedia/
├── src/
│   └── mcp_server_wikipedia/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── logging_config.py        # Logging configuration
│       ├── schemas.py               # Pydantic request/response models
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   ├── pricing.py
│       │   ├── search.py
│       │   ├── article.py
│       │   ├── summary.py
│       │   ├── sections.py
│       │   ├── links.py
│       │   └── related.py
│       │
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       ├── x402_integration/        # x402 payment configuration
│       │   ├── __init__.py
│       │   ├── config.py            # x402 settings and pricing loader
│       │   └── accepted_assets.py   # Network and asset definitions
│       │
│       └── wikipedia/               # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           └── module.py
│
├── tests/
│   ├── e2e/                         # End-to-end integration tests
│   │   ├── config.py
│   │   ├── conftest.py
│   │   ├── utils.py
│   │   ├── test_api_routers.py
│   │   └── test_hybrid_routers.py
│   ├── unit/                        # Unit tests
│   └── .env.tests.example
│
├── .env.example
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── README.md
├── tool_pricing.yaml                # Production pricing
├── tool_pricing.dev.yaml            # Development pricing
└── uv.lock
```

## Contributing

1.  Fork the repository
2.  Create your feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

This project is licensed under the MIT License.
