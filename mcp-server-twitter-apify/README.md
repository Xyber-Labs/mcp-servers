# MCP Twitter Scraper (mcp-twitter-apify)

A production-ready, multi-protocol Twitter scraping service that provides seamless access to Twitter data through REST API, MCP (Model Context Protocol), and x402 payment-enabled endpoints. Built on FastAPI and powered by Apify's `apidojo/twitter-scraper-lite` actor, with intelligent PostgreSQL-backed caching to minimize API costs and improve response times.

## Capabilities

### API-Only Endpoints (/api)

These endpoints are available only via REST API and are not exposed to MCP:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | API root endpoint with service information |
| `/api/health` | GET | Health check endpoint for monitoring and load balancers |
| `/api/v1/types` | GET | List all available query types with descriptions |
| `/api/v1/queries` | GET | List all available queries, optionally filtered by type |
| `/api/v1/results/{filename}` | GET | Get saved search results (deprecated, use search endpoints) |
| `/api/v1/results` | GET | List cache status (deprecated, results now in Postgres) |

### Hybrid Endpoints (/hybrid)

These endpoints are available via both REST API and can be called by external services:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hybrid/v1/search/topic` | POST | Search tweets by keyword/topic with sorting, verification, and image filters |
| `/hybrid/v1/search/profile` | POST | Search tweets from specific user with optional date range filtering |
| `/hybrid/v1/search/profile/latest` | POST | Get most recent tweets from a user without date constraints |
| `/hybrid/v1/search/replies` | POST | Fetch conversation threads via conversation IDs |
| `/hybrid/v1/search/profile/batch` | POST | Search tweets from multiple users in parallel with error handling |
| `/hybrid/v1/search/profile/latest/batch` | POST | Get latest tweets from multiple users in parallel |
| `/hybrid/v1/run/{query_id}` | POST | Execute a predefined query by ID from the registry |

### MCP-Only Endpoints

These endpoints are exclusively available to AI agents via the MCP protocol at `/mcp`:

| Tool Name | Description |
|-----------|-------------|
| `twitter_search_topic` | Search tweets by topic/keyword with full filtering options (MCP-only tool for AI agents) |

Note: Additional MCP tools (profile search, replies, batch operations) are temporarily disabled but available in the codebase.

## API Documentation

Interactive API documentation is available when the server is running:

- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

### Key Features

- **Topic Search**: Search by keyword/topic with sorting (Latest/Top), verified user filtering, and image-only filtering
- **Profile Search**: Retrieve tweets from specific users with optional date range filtering
- **Profile Latest**: Get the most recent tweets from users without date constraints
- **Batch Operations**: Process multiple profile searches in parallel with error handling
- **Reply Threads**: Fetch conversation threads via conversation IDs
- **Query Registry**: Predefined queries for common use cases with execution by ID
- **Output Formats**:
  - `min` format: Compact JSON with essential tweet data
  - `max` format: Full tweet metadata including extended fields
- **Intelligent Caching**: PostgreSQL-backed cache with configurable TTLs per query type
- **x402 Payment Integration**: Optional pay-per-use API access via Coinbase Developer Platform

## Requirements

- Python 3.12+
- PostgreSQL (via Docker or local installation)
- Apify account with API token
- Docker (optional, for containerized deployment)

## Setup

1. **Clone the repository** (if applicable) or navigate to the project directory

2. **Install dependencies**:
   ```bash
   uv sync --dev
   ```

3. **Configure environment variables**:
   Copy `.example.env` to `.env` and fill in your values:
   ```bash
   cp .example.env .env
   ```

   Required variables:
   ```env
   APIFY_TOKEN=your_apify_token_here
   APIFY_ACTOR_NAME=apidojo/twitter-scraper-lite

   # Database configuration
   DB_NAME=mcp_twitter_apify
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=127.0.0.1
   DB_PORT=5432

   # Optional: Cache TTL overrides (in seconds)
   # CACHE_TTL_TOPIC_LATEST=900      # 15 minutes
   # CACHE_TTL_TOPIC_TOP=86400       # 24 hours
   # CACHE_TTL_PROFILE=1800          # 30 minutes
   # CACHE_TTL_REPLIES=3600          # 1 hour
   ```

4. **Start PostgreSQL**:
   ```bash
   docker run -d --name mcp-postgres \
     -e POSTGRES_DB=mcp_twitter_apify \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -v pgdata_mcp:/var/lib/postgresql/data \
     postgres:15-alpine
   ```

   **Notes:**
   - The app builds `DATABASE_URL` from `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`
   - Tables are created automatically on first connection
   - If container already exists: `docker start mcp-postgres`
   - To stop later: `docker stop mcp-postgres`

5. **Verify database connectivity** (optional):
   ```bash
   docker exec -it mcp-postgres psql -U postgres -d mcp_twitter_apify -c '\dt'
   ```

## Running the Server

### Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: mcp-postgres
    environment:
      POSTGRES_DB: mcp_twitter_apify
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata_mcp:/var/lib/postgresql/data

  mcp-twitter:
    build: .
    container_name: mcp-twitter-server
    ports:
      - "8000:8000"
    environment:
      APIFY_TOKEN: ${APIFY_TOKEN}
      APIFY_ACTOR_NAME: apidojo/twitter-scraper-lite
      DB_NAME: mcp_twitter_apify
      DB_USER: postgres
      DB_PASSWORD: postgres
      DB_HOST: postgres
      DB_PORT: 5432
    depends_on:
      - postgres

volumes:
  pgdata_mcp:
```

Then run:
```bash
docker-compose up -d
```

### Locally

Start the FastAPI server:

```bash
uv run python -m mcp_twitter --host 0.0.0.0 --port 8002
```

Or with hot reload for development:

```bash
uv run python -m mcp_twitter --host 0.0.0.0 --port 8002 --reload
```

The API will be available at:
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc
- **API Root:** http://localhost:8002/

### Docker Standalone

**1. Build the Docker image:**

```bash
docker build -t mcp-twitter-apify:latest .
```

**2. Run the container:**

```bash
docker run -d \
  --name mcp-twitter-server \
  -p 8000:8000 \
  --env-file .env \
  --network host \
  mcp-twitter-apify:latest
```

Or with environment variables directly:

```bash
docker run -d \
  --name mcp-twitter-server \
  -p 8000:8000 \
  -e APIFY_TOKEN=your_token_here \
  -e APIFY_ACTOR_NAME=apidojo/twitter-scraper-lite \
  -e DB_NAME=mcp_twitter_apify \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  --add-host=host.docker.internal:host-gateway \
  mcp-twitter-apify:latest
```

**Note:**
- If PostgreSQL is running in Docker, use `--network host` or connect containers via Docker network
- For Docker Desktop on Mac/Windows, use `host.docker.internal` as `DB_HOST`
- For Linux, use `172.17.0.1` (default Docker bridge IP) or `--network host`

**3. View logs:**

```bash
docker logs -f mcp-twitter-server
```

**4. Stop/restart the container:**

```bash
docker stop mcp-twitter-server
docker rm mcp-twitter-server
docker restart mcp-twitter-server
```

## Testing

Run the full test suite:

```bash
# Install test dependencies (if not already installed)
uv sync --dev

# Run all tests
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_database.py -v
uv run pytest tests/test_api.py -v
uv run pytest tests/test_scraper_cache.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### MCP E2E Tests

The MCP tools tests (`tests/test_mcp_tools.py`) are end-to-end integration tests that require a running server. These tests verify that the MCP transport layer works correctly and that all MCP tools are accessible.

**Prerequisites:**
- Server must be running
- `APIFY_TOKEN` environment variable must be set (for tests that make real API calls)

**Running the MCP E2E tests:**

1. **Start the server** in a separate terminal:
   ```bash
   uv run python -m mcp_twitter --host 0.0.0.0 --port 8003
   ```

2. **Run the E2E tests** (in another terminal):
   ```bash
   RUN_MCP_E2E=1 MCP_SERVER_URL=http://localhost:8003 uv run pytest tests/test_mcp_tools.py -v
   ```

**What these tests cover:**
- MCP session negotiation and initialization
- Listing available MCP tools
- Calling MCP tools: `twitter_search_topic` and other agent-specific endpoints

**Note:** If `APIFY_TOKEN` is not set, tests that make real API calls will be skipped automatically.

## Project Structure

```
mcp-twitter-apify/
├── src/
│   └── mcp_twitter/
│       ├── app.py                    # Main application factory and lifespan management
│       ├── config.py                 # Configuration management
│       ├── api_routers/              # REST-only endpoints
│       │   ├── admin.py              # Health check and root endpoints
│       │   ├── health.py             # Health monitoring endpoints
│       │   └── queries.py            # Query management endpoints
│       ├── hybrid_routers/           # REST + externally callable endpoints
│       │   ├── search.py             # Search endpoints (topic, profile, replies, batch)
│       │   └── pricing.py            # Pricing-related endpoints
│       ├── mcp_routers/              # MCP-only endpoints for AI agents
│       │   └── search.py             # AI agent search tools
│       ├── middlewares/              # Application middlewares
│       │   └── x402_wrapper.py       # x402 payment middleware
│       ├── twitter/                  # Core Twitter scraping logic
│       │   ├── scraper.py            # Apify scraper wrapper with caching
│       │   └── queries.py            # Query definitions and registry
│       └── x402_config.py            # x402 payment configuration
├── db/                               # Database layer
│   ├── models.py                     # SQLAlchemy models for cache
│   └── database.py                   # Database operations
├── tests/                            # Test suite
│   ├── test_api.py                   # API endpoint tests
│   ├── test_database.py              # Database tests
│   ├── test_scraper_cache.py         # Scraper cache tests
│   └── test_mcp_tools.py             # MCP E2E tests
├── logs/                             # Application logs (auto-created)
├── .example.env                      # Example environment configuration
├── Dockerfile                        # Docker image definition
├── docker-compose.yml                # Docker Compose configuration
└── pyproject.toml                    # Project configuration and dependencies
```

## Architecture

The server uses a hybrid architecture pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  API Routes (/api/*)   │  Hybrid Routes (/hybrid/*)     │
│                        │  MCP Routes (/mcp)             │
├─────────────────────────────────────────────────────────┤
│              x402 Payment Middleware (Optional)         │
├─────────────────────────────────────────────────────────┤
│              TwitterScraper (Apify Client)             │
├─────────────────────────────────────────────────────────┤
│         PostgreSQL Cache (Query Results Storage)        │
└─────────────────────────────────────────────────────────┘
```

**Key Components:**
- **FastMCP**: Converts FastAPI routes to MCP protocol endpoints
- **TwitterScraper**: Wraps Apify actor with retry logic and caching
- **Database Layer**: SQLAlchemy models with automatic table creation
- **Query Registry**: Predefined query management system

## Caching

The service uses PostgreSQL-backed caching to reduce Apify API costs:

### Cache Configuration

- **Cache Key**: Deterministic hash of query parameters
- **TTL Configuration**: Different TTLs per query type:
  - Topic (Latest): 15 minutes (default)
  - Topic (Top): 24 hours (default)
  - Profile: 30 minutes (default)
  - Replies: 1 hour (default)

**Customize TTL** via environment variables:
```env
CACHE_TTL_TOPIC_LATEST=900      # 15 minutes
CACHE_TTL_TOPIC_TOP=86400       # 24 hours
CACHE_TTL_PROFILE=1800          # 30 minutes
CACHE_TTL_REPLIES=3600          # 1 hour
```

### Cache Flow

1. Request comes in → Generate query key from parameters
2. Check cache → If valid and not expired, return cached results
3. If cache miss → Call Apify API
4. Save results → Store tweets/authors in Postgres with TTL
5. Return results → Serve to API

### Database Schema

The cache uses the following tables:

- `twitter_query_cache`: Cache entries with metadata and TTL
- `twitter_query_cache_items`: Links tweets to query cache entries
- `twitter_tweets`: Normalized tweet data (supports min/max formats)
- `twitter_authors`: Normalized author/user information

Tables are created automatically on first connection.

### Database Connection (DBeaver)

Use these parameters to connect via DBeaver:

- **Host:** `localhost` (or `127.0.0.1`)
- **Port:** `5432`
- **Database:** `mcp_twitter_apify`
- **Username:** `postgres`
- **Password:** `postgres`

**Connection URL:**
```
jdbc:postgresql://localhost:5432/mcp_twitter_apify
```

## Authentication

### x402 Payment Integration

The server supports optional x402 payment middleware for pay-per-use API access via the Coinbase Developer Platform.

**Configuration:**
- Set `pricing_mode='on'` in x402 configuration
- Define tool pricing in YAML configuration
- Middleware validates pricing configuration against available routes
- Pricing applies to both REST and MCP endpoints

**Features:**
- Per-endpoint pricing configuration
- Automatic price validation
- Request logging and monitoring
- Admin endpoints for log access

See `src/mcp_twitter/x402_config.py` for pricing configuration details.

## Logging

Logs are written to:
- Console (stdout)
- `logs/mcp_twitter.log` (main logger)
- `logs/mcp_twitter.api.log` (API logger)
- `logs/mcp_twitter.db.log` (database logger)

Set log level via `LOG_LEVEL` environment variable (default: `INFO`).

## Contributing

Contributions are welcome. Please ensure all tests pass before submitting pull requests.

## License

Copyright (c) 2025 Xyber Inc.

For issues and questions, please contact: xymanchick@xyber.inc
