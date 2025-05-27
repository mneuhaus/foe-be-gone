#!/usr/bin/env bashio

# Home Assistant specific paths
export DATA_PATH="/data"
export SNAPSHOT_PATH="/data/snapshots"
export VIDEO_PATH="/data/videos"
export SOUND_PATH="/media/sounds"
export DATABASE_URL="sqlite:///${DATA_PATH}/foe_be_gone.db"

# All configuration is now managed through the web interface
export LOG_LEVEL="INFO"

# Ingress configuration
export INGRESS_ENTRY=$(bashio::addon.ingress_entry)
export INGRESS_PORT=$(bashio::addon.port 8000)

# Copy default sounds to media folder if not exists
if [ ! -d "${SOUND_PATH}/crows" ]; then
    bashio::log.info "Copying default sounds to media folder..."
    cp -r /app/public/sounds/* ${SOUND_PATH}/
fi

# Log startup info
bashio::log.info "Starting Foe Be Gone..."
bashio::log.info "Configuration will be managed via web interface"
bashio::log.info "Ingress URL: ${INGRESS_ENTRY}"

# Run database migrations
bashio::log.info "Running database migrations..."
cd /app && uv run alembic upgrade head

# Start the application
bashio::log.info "Starting FastAPI application..."
cd /app && exec uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --root-path="${INGRESS_ENTRY}"