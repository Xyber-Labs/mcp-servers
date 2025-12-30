# MCP Twitter Scraper

A FastAPI-based Twitter scraper service using Apify's `apidojo/twitter-scraper-lite` actor with Postgres-backed caching to reduce API costs.

## Features

- **REST API**: FastAPI-based API with interactive Swagger documentation
- **Database Caching**: Postgres-backed cache to reduce Apify API calls and costs
- **Query Types**: Support for topic searches, profile searches, and reply threads
- **Flexible Output**: Min/max output formats for tweets
- **Query Registry**: Predefined queries with custom query support

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

### API Server Mode

Start the FastAPI server:

```bash
python -m mcp_twitter --serve --host 0.0.0.0 --port 8002
```

The API will be available at:
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc
- **API Root:** http://localhost:8002/

### API Endpoints

#### Search Endpoints

**Topic Search:**
```bash
POST /api/v1/search/topic
Content-Type: application/json

{
  "topic": "starlink",
  "max_items": 50,
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
