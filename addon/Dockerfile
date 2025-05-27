# Multi-architecture support with Home Assistant base images
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and system dependencies
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

# Copy application files
COPY pyproject.toml /app/
COPY app /app/app
COPY alembic.ini /app/
COPY alembic /app/alembic
COPY public /app/public

# Install Python dependencies
RUN uv pip install --system -e .

# Create necessary directories
RUN mkdir -p /data /config /media/sounds data/snapshots

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    HOME_ASSISTANT_ADDON=1

# Copy add-on specific files
COPY addon/run.sh /
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