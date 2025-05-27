# syntax=docker/dockerfile:1
# Home Assistant Add-on Dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    curl \
    git

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies
# Use PyPI index instead of HA's limited musllinux index
RUN uv pip install --system --break-system-packages \
    --index-url https://pypi.org/simple \
    -r pyproject.toml

# Copy application code
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY public ./public

# Copy addon run script
COPY run.sh /

# Make run script executable
RUN chmod a+x /run.sh

# Create necessary directories
RUN mkdir -p /data /config /media/sounds

# Set labels
LABEL \
    io.hass.name="Foe Be Gone" \
    io.hass.description="AI-powered wildlife detection and deterrent system" \
    io.hass.version="2.0.20" \
    io.hass.type="addon" \
    io.hass.arch="amd64|aarch64"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["/run.sh"]