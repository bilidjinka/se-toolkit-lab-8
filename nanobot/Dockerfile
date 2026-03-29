# Multi-stage build for nanobot gateway
# Follows the same pattern as backend/Dockerfile

# ---
# Stage 1: Build the application
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads, use system interpreter
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy root workspace files for dependency resolution
COPY --from=workspace pyproject.toml uv.lock /app/

# Copy nanobot-websocket-channel and mcp for workspace packages
COPY --from=workspace nanobot-websocket-channel /app/nanobot-websocket-channel
COPY --from=workspace mcp /app/mcp

# Copy nanobot project file
COPY pyproject.toml /app/nanobot/pyproject.toml
COPY uv.lock /app/nanobot/uv.lock

# Sync nanobot package with workspace dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package nanobot

# Copy nanobot source
COPY . /app/nanobot

# Sync with nanobot source installed (no cache to avoid stale archive issues)
RUN uv sync --frozen --package nanobot

# ---
# Stage 2: Final runtime image
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Accept APP_UID and APP_GID as build args for consistent user IDs
ARG APP_UID=999
ARG APP_GID=999

# Create non-root user with specified IDs
RUN groupadd --system --gid "${APP_GID}" appuser \
    && useradd --system --gid "${APP_GID}" --uid "${APP_UID}" --create-home appuser

# Copy the application from builder
COPY --from=builder --chown=appuser:appuser /app /app

# Place venv in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER appuser

WORKDIR /app

# Run the entrypoint which resolves config and starts nanobot gateway
CMD ["python", "/app/nanobot/entrypoint.py"]
