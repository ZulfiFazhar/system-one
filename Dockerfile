# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies with CPU-only PyTorch wheel to keep image minimal
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --find-links https://download.pytorch.org/whl/cpu

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root system user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/sh -m appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Prepare models directory with proper permissions
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Copy application source and static assets
COPY app/ ./app/
COPY public/ ./public/

USER appuser

EXPOSE 8000

# Lightweight healthcheck using stdlib python without extra curl dependency
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["fastapi", "run", "--port", "8000"]
