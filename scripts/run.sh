#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Foe Be Gone
# Runs the Foe Be Gone application
# ==============================================================================

# Get addon options
CONFIG_PATH=/data/options.json

# Get configuration from Home Assistant
# Note: OpenAI settings are managed through the web interface, not addon config
SNAPSHOT_CAPTURE_LEVEL=$(bashio::config 'snapshot_capture_level')
PHASH_THRESHOLD=$(bashio::config 'phash_threshold')
DEV_MODE=$(bashio::config 'dev_mode')

# Set environment variables
export SNAPSHOT_CAPTURE_LEVEL="${SNAPSHOT_CAPTURE_LEVEL}"
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
bashio::log.info "Snapshot Capture Level: ${SNAPSHOT_CAPTURE_LEVEL} (0=Foe Deterred, 1=AI Detection, 2=Threshold Crossed, 3=All)"
bashio::log.info "pHash Threshold: ${PHASH_THRESHOLD}"
bashio::log.info "Dev Mode: ${DEV_MODE}"

# Start SSH server if in dev mode
if [ "${DEV_MODE}" = "true" ]; then
    bashio::log.warning "Development mode enabled - Starting SSH server on port 2222"
    bashio::log.warning "SSH access: root with no password (INSECURE - FOR DEVELOPMENT ONLY)"
    /usr/sbin/sshd -D &
    SSH_PID=$!
    bashio::log.info "SSH server started with PID ${SSH_PID}"
    
    # Create development directories if they don't exist
    mkdir -p /share/foe-be-gone-dev/dev-workspace
    mkdir -p /share/foe-be-gone-dev/gh-config
    mkdir -p /share/foe-be-gone-dev/claude-config
    
    # Create symlinks for development tools
    bashio::log.info "Setting up development environment symlinks..."
    mkdir -p /root/.config
    ln -sfn /share/foe-be-gone-dev/dev-workspace /dev-workspace
    ln -sfn /share/foe-be-gone-dev/gh-config /root/.config/gh
    ln -sfn /share/foe-be-gone-dev/claude-config /root/.claude
    if [ -f /share/foe-be-gone-dev/claude.json ]; then
        ln -sfn /share/foe-be-gone-dev/claude.json /root/.claude.json
    fi
    
    # Initialize dev workspace if not already done
    if [ ! -f "/var/lib/foe-be-gone/dev-workspace/.initialized" ]; then
        bashio::log.info "Initializing development workspace..."
        /opt/foe-be-gone/scripts/dev-init.sh
        touch /var/lib/foe-be-gone/dev-workspace/.initialized
        bashio::log.info "Development workspace initialized"
    else
        bashio::log.info "Development workspace already initialized"
    fi
fi

# Change to application directory
cd /opt/foe-be-gone

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