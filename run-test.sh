#!/bin/sh
# Test run script without bashio dependencies

# Read config from options.json
if [ -f /data/options.json ]; then
    CAPTURE_ALL_SNAPSHOTS=$(cat /data/options.json | grep -o '"capture_all_snapshots"[[:space:]]*:[[:space:]]*[^,}]*' | sed 's/.*:[[:space:]]*//')
    PHASH_THRESHOLD=$(cat /data/options.json | grep -o '"phash_threshold"[[:space:]]*:[[:space:]]*[^,}]*' | sed 's/.*:[[:space:]]*//')
fi

# Set environment variables
export CAPTURE_ALL_SNAPSHOTS="${CAPTURE_ALL_SNAPSHOTS}"
export PHASH_THRESHOLD="${PHASH_THRESHOLD}"

# Set data paths
export DATA_PATH="/data"
export SNAPSHOT_PATH="/share/foe-be-gone/snapshots"
export VIDEO_PATH="/share/foe-be-gone/videos"
export SOUND_PATH="/share/foe-be-gone/sounds"
export DATABASE_URL="sqlite:////data/foe_be_gone.db"

# Create directories with proper permissions
mkdir -p "${SNAPSHOT_PATH}" "${VIDEO_PATH}" "${SOUND_PATH}" /data
chmod 777 /data  # Ensure write permissions for testing

# Log configuration
echo "Starting Foe Be Gone..."
echo "Capture All Snapshots: ${CAPTURE_ALL_SNAPSHOTS}"
echo "pHash Threshold: ${PHASH_THRESHOLD}"
echo "Database URL: ${DATABASE_URL}"

# Change to app directory
cd /app

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Start the application
echo "Starting Foe Be Gone application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000