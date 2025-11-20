# Tavily MCP Server - System Design Document

## Architecture Overview
Hybrid MCP server exposing Tavily web search through REST APIs, MCP tools, and hybrid endpoints with x402 payment integration.

## System Layers

### 1. Application Layer (`app.py`)
- FastAPI application factory
- Combines REST and MCP capabilities via FastMCP
- Manages lifespan for Tavily service client
- Mounts routers and middleware

### 2. Configuration Layer (`config.py`)
- `AppSettings`: Server configuration (host, port, logging)
- `X402Config`: Payment configuration (facilitator, payee wallet, pricing)
- `PaymentOption`: Pricing model for endpoints
- Environment variable loading with Pydantic Settings
- Pricing YAML file parsing

### 3. Router Layer
- **API Routers** (`api_routers/`):
  - `health.py`: Free health check endpoint
  - `admin.py`: Paid admin logs endpoint
- **Hybrid Routers** (`hybrid_routers/`):
  - `search.py`: Paid web search (REST + MCP)
- **MCP Routers** (`mcp_routers/`):
  - `config.py`: Free utility tool for search configuration

### 4. Middleware Layer (`middlewares/`)
- `x402_wrapper.py`: Payment enforcement middleware
  - Intercepts REST and MCP requests
  - Validates x402 payment headers
  - Verifies payments via facilitator
  - Handles settlement

### 5. Domain Layer (`tavily/`)
- `config.py`: Tavily-specific configuration (API key, search params)
- `models.py`: Domain models (TavilySearchResult)
- `module.py`: Business logic (_TavilyService)
- `errors.py`: Domain-specific exceptions

### 6. Dependency Injection (`dependencies.py`)
- `get_tavily_client()`: Provides Tavily service instance
- Uses Request-scoped dependencies for FastAPI

## Payment Flow

1. Client requests paid endpoint
2. Middleware checks for `X-PAYMENT` header
3. If missing: Returns 402 with payment requirements
4. If present: Decodes and validates payment payload
5. Matches payment against configured options
6. Verifies payment via facilitator (with retries)
7. On success: Processes request and settles payment
8. Returns response with `X-PAYMENT-RESPONSE` header

## Secret Passing Flow

1. Client includes `Tavily-Api-Key` header in request
2. Router extracts header via FastAPI `Header()` dependency
3. Validates header presence (400 if missing)
4. Passes API key to Tavily service
5. Service uses key for upstream Tavily API calls
6. Upstream errors (401) translated to 503 responses

## Integration Points

### Tavily API Integration
- Uses `langchain-tavily` library
- Async search operations with retry logic
- Error handling for API failures
- Result formatting and normalization

### x402 Integration
- Facilitator client for payment verification
- Support for multiple payment options per endpoint
- Network and token validation
- Settlement tracking

## Configuration Strategy

- Environment variables for server and payment settings
- YAML file for endpoint pricing configuration
- Domain-specific configs (Tavily) loaded via Pydantic
- LRU-cached factory functions for singleton services

## Error Handling

- Domain errors (`TavilyApiError`, `TavilyServiceError`) raised from module
- Router layer maps to HTTP status codes
- Middleware handles payment-related errors
- Unknown errors passed through with details preserved

## Testing Strategy

- Unit tests for routers (stubbed clients)
- Integration tests for x402 middleware
- E2E tests for full request flow
- Domain tests for Tavily service logic

