# Use the main image as base for Home Assistant add-on
ARG BUILD_FROM=ghcr.io/mneuhaus/foe-be-gone:latest
FROM ${BUILD_FROM}

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