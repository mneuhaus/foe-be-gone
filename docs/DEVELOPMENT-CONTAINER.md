# Development Container Setup

This guide explains how to set up a development environment inside the Home Assistant addon container.

## Prerequisites

- Home Assistant with Foe Be Gone addon installed
- SSH access to the addon container
- Claude Code installed on your local machine (not in the container)

## Setup Steps

1. **SSH into the container**:
   ```bash
   ssh root@<addon-ip>
   # Password is empty by default
   ```

2. **Initialize development environment**:
   ```bash
   /dev-init.sh
   ```
   This will:
   - Clone the git repository to `/dev-workspace`
   - Install development dependencies
   - Create symlinks for live development
   - Set up git configuration

3. **Switch to development mode**:
   ```bash
   /dev-mode.sh start
   ```
   This stops the production server and starts it with hot-reload enabled.

## Development Workflow

### Using Claude Code (from your local machine)

Since Claude Code runs on your local machine, you'll need to use SSH:

```bash
# On your local machine
claude-code ssh://root@<addon-ip>/dev-workspace
```

### Manual Development

1. **Edit files in the container**:
   ```bash
   cd /dev-workspace
   # Edit files with vi, nano, or your preferred editor
   ```

2. **Changes are automatically reloaded** thanks to:
   - Symlinks from `/dev-workspace/app` to `/app/app`
   - Hot-reload enabled in development mode

3. **Run tests**:
   ```bash
   cd /dev-workspace
   uv run pytest
   ```

### Switching Between Modes

- **Development mode**: `/dev-mode.sh start`
- **Production mode**: `/dev-mode.sh stop`
- **Check status**: `/dev-mode.sh status`

## Important Notes

- Development server runs on port 8000 (same as production)
- Full Home Assistant context is preserved
- Database is at `/data/foe-be-gone.db`
- Logs are in `/app/logs/`
- Changes in `/dev-workspace` are immediately reflected in the running app