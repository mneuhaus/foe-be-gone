# Home Assistant Add-on Architecture

## Overview

To package Foe Be Gone as a Home Assistant add-on, we need to create specific configuration files and structure the project appropriately.

## Required Files

### 1. config.yaml
The main configuration file that defines the add-on metadata, requirements, and options.

### 2. Dockerfile
Defines how to build the Docker container for the add-on.

### 3. run.sh
The script that starts the application when the add-on container runs.

### 4. apparmor.txt (optional)
Security profile for the add-on.

### 5. logo.png / icon.png
Visual assets for the add-on store.

## Structure

```
foe-be-gone-addon/
├── config.yaml          # Add-on configuration
├── Dockerfile           # Container build instructions
├── run.sh              # Startup script
├── apparmor.txt        # Security profile
├── logo.png            # 256x256 logo
├── icon.png            # 128x128 icon
├── DOCS.md             # Documentation
├── CHANGELOG.md        # Version history
└── app/                # Application code
    └── ... (existing project structure)
```

## Integration Points

### 1. Home Assistant API
- Use supervisor API for configuration
- Access Home Assistant entities
- Send notifications through HA

### 2. Ingress Support
- Enable ingress for seamless UI integration
- No separate port configuration needed

### 3. Configuration
- Map HA config to app settings
- Use options.json for dynamic config

### 4. Persistence
- Store data in /data (persisted)
- Store cache in /tmp (ephemeral)

## Environment Variables

The add-on will have access to:
- `SUPERVISOR_TOKEN` - For API access
- `HASSIO_TOKEN` - Legacy token
- Options from config as env vars

## Next Steps

1. Create config.yaml with proper schema
2. Build multi-arch Docker image
3. Set up ingress routing
4. Map HA media folders
5. Integrate with HA notifications