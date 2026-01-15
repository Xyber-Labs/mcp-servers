# Scripts

This directory contains helper scripts for running the MCP Deep Researcher Server.

## Scripts

### `start-db.sh`
Starts a local PostgreSQL database container for development.

**Usage:**
```bash
./scripts/start-db.sh
```

**What it does:**
- Creates a PostgreSQL Docker container if it doesn't exist
- Starts the container if it exists but is stopped
- Waits for PostgreSQL to be ready
- Displays connection information

**Container details:**
- Name: `mcp-deep-research-postgres-local`
- Database: `mcp_deep_research_postgres`
- User: `postgres`
- Password: `postgres`
- Port: `5432`

### `start-server.sh`
Starts the MCP Deep Researcher Server locally.

**Usage:**
```bash
# Basic usage (development mode with hot reload)
./scripts/start-server.sh

# Restart the server (stops existing instance first)
./scripts/start-server.sh --restart

# Rebuild dependencies and restart
./scripts/start-server.sh --rebuild

# Production mode (no hot reload)
./scripts/start-server.sh --no-reload

# Custom port
./scripts/start-server.sh --port 9000

# Combine options
./scripts/start-server.sh --rebuild --no-reload --port 9000

# Show help
./scripts/start-server.sh --help
```

**Options:**
- `--restart`: Stop the server if running on the port and restart it
- `--rebuild`: Rebuild dependencies (`uv sync`) and restart (implies `--restart`)
- `--no-reload`: Disable hot reload (production mode)
- `--port PORT`: Specify a custom port (default: 8003)
- `--help, -h`: Show help message

**What it does:**
- Checks if PostgreSQL is running (starts it if not)
- Validates that required tools are installed
- Optionally stops existing server instance
- Optionally rebuilds dependencies
- Starts the server with hot reload enabled (unless `--no-reload`)
- Displays server URLs

**Server endpoints:**
- API: http://localhost:8003
- API Docs: http://localhost:8003/docs
- MCP Endpoint: http://localhost:8003/mcp-server/mcp
- Health Check: http://localhost:8003/health

## Prerequisites

- Docker (for database)
- `uv` package manager
- Python 3.12
- `.env` file with required configuration (see main README)

## Troubleshooting

### Database won't start
- Check if Docker is running: `docker info`
- Check if port 5432 is already in use: `lsof -i :5432`
- View container logs: `docker logs mcp-deep-research-postgres-local`

### Server won't start
- Ensure `.env` file exists with required variables
- Check that all dependencies are installed: `uv sync`
- Verify Python 3.12 is available: `python --version`

### Port conflicts
- Change the port in `start-server.sh` or set `MCP_DEEP_RESEARCHER_PORT` environment variable
- For database, change the port mapping in `start-db.sh`

