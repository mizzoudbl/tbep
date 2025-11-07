FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_CACHE_DIR=/root/.cache/uv/python

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

LABEL org.opencontainers.image.source="https://github.com/mizzoudbl/tbep"

# Use exec form for CMD and avoid unnecessary quotes
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]