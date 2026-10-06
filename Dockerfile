# ==============================================================================
# CodeSentinel - Multi-Agent Code Review / QA Automation
# Multi-stage Dockerfile: builder + runtime
# Base image: python:3.13-slim (used for both stages to avoid musl libc issues)
# ==============================================================================

# --------------------------------------------------------------------------
# Stage 1: builder - install dependencies with uv
# --------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and set buffer flushing
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps (curl) and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*
RUN UV_NO_MODIFY_PATH=1 curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

# Copy only dependency manifests first (layer caching optimization)
COPY pyproject.toml uv.lock ./

# Install all dependencies frozen to the lockfile
RUN uv sync --frozen --no-install-project

# --------------------------------------------------------------------------
# Stage 2: runtime - minimal non-root image
# --------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Application directory
WORKDIR /app

# Same Python env settings as builder for consistent runtime behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH" \
    UV_RUN_IN_USER=0

# Copy installed dependencies (uv virtualenv) from builder
COPY --from=builder /app/.venv /app/.venv
# Copy uv binary globally so appuser can execute it
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv

# Copy the rest of the application source code
COPY api/ agents/ core/ graph/ infra/ jenkins/ ./

# Create a non-root user (UID 1000) for running the application
RUN useradd --create-home --uid 1000 --no-log-init appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Health check: verify API responds before considering container healthy
# interval=30s, timeout=10s, start-period=60s (grace for cold start), retries=3
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Expose the API port
EXPOSE 8000

# Entrypoint: run uvicorn under the installed uv environment
ENTRYPOINT ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
