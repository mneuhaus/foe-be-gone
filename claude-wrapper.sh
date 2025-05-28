#!/bin/bash
# Wrapper script for claude-code to work on Alpine Linux
# Alpine's env doesn't support -S flag, so we work around it

# Find the actual claude-code binary
CLAUDE_BIN=$(npm bin -g)/claude-code

# Execute it directly with node
exec node "$CLAUDE_BIN" "$@"