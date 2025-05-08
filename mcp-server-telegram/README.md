# MCP Telegram Server

MCP Server for Posting Messages to a Telegram Channel.

## Overview

This server provides an API exposing a single MCP tool, `post_to_telegram`, designed to send messages to a pre-configured Telegram channel using a bot token. It handles interactions with the Telegram Bot API, including text formatting and message length constraints.

## Features

- **Telegram Message Posting**: Utilizes the `post_to_telegram` tool to send messages.
  - **Input**: Accepts a JSON object with a `message` field (string) containing the text to be sent.
  - **Output**: Returns a JSON response indicating success or failure.
- **Telegram API Interaction**:
  - Uses HTTP requests to communicate with the Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`).
  - Sends messages with HTML `parse_mode` by default, with an automatic fallback to no parse mode if HTML parsing fails.
  - Truncates messages exceeding 4000 characters, appending "... [message truncated]" to ensure delivery.
- **Structured Configuration**: Leverages environment variables for secure and flexible setup.
- **API Endpoint**: Provides a standard MCP server endpoint for tool listing and execution.
- **Docker Support**: Includes a `Dockerfile` for easy containerization and deployment.

## Requirements

- Python 3.11+
- A Telegram Bot Token.
- A Telegram Channel Username (e.g., `@mychannel`) or Chat ID.
- `.env` file configured with the necessary environment variables.

## Setup

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd mcp-server-telegram
    ```

2.  **Create and Configure `.env` File**:
    Create a `.env` file in the `mcp-server-telegram` root directory by copying `.env.example` (if provided) or creating a new one. Add the following environment variables:
    ```env
    TELEGRAM_TOKEN="your_bot_token_here"
    TELEGRAM_CHANNEL="your_channel_id_or_@username_here"
    # Optional: Set log level, e.g., LOG_LEVEL="DEBUG"
    ```
    - `TELEGRAM_TOKEN`: Your Telegram Bot API token.
    - `TELEGRAM_CHANNEL`: The target Telegram channel ID (e.g., `-1001234567890`) or username (e.g., `@mychannelname`).

3.  **Install Dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    # Ensure uv is installed (or use pip)
    # python -m pip install uv
    uv pip install -e .
    ```
    Alternatively, using pip:
    ```bash
    # pip install -e '.[dev]' # Include dev dependencies
    pip install -e .
    ```

## Running the Server

To run the server directly (ensure your `.env` file is configured and dependencies are installed):
```bash
python -m src.mcp_server_telegram
# Or, if you have uvicorn installed and prefer to run it that way for development:
# uvicorn src.mcp_server_telegram:server_app --reload --port 8002 --host 0.0.0.0
```
(Note: The exact command might depend on how `__main__.py` and `pyproject.toml` [scripts] are set up. The above assumes `src.mcp_server_telegram` can be run as a module.)

### Using Docker

1.  **Build the Docker Image**:
    ```bash
    docker build -t mcp-server-telegram .
    ```
2.  **Run the Docker Container**:
    Make sure your `.env` file is in the `mcp-server-telegram` directory.
    ```bash
    docker run --rm -it -p 8002:8002 --env-file .env mcp-server-telegram
```

## API Usage

The server exposes MCP-compatible endpoints. The primary tool is `post_to_telegram`.

### Tool: `post_to_telegram`

-   **Description**: Posts a given message to the pre-configured Telegram channel.
-   **Input Schema**:
    ```json
    {
        "message": "str"
    }
    ```
    -   `message` (string, required): The text message content to post.

-   **Example Request (using a generic MCP client)**:
    ```python
    # Assuming 'client' is an initialized MCP client pointing to this server
    tool_input = {"message": "Hello from MCP! This is a <b>test</b> message."}
    result = client.call_tool("post_to_telegram", tool_input)
    print(result)
    ```

-   **Example Success Response**:
    ```json
    [
        {
            "type": "text",
            "text": "Message successfully posted to the Telegram channel."
        }
    ]
    ```

-   **Example Error Response (e.g., validation error)**:
    ```json
    [
        {
            "type": "text",
            "text": "Invalid arguments for tool 'post_to_telegram': ..."
        }
    ]
    ```

## Error Handling

The server includes error handling for:
-   **Configuration Errors**: If `TELEGRAM_TOKEN` or `TELEGRAM_CHANNEL` are missing or invalid (raises `TelegramConfigError`).
-   **Telegram API Errors**: If the Telegram API returns an error (e.g., invalid token, chat not found). Details are logged.
-   **Input Validation Errors**: If the input to `post_to_telegram` does not match the schema.
-   **Network Issues**: Handles request exceptions like timeouts or connection errors when communicating with Telegram.

Logs provide details on these errors to help with troubleshooting.


```bash
# Make sure uv is installed or use pip
# pip install uv
uv pip install -e .
# Or with pip
# pip install -e '.[dev]' # Include dev dependencies
