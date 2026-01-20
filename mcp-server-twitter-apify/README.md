# MCP Twitter Scraper (mcp-twitter-apify)

A production-ready, multi-protocol Twitter scraping service that provides seamless access to Twitter data through REST API, MCP (Model Context Protocol), and x402 payment-enabled endpoints. Built on FastAPI and powered by Apify's `apidojo/twitter-scraper-lite` actor, with intelligent PostgreSQL-backed caching to minimize API costs and improve response times.

## Overview

`mcp-twitter-apify` is a hybrid server that combines three access patterns in a single application:

- **REST API** (`/api/*`, `/hybrid/*`): Traditional HTTP endpoints for direct integration
- **MCP Protocol** (`/mcp`): Model Context Protocol endpoints for AI agent integration via FastMCP
- **x402 Payment Middleware**: Optional pay-per-use functionality for monetized API access

The server intelligently caches Twitter search results in PostgreSQL, dramatically reducing Apify API costs while maintaining data freshness through configurable TTLs per query type.

## Key Features

### 🔍 **Search Capabilities**
- **Topic Search**: Search tweets by keyword/topic with sorting (Latest/Top), verified user filtering, and image-only filtering
- **Profile Search**: Retrieve tweets from specific users with optional date range filtering
- **Profile Latest**: Get the most recent tweets from users without date constraints
- **Batch Operations**: Process multiple profile searches in parallel with error handling
- **Reply Threads**: Fetch conversation threads via conversation IDs

### 💾 **Intelligent Caching**
- **PostgreSQL-Backed Cache**: Persistent, normalized storage of tweets and authors
- **Configurable TTLs**: Different cache durations per query type:
  - Topic (Latest): 15 minutes
  - Topic (Top): 24 hours
  - Profile: 30 minutes
  - Replies: 1 hour
- **Automatic Cache Management**: Deterministic cache keys ensure consistent results
- **Cost Optimization**: Reduces Apify API calls by serving cached results when available

### 🛠️ **Query Management**
- **Query Registry**: Predefined queries for common use cases
- **Custom Queries**: Support for ad-hoc searches with full parameter control
- **Query Types**: Organized by topic, profile, and replies
- **Query Execution**: Run predefined queries by ID with timeout control

### 📊 **Output Formats**
- **Min Format**: Compact JSON with essential tweet data
- **Max Format**: Full tweet metadata including extended fields
- **Normalized Data**: Consistent structure across all endpoints

### 🔐 **Enterprise Features**
- **x402 Payment Integration**: Optional pay-per-use API access via Coinbase Developer Platform
- **Pricing Configuration**: YAML-based tool pricing with validation
- **Admin Endpoints**: Log access and system monitoring
- **Health Checks**: Built-in health monitoring endpoints

### 🚀 **Developer Experience**
- **Interactive Documentation**: Swagger UI and ReDoc for API exploration
- **Docker Support**: Production-ready Docker images with multi-stage builds
- **Comprehensive Testing**: Unit tests, integration tests, and MCP E2E tests
- **Structured Logging**: Separate log files for different components
- **Type Safety**: Full type hints and Pydantic validation

## Architecture

The server uses a hybrid architecture pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  REST Routes (/api/*)  │  Hybrid Routes (/hybrid/*)    │
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

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL (via Docker or local installation)
- Apify account with API token

### Setup

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
   ```

## Database Setup

### Running Postgres with Docker

Start a Postgres container with the default configuration:

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
- Override via env vars in your shell or `.env` if needed
- Tables are created automatically on first connection

**Verify connectivity:**
```bash
docker exec -it mcp-postgres psql -U postgres -d mcp_twitter_apify -c '\dt'
```

**Stop / start later:**
```bash
docker stop mcp-postgres
docker start mcp-postgres
```

### DBeaver Connection

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

## Usage

**⚠️ Important:** Before starting the server, ensure PostgreSQL is running. If you haven't started it yet, run:

```bash
docker run -d --name mcp-postgres \
  -e POSTGRES_DB=mcp_twitter_apify \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -v pgdata_mcp:/var/lib/postgresql/data \
  postgres:15-alpine
```

If the container already exists, start it with:
```bash
docker start mcp-postgres
```

### API Server Mode

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

### Docker Deployment

Build and run the server using Docker:

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

**4. Stop the container:**

```bash
docker stop mcp-twitter-server
docker rm mcp-twitter-server
docker restart mcp-twitter-server
```

**Using Docker Compose:**

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

### API Endpoints

#### Search Endpoints

**Topic Search:**
```bash
POST /api/v1/search/topic
Content-Type: application/json

{
  "topic": "starlink",
  "max_items": 10,
  "sort": "Top",
  "only_verified": false,
  "only_image": false,
  "lang": "en",
  "output_format": "min"
}
```

**Profile Search:**
```bash
POST /api/v1/search/profile
Content-Type: application/json

{
  "username": "elonmusk",
  "max_items": 100,
  "since": "2025-12-01",
  "until": "2025-12-31",
  "lang": "en",
  "output_format": "min"
}
```

**Profile Search (Batch):**
```bash
POST /api/v1/search/profile/batch
Content-Type: application/json

{
  "usernames": ["elonmusk", "jack"],
  "max_items": 100,
  "since": "2025-12-01",
  "until": "2025-12-31",
  "lang": "en",
  "output_format": "min",
  "continue_on_error": true
}
```

**Profile Latest (no date range):**
```bash
POST /api/v1/search/profile/latest
Content-Type: application/json

{
  "username": "elonmusk",
  "max_items": 10,
  "lang": "en",
  "output_format": "min"
}
```

**Profile Latest (Batch):**
```bash
POST /api/v1/search/profile/latest/batch
Content-Type: application/json

{
  "usernames": ["elonmusk", "jack"],
  "max_items": 10,
  "lang": "en",
  "output_format": "min",
  "continue_on_error": true
}
```

**Replies Search:**
```bash
POST /api/v1/search/replies
Content-Type: application/json

{
  "conversation_id": "1728108619189874825",
  "max_items": 50,
  "lang": "en",
  "output_format": "min"
}
```

#### Query Management

**List query types:**
```bash
GET /api/v1/types
```

**List queries:**
```bash
GET /api/v1/queries?query_type=topic
```

**Run predefined query:**
```bash
POST /api/v1/run/{query_id}?timeout_seconds=600
```

#### Health & Info

**Health check:**
```bash
GET /health
```

**API info:**
```bash
GET /
```

## Caching

The service uses Postgres-backed caching to reduce Apify API costs:

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

**How it works:**
1. Request comes in → Generate query key from parameters
2. Check cache → If valid and not expired, return cached results
3. If cache miss → Call Apify API
4. Save results → Store tweets/authors in Postgres with TTL
5. Return results → Serve to API

## Database Schema

The cache uses the following tables:

- `twitter_query_cache`: Cache entries with metadata and TTL
- `twitter_query_cache_items`: Links tweets to query cache entries
- `twitter_tweets`: Normalized tweet data (supports min/max formats)
- `twitter_authors`: Normalized author/user information

Tables are created automatically on first connection.

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
- Server must be running (see [API Server Mode](#api-server-mode))
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

   Or if the server is running on a different port:
   ```bash
   RUN_MCP_E2E=1 MCP_SERVER_URL=http://localhost:8002 uv run pytest tests/test_mcp_tools.py -v
   ```

**What these tests cover:**
- MCP session negotiation and initialization
- Listing available MCP tools
- Calling MCP tools: `mcp_list_types`, `mcp_list_queries`, `mcp_search_topic`, `mcp_search_profile`, `mcp_search_replies`

**Note:** If `APIFY_TOKEN` is not set, tests that make real API calls will be skipped automatically.

## Development

### Project Structure

```
mcp-twitter/
├── src/
│   ├── mcp_twitter/      # Main application package
│   │   ├── config.py     # Configuration
│   │   ├── scraper.py    # Apify scraper wrapper
│   │   └── ...
│   └── db/               # Database package
│       ├── models.py     # SQLAlchemy models
│       └── database.py   # Database operations
├── tests/                # Test suite
├── main.py              # Entry point
└── pyproject.toml       # Project configuration
```

### Logging

Logs are written to:
- Console (stdout)
- `logs/mcp_twitter.log` (main logger)
- `logs/mcp_twitter.api.log` (API logger)
- `logs/mcp_twitter.db.log` (database logger)

Set log level via `LOG_LEVEL` environment variable (default: `INFO`).

## License

Copyright (c) 2025 Xyber Inc.

## Support

For issues and questions, please contact: xymanchick@xyber.inc
