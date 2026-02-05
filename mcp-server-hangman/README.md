# MCP Hangman Server

> **General:** This repository provides an MCP (Model Context Protocol) server for playing a game of Hangman.
> It demonstrates a **hybrid architecture** that exposes functionality through REST APIs, MCP, or both simultaneously.

## Capabilities

### 1. **API-Only Endpoints** (`/api`)

Standard REST endpoints for traditional clients (e.g., web apps, dashboards).

| Method | Endpoint              | Price      | Description                            |
| :----- | :-------------------- | :--------- | :------------------------------------- |
| `GET`  | `/api/health`         | **Free**   | Checks the server's operational status |

### 2. **Hybrid Endpoints** (`/hybrid`)

Accessible via both REST and as MCP tools. Ideal for functionality shared between humans and AI.

| Method | Endpoint               | MCP Tool              | Price    | Description                              |
| :----- | :--------------------- | :-------------------- | :------- | :--------------------------------------- |
| `GET`  | `/hybrid/pricing`      | `hangman_get_pricing` | **Free** | Returns tool pricing configuration       |
| `POST` | `/hybrid/start-game`   | `hangman_start_game`  | **Free** | Starts a new Hangman game                |
| `POST` | `/hybrid/guess-letter` | `hangman_guess_letter`| **Free** | Makes a letter guess in an ongoing game  |

*Note: Paid endpoints require x402 payment protocol configuration. See `.env.example` for details.*

### GameState Object

The `start_game` and `guess_letter` endpoints return a `GameState` object with the following structure:
```json
{
  "player_id": "string",
  "masked_word": "list[str]",
  "remaining_attempts": "int",
  "correct_guesses": "list[str]",
  "incorrect_guesses": "list[str]",
  "status": "string"
}
```

**Fields:**
- `player_id`: Unique identifier for this game session
- `masked_word`: The secret word with unrevealed letters shown as '_'
- `remaining_attempts`: Number of attempts left before losing
- `correct_guesses`: List of correctly guessed letters
- `incorrect_guesses`: List of incorrectly guessed letters
- `status`: Game status ('in_progress', 'won', 'lost')

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
    cd mcp-server-hangman
    # Configure environment for x402, logging, etc. (if needed, see .env.example).
    ```

2.  **Virtual Environment**
    ```bash
    # working directory: ./mcp-servers/mcp-server-hangman/
    uv sync
    ```

## Running the Server

### Using Docker Compose (Recommended)

From the root `mcp-servers` directory, you can run the service for production or development.

```bash
# path: ./mcp-servers
# Run the production container
docker compose up mcp_server_hangman

# Run the development container with hot-reloading
docker compose -f docker-compose.debug.yml up mcp_server_hangman
```

### Locally

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Basic run
uv run python -m mcp_server_hangman

# Or with custom port and host
uv run python -m mcp_server_hangman --port 8000 --reload
```

### Using Docker (Standalone)

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Build the image
docker build -t mcp-server-hangman .

# Run the container
docker run --rm -it -p 8000:8000 mcp-server-hangman
```

## Testing

```bash
# path: ./mcp-servers/mcp-server-hangman/
# Run all tests
uv run pytest
```

## Project Structure

```
mcp-server-hangman/
├── src/
│   └── mcp_server_hangman/
│       ├── __init__.py
│       ├── __main__.py              # Entry point (CLI + uvicorn)
│       ├── app.py                   # Application factory & lifespan
│       ├── config.py                # Settings configuration
│       ├── logging_config.py        # Logging configuration
│       ├── dependencies.py          # FastAPI dependency injection
│       ├── schemas.py               # Pydantic request/response models
│       ├── x402_config.py           # x402 payment configuration
│       │
│       ├── api_routers/             # API-Only endpoints (REST)
│       │   ├── __init__.py
│       │   └── health.py            # Health check endpoint
│       ├── hybrid_routers/          # Hybrid endpoints (REST + MCP)
│       │   ├── __init__.py
│       │   ├── pricing.py           # Tool pricing configuration
│       │   ├── start_game.py        # Start new hangman game
│       │   └── guess_letter.py      # Make letter guess
│       ├── middlewares/
│       │   ├── __init__.py
│       │   └── x402_wrapper.py      # x402 payment middleware
│       │
│       └── hangman/                 # Business logic layer
│           ├── models.py            # Game state models
│           └── module.py            # Core game logic
│
├── tests/
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


