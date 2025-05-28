#!/bin/bash
# Toggle between production and development mode

case "$1" in
  start)
    echo "Switching to development mode..."
    
    # Stop production server
    echo "Stopping production server..."
    pkill -f 'uvicorn app.main:app' 2>/dev/null || true
    
    # Wait for port to be released
    sleep 2
    
    # Start development server with hot-reload
    echo "Starting development server with hot-reload..."
    echo "Server will restart automatically when you edit files"
    echo ""
    cd /opt/foe-be-gone
    exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
    ;;
    
  stop)
    echo "Stopping development server..."
    pkill -f 'uvicorn app.main:app'
    
    echo "Restarting production server..."
    cd /opt/foe-be-gone
    exec /run.sh
    ;;
    
  status)
    if pgrep -f "uvicorn.*--reload" > /dev/null; then
      echo "Development mode: ACTIVE (with hot-reload)"
    elif pgrep -f "uvicorn" > /dev/null; then
      echo "Production mode: ACTIVE"
    else
      echo "No server running"
    fi
    ;;
    
  *)
    echo "Usage: /dev-mode.sh {start|stop|status}"
    echo ""
    echo "  start  - Stop production server and start dev server with hot-reload"
    echo "  stop   - Stop dev server and restart production server"
    echo "  status - Show current server mode"
    exit 1
    ;;
esac