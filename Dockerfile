# syntax=docker/dockerfile:1
# Standalone Dockerfile for running outside Home Assistant
FROM python:3.11-slim

# Install system dependencies (least likely to change)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc
ENV PATH="/root/.local/bin:${PATH}"

# Verify uv installation
RUN which uv && uv --version

# Set working directory
WORKDIR /app

# Copy only dependency files first (most important for caching)
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies with cache mount for uv
# This caches downloaded packages between builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r pyproject.toml

# Copy application code (most likely to change)
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY public ./public

# Create necessary directories
RUN mkdir -p /data/snapshots /data/videos /data/sounds

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_PATH=/data
ENV SNAPSHOT_PATH=/data/snapshots
ENV VIDEO_PATH=/data/videos
ENV SOUND_PATH=/data/sounds
ENV DATABASE_URL=sqlite:///data/foe_be_gone.db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run database migrations and start the application
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]