# MCP Together Image Generation Server

> **General:** This repository contains an MCP server for generating images using the Together AI API.

## Overview

This microservice exposes image generation functionality through the Model Context Protocol (MCP). It uses the Together AI API to generate images from text prompts, with optional support for LoRA models.

## MCP Tools:

1. `generate_image`
    - **Description:** Generates an image based on a text prompt.
    - **Input:**
        - `prompt` (required): The text prompt to generate the image from.
        - `width` (optional): The width of the image. Defaults to 1024.
        - `height` (optional): The height of the image. Defaults to 1024.
        - `steps` (optional): The number of generation steps. Defaults to 28.
        - `guidance_scale` (optional): The guidance scale. Defaults to 3.5.
        - `seed` (optional): The seed for the generation. Defaults to 42.
        - `lora_url` (optional): The URL of the LoRA model to use.
        - `lora_scale` (optional): The scale of the LoRA model. Defaults to 0.9.
        - `refine_prompt` (optional): Whether to refine the prompt using a chat model. Defaults to `False`.
    - **Output:** A base64 encoded PNG image as a string.

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
   ```

2. **Create `.env` File based on `env.example`**:
   Create a `.env` file inside `./mcp-server-together-imgen/`.
   ```dotenv
   # Required environment variables
   TOGETHER_API_KEY="your_together_api_key"
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
│       ├── __main__.py
│       ├── config.py
│       ├── logging_config.py
│       ├── schemas.py
│       ├── server.py
│       └── together_client.py
├── tests/
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT
