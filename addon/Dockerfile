ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:15.0.1
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    ffmpeg \
    python3-dev \
    build-base \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Copy add-on specific files
COPY addon/run.sh /
RUN chmod a+x /run.sh

# Create necessary directories
RUN mkdir -p /data/snapshots /data/videos /data/sounds

# Labels
LABEL \
    io.hass.name="Foe Be Gone" \
    io.hass.description="AI-powered wildlife detection and deterrent system" \
    io.hass.version="2.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"

# Start script
CMD [ "/run.sh" ]