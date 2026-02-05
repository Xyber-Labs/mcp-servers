# AAVE MCP Server

A Model Context Protocol (MCP) server that provides real-time Aave v3 market data via a clean, agent-friendly schema. This service queries Aave v3 GraphQL across multiple networks and returns a simplified structure with network overviews, per-reserve summaries, and optional filtering capabilities.

## Capabilities

### API-Only Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Returns the operational status of the server (not exposed to MCP) |

### Hybrid Endpoints (REST + MCP)

| Endpoint | Method | Operation ID | Description |
|----------|--------|--------------|-------------|
| `/hybrid/pricing` | GET | `aave_get_pricing` | Get tool pricing configuration |
| `/hybrid/available-networks` | POST | `aave_get_available_networks` | Returns the list of supported Aave networks |
| `/hybrid/comprehensive-aave-data` | POST | `aave_get_comprehensive_data` | Fetch comprehensive Aave market data with optional filtering |

### MCP-Only Endpoints

None - all MCP tools are now accessible via hybrid endpoints.

## API Documentation

Once the server is running, you can access:
- Interactive API documentation at `http://localhost:8000/docs`
- Alternative API documentation at `http://localhost:8000/redoc`
- MCP endpoint at `http://localhost:8000/mcp`

## Requirements

- Python 3.12+
- UV (dependency management)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-server-aave
```

2. Install dependencies:
```bash
uv sync
```

3. Configure environment:
```bash
cp env.example .env
# Edit .env to suit your environment
```

Environment variables (see `env.example`):
```dotenv
AAVE_API_BASE_URL=https://api.v3.aave.com/graphql
AAVE_TIMEOUT_SECONDS=30
AAVE_MAX_RETRIES=3
AAVE_ENABLE_CACHING=true
AAVE_CACHE_TTL_SECONDS=300
MCP_AAVE_HOST=0.0.0.0
MCP_AAVE_PORT=8000
LOGGING_LEVEL=INFO
```

## Running

Start the server:
```bash
uv run python -m mcp_server_aave
```

The server will be available at `http://localhost:8000` (or the configured host/port).

## Testing

Run tests:
```bash
uv run pytest
```

Lint and format:
```bash
uv run ruff check .
uv run black .
uv run isort .
```

## Project Structure

```
mcp-server-aave/
├── src/
│   └── mcp_server_aave/
│       ├── app.py                 # Main application factory
│       ├── api_routers/           # REST-only endpoints
│       │   ├── __init__.py
│       │   └── health.py          # Health check endpoint
│       ├── hybrid_routers/        # REST + MCP endpoints
│       │   ├── __init__.py
│       │   ├── pricing.py         # Pricing configuration
│       │   ├── available_networks.py    # Network listing
│       │   └── comprehensive_data.py    # Market data
│       ├── middlewares/           # Custom middleware
│       ├── aave.py                # Aave API client
│       ├── schemas.py             # Data models
│       └── x402_config.py         # Payment configuration
├── tests/
├── pyproject.toml
├── env.example
└── README.md
```

## Usage Examples

### Get Available Networks

Returns the list of supported networks as known by the upstream API.

**Input**: None

**Output**: `list[str]`

```python
networks = await get_available_networks()
# ["Ethereum", "Polygon", "Avalanche", "Arbitrum", "Optimism"]
```

### Get Comprehensive Aave Data

Returns a simplified, comprehensive view of Aave data with optional filtering.

**Inputs**:
- `networks` (optional, `list[str]`): Restrict results to specific networks (e.g., ["ethereum", "polygon"])
- `asset_symbols` (optional, `list[str]`): Restrict results to specific token symbols

**Output**: `ComprehensiveAaveData` with the following structure:
- `data: list[NetworkAaveData]`
  - `network: str`
  - `overview: MarketOverview`
    - `total_reserves: int`
    - `total_liquidity_usd: str`
    - `total_variable_debt_usd: str`
    - `utilization_rate: str`
    - `base_currency_info: {symbol: str, decimals: int}`
  - `reserves: list[AssetSummary]`
    - `address: str`
    - `symbol: str`
    - `name: str`
    - `supply_apy: str`
    - `borrow_apy: str`
    - `total_supply: str`
    - `total_debt: str`

**Examples**:

Get all markets:
```python
data = await get_comprehensive_aave_data()
# Access: data.data[0].overview.total_reserves
# Access: data.data[0].reserves[0].symbol
```

Filter by network:
```python
eth = await get_comprehensive_aave_data(networks=["ethereum"])
# Returns single network entry with its reserves
```

Filter by network and asset:
```python
usdc_eth = await get_comprehensive_aave_data(
    networks=["ethereum"],
    asset_symbols=["USDC"]
)
# Returns one network with filtered USDC reserve data
```

## Data Model Notes

- Values are strings to avoid floating point ambiguity and because many LLM clients prefer strings for numeric data
- APYs are variable-rate and can change; do not treat as guarantees
- Raw pool data and separate risk blocks are intentionally omitted to reduce duplication and confusion

## Development

### Docker

Build and run with Docker:
```bash
docker build -t mcp-server-aave .
docker run -p 8000:8000 mcp-server-aave
```

## License

MIT
