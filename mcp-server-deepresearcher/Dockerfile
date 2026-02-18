FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install git for fetching git dependencies (xyber-sdk)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Tels uv to place dependencies source code inside the venv
ENV UV_LINK_MODE=copy

# Enable bytecode compilation: longer builds but faster startup
ENV UV_COMPILE_BYTECODE=1

# Install project dependencies using mounted uv.lock (ensure it exists locally)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Copy application code
COPY src/ /app/src/

# Install only the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    uv pip install --no-deps .

# --- Dev stage --- #
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Copy the application package from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Additionally install dev and debug dependencies without removing the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv pip install --group dev --group debug

# Make container use python installed inside the venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy DEV pricing file (lower prices for testing)
COPY tool_pricing.dev.yaml /app/tool_pricing.yaml

CMD ["tail", "-f", "/dev/null"]

# --- Production stage --- #
FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

# Copy the application package from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy PRODUCTION pricing file (full prices)
COPY tool_pricing.yaml /app/tool_pricing.yaml

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "mcp_server_deepresearcher", "--host", "0.0.0.0", "--port", "8119"]
