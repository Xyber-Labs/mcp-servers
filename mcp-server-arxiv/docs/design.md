# ArXiv MCP Server - System Design Document

## Architecture Overview
Hybrid MCP server exposing ArXiv paper search through REST APIs, MCP tools, and hybrid endpoints with x402 payment integration.

## System Layers

### 1. Application Layer (`app.py`)
- FastAPI application factory
- Combines REST and MCP capabilities via FastMCP
- Manages lifespan for ArXiv service client
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
  - `search.py`: Paid paper search with PDF extraction (REST + MCP)
- **MCP Routers** (`mcp_routers/`):
  - `metadata.py`: Free utility tool for paper metadata lookup

### 4. Middleware Layer (`middlewares/`)
- `x402_wrapper.py`: Payment enforcement middleware
  - Intercepts REST and MCP requests
  - Validates x402 payment headers
  - Verifies payments via facilitator
  - Handles settlement

### 5. Domain Layer (`arxiv/`)
- `config.py`: ArXiv-specific configuration (defaults for max_results, max_text_length)
- `models.py`: Domain models (ArxivSearchResult)
- `module.py`: Business logic (_ArxivService)
- `errors.py`: Domain-specific exceptions

### 6. Dependency Injection (`dependencies.py`)
- `get_arxiv_client()`: Provides ArXiv service instance
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

- No external API keys required (ArXiv is public)
- All authentication handled via x402 payment model
- Rate limiting enforced through payment verification

## Integration Points

### ArXiv API Integration
- Uses official `arxiv` Python library
- Async search operations
- Synchronous PDF download (executed in thread pool)
- PyMuPDF for text extraction
- Temporary file management for PDFs

### x402 Integration
- Facilitator client for payment verification
- Support for multiple payment options per endpoint
- Network and token validation
- Settlement tracking

## Configuration Strategy

- Environment variables for server and payment settings
- YAML file for endpoint pricing configuration
- Domain-specific configs (ArXiv) loaded via Pydantic
- LRU-cached factory functions for singleton services

## Error Handling

- Domain errors (`ArxivApiError`, `ArxivServiceError`) raised from module
- Router layer maps to HTTP status codes
- Middleware handles payment-related errors
- PDF processing errors captured in result objects
- Unknown errors passed through with details preserved

## Testing Strategy

- Unit tests for routers (stubbed clients)
- Integration tests for x402 middleware
- E2E tests for full request flow
- Domain tests for ArXiv service logic (including PDF processing)

## Performance Considerations

- PDF downloads and text extraction are CPU/IO intensive
- Async processing with thread pool executors
- Temporary file cleanup after processing
- Configurable max_results and max_text_length limits

