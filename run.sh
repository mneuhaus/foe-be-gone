#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Foe Be Gone
# Runs the Foe Be Gone application
# ==============================================================================

# Get addon options
CONFIG_PATH=/data/options.json

# Get configuration from Home Assistant
# Note: OpenAI settings are managed through the web interface, not addon config
CAPTURE_ALL_SNAPSHOTS=$(bashio::config 'capture_all_snapshots')
PHASH_THRESHOLD=$(bashio::config 'phash_threshold')
DEV_MODE=$(bashio::config 'dev_mode')

# Set environment variables
export CAPTURE_ALL_SNAPSHOTS="${CAPTURE_ALL_SNAPSHOTS}"
export PHASH_THRESHOLD="${PHASH_THRESHOLD}"
export DEV_MODE="${DEV_MODE}"

# Set data paths
export DATA_PATH="/data"
export SNAPSHOT_PATH="/share/foe-be-gone/snapshots"
export VIDEO_PATH="/share/foe-be-gone/videos"
export SOUND_PATH="/share/foe-be-gone/sounds"
export DATABASE_URL="sqlite:////data/foe_be_gone.db"

# Create directories
mkdir -p "${SNAPSHOT_PATH}" "${VIDEO_PATH}" "${SOUND_PATH}"

# Log configuration
bashio::log.info "Starting Foe Be Gone..."
bashio::log.info "Capture All Snapshots: ${CAPTURE_ALL_SNAPSHOTS}"
bashio::log.info "pHash Threshold: ${PHASH_THRESHOLD}"
bashio::log.info "Dev Mode: ${DEV_MODE}"

# Start SSH server if in dev mode
if [ "${DEV_MODE}" = "true" ]; then
    bashio::log.warning "Development mode enabled - Starting SSH server on port 2222"
    bashio::log.warning "SSH access: root with no password (INSECURE - FOR DEVELOPMENT ONLY)"
    /usr/sbin/sshd -D &
    SSH_PID=$!
    bashio::log.info "SSH server started with PID ${SSH_PID}"
fi

# Change to app directory
cd /app

# Run database migrations
bashio::log.info "Running database migrations..."
python3 -m alembic upgrade head

# Start the application
bashio::log.info "Starting Foe Be Gone application..."
if [ "${DEV_MODE}" = "true" ]; then
    bashio::log.info "Starting with hot-reload enabled for development"
    exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-include '*.py' --reload-include '*.html' --reload-include '*.js'
else
    exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
fi