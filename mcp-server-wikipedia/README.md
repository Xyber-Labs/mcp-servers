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

| Method/Tool                      | Price      | Description                                      |
| :------------------------------- | :--------- | :----------------------------------------------- |
| `GET /hybrid/pricing`            | **Free**   | Returns tool pricing configuration               |
| `search_wikipedia`               | **Free**   | Searches for articles and returns list of titles |
| `get_wikipedia_article`          | **Free**   | Retrieves full content and metadata of an article|
| `get_wikipedia_summary`          | **Free**   | Fetches the summary of an article                |
| `get_wikipedia_sections`         | **Free**   | Lists all section titles in an article           |
| `get_wikipedia_links`            | **Free**   | Lists all internal links within an article       |
| `get_wikipedia_related_topics`   | **Free**   | Finds related topics based on article's links    |

*Note: Paid endpoints require x402 payment protocol configuration. See `.env` file for details.*

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
    # Optional environment variables
    WIKIPEDIA_USER_AGENT="MyCoolAgent/1.0 (https://example.com; my-email@example.com)"
    WIKIPEDIA_LANGUAGE="en"
    LOGGING_LEVEL="info"
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

```bash
# path: ./mcp-servers/mcp-server-wikipedia/
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

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
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py
│       │
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   └── pricing.py
│       │
│       ├── mcp_routers/             # MCP-Only endpoints
│       │   ├── __init__.py
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
│       └── wikipedia/               # Business logic layer
│           ├── __init__.py
│           ├── config.py
│           ├── models.py
│           └── module.py
│
├── tests/
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── README.md
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
