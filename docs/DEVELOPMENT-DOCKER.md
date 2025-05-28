# Development with Docker

## Quick Start

To run Foe Be Gone with persistent development volumes:

```bash
# Start with development volumes
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Access the container
docker-compose -f docker-compose.dev.yml exec foe-be-gone bash
```

## Directory Structure

Following Linux FHS standards:
- `/opt/foe-be-gone/` - Main application code
- `/var/lib/foe-be-gone/dev-workspace/` - Development git repository
- `/var/lib/foe-be-gone/data/` - Application data
- `/usr/local/bin/` - User commands (foe-dev-mode, foe-dev-init)
- `/opt/foe-be-gone/scripts/` - Application scripts

Compatibility symlinks:
- `/app` → `/opt/foe-be-gone`
- `/dev-workspace` → `/var/lib/foe-be-gone/dev-workspace`
- `/data` → `/var/lib/foe-be-gone/data`

## Persistent Volumes

The development docker-compose file creates the following persistent volumes:

- `foe-be-gone-dev-workspace` - Your git repository clone at `/var/lib/foe-be-gone/dev-workspace`
- `foe-be-gone-claude-config` - Claude configuration at `/root/.config`
- `foe-be-gone-claude-cache` - Claude cache at `/root/.claude`
- `foe-be-gone-claude-settings` - Claude settings at `/root/.claude.json`

These volumes persist between container restarts, preserving your:
- Git repository and changes
- Claude Code configuration
- GitHub CLI authentication
- Development environment setup

## Environment Variables

Set `DEV_MODE=true` to enable:
- Auto-initialization of dev workspace on first start
- SSH server on port 2222
- Hot-reload mode for the application

## Development Workflow

1. **First Time Setup**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```
   The container will automatically initialize the dev workspace on first run.

2. **Access the Container**
   ```bash
   docker-compose -f docker-compose.dev.yml exec foe-be-gone bash
   cd /dev-workspace
   claude .
   ```

3. **GitHub CLI Authentication**
   ```bash
   # Inside the container
   gh auth login
   ```
   Your authentication will persist in the claude-config volume.

4. **Making Changes**
   - Edit code in `/dev-workspace`
   - Use `foe-dev-mode start` for hot-reload
   - Changes persist in the dev-workspace volume

5. **Clean Restart**
   To reset everything:
   ```bash
   docker-compose -f docker-compose.dev.yml down -v
   docker-compose -f docker-compose.dev.yml up -d
   ```

## Volume Management

List volumes:
```bash
docker volume ls | grep foe-be-gone
```

Inspect a volume:
```bash
docker volume inspect foe-be-gone-dev-workspace
```

Remove all dev volumes (careful!):
```bash
docker volume rm foe-be-gone-dev-workspace foe-be-gone-claude-config foe-be-gone-claude-cache foe-be-gone-claude-settings
```