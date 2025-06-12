"""
Routes for viewing application logs with timezone support
"""

import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.core.templates import templates
from app.services.settings_service import SettingsService
from app.core.session import get_db_session
import pytz

router = APIRouter(tags=["logs"])

# Determine log file path - check multiple possible locations
def get_log_file_path():
    # Check for service installation path (with hyphens - used by launchd stdout) - CURRENT LIVE LOGS
    if os.path.exists("logs/foe-be-gone.log"):
        return Path("logs/foe-be-gone.log")
    # Check for local development path (with underscores - Python logging) - APPLICATION LOGS
    elif os.path.exists("logs/foe_be_gone.log"):
        return Path("logs/foe_be_gone.log")
    # Check for Home Assistant addon path
    elif os.path.exists("/data/logs/foe_be_gone.log"):
        return Path("/data/logs/foe_be_gone.log")
    # Check for system service path
    elif os.path.exists("/var/log/foe_be_gone.log"):
        return Path("/var/log/foe_be_gone.log")
    # Default to /data/logs if /data exists
    elif os.path.exists("/data"):
        return Path("/data/logs/foe_be_gone.log")
    # Otherwise use local logs directory with hyphens (service default)
    else:
        return Path("logs/foe-be-gone.log")

LOG_FILE_PATH = get_log_file_path()
MAX_LINES = 1000  # Maximum lines to return at once


@router.get("/logs", response_class=HTMLResponse, name="view_logs")
async def view_logs(
    request: Request,
    lines: int = Query(100, ge=10, le=MAX_LINES, description="Number of lines to show"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    search: Optional[str] = Query(None, description="Search in log messages")
):
    """View application logs"""
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "current_page": "logs",
            "title": "Application Logs",
            "lines": lines,
            "level": level,
            "search": search
        }
    )


@router.get("/api/logs", tags=["logs"])
async def get_logs(
    lines: int = Query(100, ge=10, le=MAX_LINES),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0)
):
    """Get log entries as JSON"""
    if not LOG_FILE_PATH.exists():
        return {"logs": [], "total": 0, "message": "No log file found"}
    
    # Get user's timezone setting
    with get_db_session() as session:
        settings_service = SettingsService(session)
        user_timezone_str = settings_service.get_timezone()
    
    try:
        user_timezone = pytz.timezone(user_timezone_str)
        print(f"DEBUG: Using timezone: {user_timezone_str}")
    except Exception as e:
        print(f"DEBUG: Timezone error: {e}, using UTC")
        user_timezone = pytz.UTC
    
    try:
        # Read log file
        with open(LOG_FILE_PATH, 'r') as f:
            all_lines = f.readlines()
        
        # Parse log entries
        log_entries = []
        current_entry = None
        
        for line in all_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Check if this is a Python app log entry (starts with timestamp and has ' - ')
            if line_stripped[0].isdigit() and ' - ' in line_stripped and len(line_stripped.split(' - ')) >= 4:
                if current_entry:
                    log_entries.append(current_entry)
                
                # Parse the Python app log line (format: 2025-06-12 02:59:45,363 - module - level - message)
                parts = line_stripped.split(' - ', 3)
                timestamp_str, module, log_level, message = parts
                
                # Convert timestamp from UTC to user's timezone
                try:
                    # Parse the UTC timestamp (format: 2025-06-11 16:19:09,130)
                    if ',' in timestamp_str:
                        # Handle milliseconds format with comma
                        dt_part, ms_part = timestamp_str.split(',')
                        utc_dt = datetime.strptime(dt_part, '%Y-%m-%d %H:%M:%S')
                        # Add milliseconds
                        utc_dt = utc_dt.replace(microsecond=int(ms_part) * 1000)
                    else:
                        # Handle format without milliseconds
                        utc_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Localize to UTC first, then convert to user's timezone
                    utc_dt = pytz.UTC.localize(utc_dt)
                    local_dt = utc_dt.astimezone(user_timezone)
                    
                    # Format back to string
                    local_timestamp_str = local_dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                except Exception as e:
                    # If parsing fails, use original timestamp
                    local_timestamp_str = timestamp_str
                
                current_entry = {
                    "timestamp": local_timestamp_str,
                    "module": module,
                    "level": log_level,
                    "message": message
                }
            
            # Check if this is a uvicorn log entry (starts with log level like "INFO:")
            elif line_stripped.startswith(('DEBUG:', 'INFO:', 'WARNING:', 'ERROR:', 'CRITICAL:')):
                if current_entry:
                    log_entries.append(current_entry)
                
                # Parse uvicorn log line (format: INFO:     127.0.0.1:51209 - "GET / HTTP/1.1" 200 OK)
                parts = line_stripped.split(':', 1)
                if len(parts) >= 2:
                    log_level = parts[0].strip()
                    message = parts[1].strip()
                    
                    # Use current time for uvicorn logs since they don't have timestamps
                    current_time = datetime.now(user_timezone)
                    local_timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                    
                    current_entry = {
                        "timestamp": local_timestamp_str,
                        "module": "uvicorn",
                        "level": log_level,
                        "message": message
                    }
                else:
                    current_entry = {"raw": line_stripped}
            
            # Handle other log formats or continuation lines
            else:
                if current_entry and "message" in current_entry:
                    # Continuation of previous entry (multiline log)
                    current_entry["message"] += "\n" + line.rstrip()
                elif current_entry:
                    # Continuation of raw entry
                    current_entry["raw"] += "\n" + line.rstrip()
                else:
                    # Standalone line without proper format
                    current_entry = {"raw": line_stripped}
        
        # Don't forget the last entry
        if current_entry:
            log_entries.append(current_entry)
        
        # Apply filters
        if level:
            log_entries = [e for e in log_entries if e.get("level") == level.upper()]
        
        if search:
            search_lower = search.lower()
            log_entries = [
                e for e in log_entries 
                if search_lower in e.get("message", "").lower() 
                or search_lower in e.get("raw", "").lower()
            ]
        
        # Keep chronological order (oldest first)
        total = len(log_entries)
        
        # Get the last N entries to show most recent logs
        if offset == 0 and len(log_entries) > lines:
            # When not paginating, show the most recent entries
            log_entries = log_entries[-lines:]
        else:
            # Apply normal pagination
            log_entries = log_entries[offset:offset + lines]
        
        return {
            "logs": log_entries,
            "total": total,
            "offset": offset,
            "lines": lines
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@router.get("/api/logs/stream")
async def stream_logs(
    lines: int = Query(100, ge=10, le=MAX_LINES),
    follow: bool = Query(False, description="Follow log file (tail -f)")
):
    """Stream log entries in real-time"""
    if not LOG_FILE_PATH.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    async def generate():
        # Start with last N lines
        with open(LOG_FILE_PATH, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in last_lines:
                yield f"data: {line.rstrip()}\n\n"
        
        if follow:
            # Continue following the file
            import asyncio
            last_position = LOG_FILE_PATH.stat().st_size
            
            while True:
                await asyncio.sleep(1)
                current_size = LOG_FILE_PATH.stat().st_size
                
                if current_size > last_position:
                    with open(LOG_FILE_PATH, 'r') as f:
                        f.seek(last_position)
                        new_lines = f.read()
                        last_position = current_size
                        
                        for line in new_lines.splitlines():
                            if line.strip():
                                yield f"data: {line}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/api/logs")
async def clear_logs():
    """Clear the log file"""
    if LOG_FILE_PATH.exists():
        # Truncate the file
        with open(LOG_FILE_PATH, 'w') as f:
            f.write("")
        return {"message": "Logs cleared"}
    return {"message": "No log file to clear"}


@router.get("/api/logs/debug")
async def debug_logs():
    """Debug endpoint to check log file location and status"""
    import os
    import pwd
    
    debug_info = {
        "configured_path": str(LOG_FILE_PATH),
        "exists": LOG_FILE_PATH.exists(),
        "absolute_path": str(LOG_FILE_PATH.absolute()),
        "current_working_directory": os.getcwd(),
        "user": pwd.getpwuid(os.getuid()).pw_name,
        "checked_paths": []
    }
    
    # Check all possible locations
    paths_to_check = [
        "/data/logs/foe_be_gone.log",
        "/var/log/foe_be_gone.log",
        "logs/foe_be_gone.log",
        os.path.join(os.getcwd(), "logs/foe_be_gone.log")
    ]
    
    for path in paths_to_check:
        path_info = {
            "path": path,
            "exists": os.path.exists(path),
            "is_file": os.path.isfile(path) if os.path.exists(path) else False,
            "size": os.path.getsize(path) if os.path.exists(path) and os.path.isfile(path) else 0
        }
        debug_info["checked_paths"].append(path_info)
    
    # If log file exists, get some info about it
    if LOG_FILE_PATH.exists():
        stat = os.stat(LOG_FILE_PATH)
        debug_info["file_info"] = {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:]
        }
        
        # Try to read last few lines
        try:
            with open(LOG_FILE_PATH, 'r') as f:
                lines = f.readlines()
                debug_info["total_lines"] = len(lines)
                debug_info["last_lines"] = lines[-5:] if lines else []
        except Exception as e:
            debug_info["read_error"] = str(e)
    
    return debug_info