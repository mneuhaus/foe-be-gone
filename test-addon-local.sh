#!/bin/bash
# Test script to validate addon container locally

set -e

echo "🧪 Testing Foe Be Gone addon container locally..."

# Create test directories
mkdir -p test-data test-share/foe-be-gone/{snapshots,videos,sounds}

# Create test options.json
cat > test-data/options.json << EOF
{
  "openai_api_key": "${OPENAI_API_KEY:-test-key}",
  "openai_model": "gpt-4o-mini",
  "capture_all_snapshots": false,
  "phash_threshold": 15
}
EOF

# Build the container
echo "🔨 Building container..."
docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.21 \
  -t foe-be-gone-test \
  .

# Run the container
echo "🚀 Running container..."
docker run -it --rm \
  -v "$(pwd)/test-data:/data" \
  -v "$(pwd)/test-share:/share" \
  -p 8000:8000 \
  --name foe-be-gone-test \
  foe-be-gone-test

echo "✅ Test complete"