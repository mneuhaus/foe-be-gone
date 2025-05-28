#!/bin/bash
# Development environment initialization script

echo "=== Foe Be Gone Development Environment Setup ==="
echo ""

# Check if git repo already exists
if [ -d "/dev-workspace/.git" ]; then
    echo "Git repository already exists in /dev-workspace"
    echo "Pulling latest changes..."
    cd /dev-workspace
    git pull
else
    echo "Cloning repository into /dev-workspace..."
    mkdir -p /dev-workspace
    cd /dev-workspace
    git clone https://github.com/mneuhaus/foe-be-gone.git .
fi

echo ""
echo "Installing development dependencies..."

# Install Python dev dependencies
cd /dev-workspace
uv pip install --system --break-system-packages -r pyproject.toml

# Note: claude-code should be installed on your local machine
echo ""
echo "Note: To use Claude Code, install it on your local machine and use SSH"

# Set up git config for development
echo ""
echo "Setting up git configuration..."
git config --global user.email "developer@foe-be-gone.local"
git config --global user.name "Foe Be Gone Developer"
git config --global init.defaultBranch main

# Create symlinks for live development (optional)
echo ""
echo "Creating development symlinks..."
if [ ! -L "/app/app" ]; then
    mv /app/app /app/app.original 2>/dev/null || true
    ln -s /dev-workspace/app /app/app
    echo "✓ Linked /dev-workspace/app to /app/app"
fi

if [ ! -L "/app/alembic" ]; then
    mv /app/alembic /app/alembic.original 2>/dev/null || true
    ln -s /dev-workspace/alembic /app/alembic
    echo "✓ Linked /dev-workspace/alembic to /app/alembic"
fi

# Create a dev-specific database if needed
if [ ! -f "/data/foe-be-gone-dev.db" ]; then
    echo ""
    echo "Creating development database..."
    cp /data/foe-be-gone.db /data/foe-be-gone-dev.db 2>/dev/null || echo "No production database to copy"
fi

# Display helpful information
echo ""
echo "=== Development Environment Ready ==="
echo ""
echo "Git repository: /dev-workspace"
echo ""
echo "Quick commands:"
echo "  cd /dev-workspace    # Go to development workspace"
echo "  git status           # Check git status"
echo "  uv run pytest        # Run tests"
echo ""
echo "To debug the Home Assistant addon:"
echo "  /dev-mode.sh start   # Switch to development mode with hot-reload"
echo "  /dev-mode.sh stop    # Return to production mode"
echo "  /dev-mode.sh status  # Check current mode"
echo ""
echo "In dev mode:"
echo "  - Server runs with hot-reload enabled"
echo "  - Changes in /dev-workspace/app instantly reload"
echo "  - Full Home Assistant context preserved"
echo "  - Debug logging enabled"
echo ""