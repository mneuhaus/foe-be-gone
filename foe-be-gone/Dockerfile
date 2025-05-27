# Use our pre-built main image as base
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.21
FROM mneuhaus/foe-be-gone:latest AS app

# Use Home Assistant base image for the addon
FROM ${BUILD_FROM}

# Install runtime dependencies only
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    bash

# Copy the entire application from our pre-built image
COPY --from=app /app /app
COPY --from=app /root/.local /root/.local

# Set up environment
WORKDIR /app
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV HOME_ASSISTANT_ADDON=1

# Copy add-on specific files
COPY run.sh /
RUN chmod a+x /run.sh

# Create necessary directories
RUN mkdir -p /data /config /media/sounds

# Labels for Home Assistant
LABEL \
    io.hass.name="Foe Be Gone" \
    io.hass.description="AI-powered wildlife detection and deterrent system" \
    io.hass.version="2.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

# Start script
CMD [ "/run.sh" ]