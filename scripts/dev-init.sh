#!/bin/bash
# Development environment initialization script

echo "=== Foe Be Gone Development Environment Setup ==="
echo ""

# Check if git repo already exists
if [ -d "/var/lib/foe-be-gone/dev-workspace/.git" ]; then
    echo "Git repository already exists in /var/lib/foe-be-gone/dev-workspace"
    echo "Pulling latest changes..."
    cd /var/lib/foe-be-gone/dev-workspace
    git pull
else
    echo "Cloning repository into /var/lib/foe-be-gone/dev-workspace..."
    mkdir -p /var/lib/foe-be-gone/dev-workspace
    cd /var/lib/foe-be-gone/dev-workspace
    git clone https://github.com/mneuhaus/foe-be-gone.git .
fi

echo ""
echo "Installing development dependencies..."

# Install GitHub CLI (gh)
echo "Installing GitHub CLI..."
if ! command -v gh &> /dev/null; then
    (type -p wget >/dev/null || (apt update && apt-get install wget -y)) \
        && mkdir -p -m 755 /etc/apt/keyrings \
        && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        && cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
        && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && apt update \
        && apt install gh -y
    echo "✓ GitHub CLI installed"
else
    echo "✓ GitHub CLI already installed: $(gh --version | head -n1)"
fi

# Install Python dev dependencies
cd /var/lib/foe-be-gone/dev-workspace
uv pip install --system --break-system-packages -r pyproject.toml

# Claude Code is now installed globally
echo ""
echo "Claude Code installed: $(which claude || echo 'installation pending')"

# Set up git config for development
echo ""
echo "Setting up git configuration..."
git config --global user.email "developer@foe-be-gone.local"
git config --global user.name "Foe Be Gone Developer"
git config --global init.defaultBranch main

# Create symlinks for live development (optional)
echo ""
echo "Creating development symlinks..."
if [ ! -L "/opt/foe-be-gone/app" ]; then
    mv /opt/foe-be-gone/app /opt/foe-be-gone/app.original 2>/dev/null || true
    ln -s /var/lib/foe-be-gone/dev-workspace/app /opt/foe-be-gone/app
    echo "✓ Linked dev-workspace/app to application directory"
fi

if [ ! -L "/opt/foe-be-gone/alembic" ]; then
    mv /opt/foe-be-gone/alembic /opt/foe-be-gone/alembic.original 2>/dev/null || true
    ln -s /var/lib/foe-be-gone/dev-workspace/alembic /opt/foe-be-gone/alembic
    echo "✓ Linked dev-workspace/alembic to application directory"
fi

# Create a dev-specific database if needed
if [ ! -f "/data/foe-be-gone-dev.db" ]; then
    echo ""
    echo "Creating development database..."
    cp /data/foe-be-gone.db /data/foe-be-gone-dev.db 2>/dev/null || echo "No production database to copy"
fi

# Configure zsh as default shell
echo ""
echo "Setting zsh as default shell..."
chsh -s /bin/zsh

# Display helpful information
echo ""
echo "=== Development Environment Ready ==="
echo ""
echo "Git repository: /var/lib/foe-be-gone/dev-workspace (symlinked to /dev-workspace)"
echo ""
echo "Quick commands:"
echo "  cd /dev-workspace    # Go to development workspace"
echo "  claude .             # Start Claude Code in workspace"
echo "  git status           # Check git status"
echo "  gh pr create         # Create pull request"
echo "  gh pr list           # List pull requests"
echo "  uv run pytest        # Run tests"
echo "  foe-dev-mode start   # Start development mode"
echo ""
echo "To debug the Home Assistant addon:"
echo "  foe-dev-mode start   # Switch to development mode with hot-reload"
echo "  foe-dev-mode stop    # Return to production mode"
echo "  foe-dev-mode status  # Check current mode"
echo ""
echo "In dev mode:"
echo "  - Server runs with hot-reload enabled"
echo "  - Changes in /dev-workspace/app instantly reload"
echo "  - Full Home Assistant context preserved"
echo "  - Debug logging enabled"
echo ""