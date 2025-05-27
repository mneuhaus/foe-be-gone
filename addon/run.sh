#!/usr/bin/env bashio

# Get configuration from Home Assistant
export OPENAI_API_KEY=$(bashio::config 'openai_api_key')
export DETECTION_INTERVAL=$(bashio::config 'detection_interval')
export MIN_FOE_CONFIDENCE=$(bashio::config 'min_foe_confidence')
export ENABLE_DETERRENT=$(bashio::config 'enable_deterrent')
export DETERRENT_DURATION=$(bashio::config 'deterrent_duration')
export ENABLE_NOTIFICATIONS=$(bashio::config 'enable_notifications')
export LOG_LEVEL=$(bashio::config 'log_level')

# Home Assistant specific paths
export DATA_PATH="/data"
export SNAPSHOT_PATH="/data/snapshots"
export VIDEO_PATH="/data/videos"
export SOUND_PATH="/media/sounds"
export DATABASE_URL="sqlite:///${DATA_PATH}/foe_be_gone.db"

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
bashio::log.info "OpenAI API Key: ${OPENAI_API_KEY:0:10}..."
bashio::log.info "Detection Interval: ${DETECTION_INTERVAL}s"
bashio::log.info "Min Confidence: ${MIN_FOE_CONFIDENCE}"
bashio::log.info "Deterrent Enabled: ${ENABLE_DETERRENT}"
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