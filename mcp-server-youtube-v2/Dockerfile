## This dockerfile is a template for all MCP servers
## It can be used as is or edited to fit your needs


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy

# Enable bytecode compilation: longer builds but faster startup
ENV UV_COMPILE_BYTECODE=1

# Install project dependencies using mounted uv.lock (ensure it exists locally)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project itself (done for layer caching optimization)
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# --- Dev stage --- #
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /app/.venv /app/.venv

# Additionally install dev and debug dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --group dev --group debug

# Make container use python installed inside the venv
ENV PATH="/app/.venv/bin:$PATH"

# Create logs directory
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Set log file path
ENV MCP_YOUTUBE__LOGGING__LOG_FILE="/app/logs/mcp_youtube.log"

# Mount point for logs
VOLUME ["/app/logs"]

COPY tool_pricing.yaml .

CMD ["tail", "-f", "/dev/null"]

# --- Production stage --- #
FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY tool_pricing.yaml .

ENV PATH="/app/.venv/bin:$PATH"

# Create logs directory
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Set log file path (logs directory will be created if needed)
ENV MCP_YOUTUBE__LOGGING__LOG_FILE="/app/logs/mcp_youtube.log"

# Mount point for logs
VOLUME ["/app/logs"]

EXPOSE 8002

CMD ["python", "-m", "mcp_server_youtube", "--host", "0.0.0.0", "--port", "8002"]

