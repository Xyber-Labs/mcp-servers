# MCP Telegram Server

An MCP (Model Context Protocol) server for posting messages to Telegram channels. This server provides both REST API and MCP tool interfaces for sending messages to configured Telegram channels using bot tokens, with support for text formatting and message length constraints.

## Capabilities

### API-Only Endpoints (/api)

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/health` | GET | Returns server operational status | None |

### Hybrid Endpoints (/hybrid)

Available via both REST API (`/hybrid/*`) and MCP protocol (`/mcp`):

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/hybrid/pricing` | GET | Get tool pricing configuration | None |

### MCP-Only Endpoints

Available only through MCP protocol (`/mcp`):

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|------------------|--------|
| `post_to_telegram` | Posts a message to a Telegram channel | `message` (string, 1-4096 chars) | Success/failure message |

**Authentication Headers Required:**
- `X-Telegram-Token`: Your Telegram bot API token
- `X-Telegram-Channel`: The channel ID or username (e.g., @channelname)

## API Documentation

Once the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Requirements

- Python 3.12+
- UV (for dependency management)
- Telegram Bot Token and Channel ID
- Docker (optional, for containerization)

## Setup

1. **Clone the Repository**:
   ```bash
   # path: /path/to/your/projects/
   git clone <repository-url>
   ```

2. **Create `.env` File based on `.env.example`**:
   Create a `.env` file inside `./mcp-server-telegram/`. You must provide your Telegram bot token and channel ID.
   ```dotenv
   # Required environment variables
   TELEGRAM_TOKEN="your_bot_token_here"
   TELEGRAM_CHANNEL="your_channel_id_or_@username"
   ```

3. **Install Dependencies**:
   ```bash
   # path: ./mcp-servers/mcp-server-telegram/
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
docker compose up mcp_server_telegram

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_telegram
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Basic run
uv run python -m mcp_server_telegram

# Or with custom port and host
uv run python -m mcp_server_telegram --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Build the image
docker build -t mcp-server-telegram .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-telegram
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-telegram/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-telegram/
├── src/
│   └── mcp_server_telegram/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
│       │   └── post_to_telegram.py
│       ├── middlewares/             # x402 payment middleware
│       │   ├── __init__.py
│       │   └── x402_wrapper.py
│       │
│       ├── telegram/                # Business logic layer
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── module.py
│       │
│       └── tests/
│           ├── conftest.py
│           ├── test_module.py
│           └── test_server.py
│
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Authentication

The `post_to_telegram` MCP tool requires authentication via HTTP headers:

- **X-Telegram-Token**: Your Telegram bot API token (obtained from [@BotFather](https://t.me/botfather))
- **X-Telegram-Channel**: The target channel ID or username (e.g., `@channelname` or `-1001234567890`)

These credentials must be provided in the MCP tool call headers. The server does not store credentials; they are passed per-request for security.

### Getting Telegram Credentials

1. **Create a Bot**: Message [@BotFather](https://t.me/botfather) on Telegram and use `/newbot` to create a bot
2. **Get Token**: BotFather will provide your bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
3. **Add Bot to Channel**: Add your bot as an administrator to the target channel
4. **Get Channel ID**: Use the channel username (e.g., `@mychannel`) or numeric ID

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

