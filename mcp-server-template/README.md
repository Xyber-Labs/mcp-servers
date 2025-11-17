# MCP Weather Server - Hybrid Template
> **General:** This repository serves as a production-ready template for creating MCP (Model Context Protocol) servers with optional x402 payment integration.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities


### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |
| `GET`  | `/api/admin/logs`     | **Paid**   | Retrieves server logs                  |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method/Tool                 | Price      | Description                         |
| :-------------------------- | :--------- | :---------------------------------- |
| `get_current_weather`       | **Free**   | Gets current weather for a location |
| `get_weather_forecast`      | **Paid**   | Retrieves a multi-day forecast      |

### 3. **MCP-Only Endpoints**

Tools exposed exclusively to AI agents. Not available as REST endpoints.

| Tool                    | Price      | Description                               |
| :---------------------- | :--------- | :---------------------------------------- |
| `geolocate_city`        | **Free**   | Converts a city name to coordinates       |
| `get_weather_analysis`  | **Paid**   | Generates a natural language analysis     |

*Note: Paid endpoints require x402 payment protocol configuration. See `env.example` for details.*

## API Documentation

This server automatically generates OpenAPI documentation. Once the server is running, you can access the interactive API docs at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (for REST endpoints)
- **MCP Inspector**: Use an MCP-compatible client to view available agent tools [http://localhost:8000/docs](http://localhost:8000/mcp)

These interfaces allow you to explore all REST-accessible endpoints, view their schemas, and test them directly from your browser.

## Requirements

- **Python 3.12+**
- **UV** (for dependency management)
- **OpenWeatherMap API key**
- **Docker** (optional, for containerization)

## Setup

1.  **Clone & Configure**
    ```bash
    git clone <repository-url>
    cd mcp-server-template
    cp env.example .env
    # Edit .env and add your WEATHER_API_KEY
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-template/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_weather

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_weather
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-template/
# Basic run
uv run python -m mcp_server_weather

# Or with custom port and host
uv run python -m mcp_server_weather --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-template/
# Build the image
docker build -t mcp-server-weather .

# Run the container
docker run --rm -it -p 8000:8000 --env-file .env mcp-server-weather
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-template/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
mcp-server-template/
├── src/
│   └── mcp_server_weather/
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
│       ├── mcp_routers/             # MCP-Only endpoints
│       ├── middlewares/
│       │   └── x402.py              # x402 payment middleware
│       │
│       └── weather/                 # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           ├── module.py
│           └── errors.py
│
├── tests/
├── .env.example
├── Dockerfile
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
