#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Foe Be Gone
# Runs the Foe Be Gone application
# ==============================================================================

# Get addon options
CONFIG_PATH=/data/options.json

# Get configuration from Home Assistant
OPENAI_API_KEY=$(bashio::config 'openai_api_key')
OPENAI_MODEL=$(bashio::config 'openai_model')
CAPTURE_ALL_SNAPSHOTS=$(bashio::config 'capture_all_snapshots')
PHASH_THRESHOLD=$(bashio::config 'phash_threshold')

# Set environment variables
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export OPENAI_MODEL="${OPENAI_MODEL}"
export CAPTURE_ALL_SNAPSHOTS="${CAPTURE_ALL_SNAPSHOTS}"
export PHASH_THRESHOLD="${PHASH_THRESHOLD}"

# Set data paths
export DATA_PATH="/data"
export SNAPSHOT_PATH="/share/foe-be-gone/snapshots"
export VIDEO_PATH="/share/foe-be-gone/videos"
export SOUND_PATH="/share/foe-be-gone/sounds"
export DATABASE_URL="sqlite:///data/foe_be_gone.db"

# Create directories
mkdir -p "${SNAPSHOT_PATH}" "${VIDEO_PATH}" "${SOUND_PATH}"

# Log configuration
bashio::log.info "Starting Foe Be Gone..."
bashio::log.info "OpenAI Model: ${OPENAI_MODEL}"
bashio::log.info "Capture All Snapshots: ${CAPTURE_ALL_SNAPSHOTS}"
bashio::log.info "pHash Threshold: ${PHASH_THRESHOLD}"

# Change to app directory
cd /app

# Run database migrations
bashio::log.info "Running database migrations..."
uv run alembic upgrade head

# Start the application
bashio::log.info "Starting Foe Be Gone application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000