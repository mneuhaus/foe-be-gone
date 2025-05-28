#!/bin/bash
# Local testing script for the containerized development environment

echo "=== Testing Foe Be Gone Container Locally ==="
echo ""

# Build the container
echo "1. Building container..."
docker build -t foe-be-gone:test . || exit 1

echo ""
echo "2. Starting container..."
# Run the container with volume mounts for development
docker run -d \
  --name foe-be-gone-test \
  -p 8000:8000 \
  -p 2222:22 \
  -v "$(pwd)/data:/data" \
  -v "$(pwd)/config:/config" \
  -e TZ="$(date +%Z)" \
  foe-be-gone:test

echo ""
echo "3. Waiting for container to start..."
sleep 5

echo ""
echo "4. Testing SSH access..."
ssh-keygen -f ~/.ssh/known_hosts -R "[localhost]:2222" 2>/dev/null || true
echo "SSH to container: ssh -p 2222 root@localhost"
echo "Password: (empty - just press enter)"

echo ""
echo "5. Testing web interface..."
curl -f http://localhost:8000/health && echo "✅ Health check passed" || echo "❌ Health check failed"

echo ""
echo "=== Container Testing Info ==="
echo "Web interface: http://localhost:8000"
echo "SSH access: ssh -p 2222 root@localhost"
echo "Stop container: docker stop foe-be-gone-test"
echo "Remove container: docker rm foe-be-gone-test"
echo ""
echo "To test Claude Code:"
echo "1. SSH into container: ssh -p 2222 root@localhost"
echo "2. Run: /dev-init.sh"
echo "3. Test: claude --version"
echo ""