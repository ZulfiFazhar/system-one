# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies with CPU-only PyTorch wheel to keep image minimal
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root system user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/sh -m appuser

# Prepare models directory with proper permissions
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Copy virtual environment from builder with correct ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application source and static assets with correct ownership
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser public/ ./public/

USER appuser

EXPOSE 8000

CMD ["fastapi", "run", "--port", "8000"]
