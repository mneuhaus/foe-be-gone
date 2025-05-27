# Standalone Dockerfile for running outside Home Assistant
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc
ENV PATH="/root/.local/bin:${PATH}"

# Verify uv installation
RUN which uv && uv --version

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

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