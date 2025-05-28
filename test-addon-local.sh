#!/bin/bash
# Test script to validate addon container locally

set -e

echo "🧪 Testing Foe Be Gone addon container locally..."

# Create test directories
mkdir -p test-data test-share/foe-be-gone/{snapshots,videos,sounds}

# Create test options.json
cat > test-data/options.json << EOF
{
  "capture_all_snapshots": false,
  "phash_threshold": 15
}
EOF

# Build the container
echo "🔨 Building container..."
docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bookworm \
  -t foe-be-gone-test \
  .

# Run the container
echo "🚀 Running container..."
docker run -d \
  -v "$(pwd)/test-data:/data" \
  -v "$(pwd)/test-share:/share" \
  -p 8000:8000 \
  -p 2222:22 \
  --name foe-be-gone-test \
  foe-be-gone-test

# Wait for container to start
sleep 3

echo ""
echo "🧪 Container started! Test development features:"
echo ""
echo "1. SSH into container (in another terminal):"
echo "   docker exec -it foe-be-gone-test /bin/bash"
echo ""
echo "2. Initialize development environment:"
echo "   /dev-init.sh"
echo ""
echo "3. Test Claude Code:"
echo "   claude --version"
echo ""
echo "4. Test web interface:"
echo "   curl http://localhost:8000/health"
echo ""
echo "Container logs:"
docker logs foe-be-gone-test

echo ""
echo "Press Enter to stop the container..."
read

docker stop foe-be-gone-test 2>/dev/null
docker rm foe-be-gone-test 2>/dev/null
echo "✅ Test complete"