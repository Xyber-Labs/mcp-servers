# MCP Together Image Generation Server

A microservice for generating images using Together AI's image generation models, exposed through both standard HTTP REST API and the Model Context Protocol (MCP).

## Capabilities

### API-Only Endpoints (/api)

| Endpoint | Method | Description | Operation ID |
|----------|--------|-------------|--------------|
| `/api/images` | POST | Generate an image from a text prompt using Together AI models | `generate_image` |
| `/api/models` | GET | List all available image generation models and their capabilities | `list_models` |

### Hybrid Endpoints (/hybrid)

| Endpoint | Method | Description | Operation ID | Available as MCP Tool |
|----------|--------|-------------|--------------|----------------------|
| `/hybrid/pricing` | GET | Get tool pricing configuration for x402 payment protocol | `together_imgen_get_pricing` | Yes |

### MCP-Only Endpoints

This server uses `fastapi-mcp` to automatically expose API endpoints as MCP tools. The following tools are available via MCP:

- **generate_image**: Generate images from text prompts (from `/api/images`)
- **list_models**: List available models and their capabilities (from `/api/models`)
- **together_imgen_get_pricing**: Get pricing configuration (from `/hybrid/pricing`)

## API Documentation

### POST /api/images

Generate an image from a text prompt using Together AI models.

**Request Body:**
```json
{
  "prompt": "A beautiful landscape painting",
  "model": "black-forest-labs/FLUX.2-dev",
  "width": 1024,
  "height": 1024,
  "steps": 20,
  "guidance_scale": null,
  "seed": null,
  "lora_scale": 0.0,
  "lora_url": null,
  "negative_prompt": null,
  "refine_prompt": false
}
```

**Parameters:**
- `prompt` (required): The text prompt describing the image to generate
- `model` (optional): Model name (e.g., "black-forest-labs/FLUX.2-dev"). Uses environment default if not specified
- `width` (optional): Image width in pixels (64-4096, multiple of 8). Default: 1024
- `height` (optional): Image height in pixels (64-4096, multiple of 8). Default: 1024
- `steps` (optional): Number of generation steps (1-100). Default: 20
- `guidance_scale` (optional): Guidance scale (1.0-30.0). Only supported by FLUX.1-dev and FLUX.2-flex
- `seed` (optional): Random seed for reproducibility. Use null for random
- `lora_scale` (optional): LoRA scale (0.0-1.0). Only for FLUX.1-dev-lora models
- `lora_url` (optional): LoRA model URL. Required if lora_scale > 0
- `negative_prompt` (optional): Negative prompt. Only supported by FLUX.1-dev and older models
- `refine_prompt` (optional): Refine prompt using chat model. Default: false

**Success Response:**
```
Status: 200 OK
Content-Type: image/png (or other image format)
Body: [Binary image data]
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/images \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful landscape painting",
    "model": "black-forest-labs/FLUX.2-dev",
    "width": 1024,
    "height": 1024,
    "steps": 20
  }' --output image.png
```

### GET /api/models

List all available image generation models and their capabilities.

**Success Response:**
```json
{
  "models": [
    {
      "model": "black-forest-labs/FLUX.2-dev",
      "family": "flux2",
      "capabilities": {
        "supports_negative_prompt": false,
        "supports_guidance_scale": false,
        "supports_guidance_param": false,
        "supports_steps": true,
        "supports_lora": false,
        "requires_disable_safety_checker": false,
        "response_format": "url",
        "default_response_format": "url"
      }
    }
  ]
}
```

### GET /hybrid/pricing

Get tool pricing configuration for the x402 payment protocol.

**Success Response:**
```json
{
  "pricing": {
    "generate_image": [
      {
        "chain_id": 8453,
        "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "token_amount": 1000000
      }
    ]
  }
}
```

## Requirements

- Python 3.12+
- UV (for dependency management)
- Together AI API key
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   cd mcp-servers/mcp-server-together-imgen
   ```

2. **Create `.env` File**:
   Create a `.env` file based on `.env.example`:
   ```dotenv
   # Required
   TOGETHER_API_KEY="your_together_api_key"

   # Optional - Server Configuration
   MCP_TOGETHER_IMGEN_HOST="0.0.0.0"
   MCP_TOGETHER_IMGEN_PORT="8000"
   MCP_TOGETHER_IMGEN_HOT_RELOAD="false"

   # Optional - x402 Payment Protocol
   X402_PRICING_MODE="off"  # Set to "on" to enable payment middleware
   X402_PRICING_CONFIG_PATH="./pricing.yml"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-together-imgen/
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
docker compose up mcp_server_together_imgen

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_together_imgen
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-together-imgen/
# Basic run
uv run python -m mcp_server_together_imgen

# Or with custom port and host
uv run python -m mcp_server_together_imgen --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-together-imgen/
# Build the image
docker build -t mcp-server-together-imgen .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-together-imgen
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-together-imgen/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-together-imgen/
├── src/
│   └── mcp_server_together_imgen/
│       ├── __init__.py
│       ├── __main__.py              # Application entry point
│       ├── api_router.py            # API-only endpoints
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py           # x402 pricing endpoint
│       ├── middlewares/             # Custom middleware
│       │   └── x402_wrapper.py      # x402 payment middleware
│       ├── schemas.py               # Pydantic schemas
│       ├── logging_config.py        # Logging configuration
│       ├── x402_config.py          # x402 payment configuration
│       └── together_ai/             # Together AI client
│           ├── __init__.py
│           ├── config.py
│           ├── model_registry.py
│           └── together_client.py
├── tests/
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Authentication

### Together AI API Key

This server requires a Together AI API key to function. The key is configured via the `TOGETHER_API_KEY` environment variable.

### x402 Payment Protocol (Optional)

The server supports the x402 payment protocol for monetizing API access. When enabled, clients must provide payment proofs via HTTP headers to access protected endpoints.

**Configuration:**

1. Set `X402_PRICING_MODE="on"` in your `.env` file
2. Create a `pricing.yml` file defining payment options for each tool:

```yaml
generate_image:
  - chain_id: 8453  # Base Mainnet
    token_address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
    token_amount: 1000000  # 1 USDC (6 decimals)

list_models:
  - chain_id: 8453
    token_address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    token_amount: 100000  # 0.1 USDC
```

3. Set `X402_PRICING_CONFIG_PATH` to point to your pricing configuration file

**Supported Networks:**
- Ethereum Mainnet (chain_id: 1)
- Base Mainnet (chain_id: 8453)
- Base Sepolia (chain_id: 84532)
- Optimism (chain_id: 10)
- Arbitrum One (chain_id: 42161)
- Polygon (chain_id: 137)

**Note:** Token amounts should be specified in the token's smallest unit (e.g., for USDC with 6 decimals, 1 USDC = 1,000,000 token_amount).

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
