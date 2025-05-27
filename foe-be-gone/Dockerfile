# syntax=docker/dockerfile:1
# Multi-architecture support with Home Assistant base images
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and system dependencies (least likely to change)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    git \
    curl \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc
ENV PATH="/root/.local/bin:${PATH}"

# Set up Python environment
WORKDIR /app

# Copy only dependency files first (for better caching)
COPY pyproject.toml ./

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# Copy application code (most likely to change)
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY public ./public

# Create necessary directories
RUN mkdir -p /data /config /media/sounds data/snapshots

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    HOME_ASSISTANT_ADDON=1

# Copy add-on specific files
COPY foe-be-gone/run.sh /
RUN chmod a+x /run.sh

# Labels for Home Assistant
LABEL \
    io.hass.name="Foe Be Gone" \
    io.hass.description="AI-powered wildlife detection and deterrent system" \
    io.hass.version="2.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

# Start script
CMD [ "/run.sh" ]