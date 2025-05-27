"""
Routes for viewing application logs
"""

import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

LOG_FILE_PATH = Path("logs/foe_be_gone.log")
MAX_LINES = 1000  # Maximum lines to return at once


@router.get("/logs", response_class=HTMLResponse)
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


@router.get("/api/logs")
async def get_logs(
    lines: int = Query(100, ge=10, le=MAX_LINES),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0)
):
    """Get log entries as JSON"""
    if not LOG_FILE_PATH.exists():
        return {"logs": [], "total": 0, "message": "No log file found"}
    
    try:
        # Read log file
        with open(LOG_FILE_PATH, 'r') as f:
            all_lines = f.readlines()
        
        # Parse log entries
        log_entries = []
        current_entry = None
        
        for line in all_lines:
            # Check if this is a new log entry (starts with timestamp)
            if line.strip() and line[0].isdigit() and ' - ' in line:
                if current_entry:
                    log_entries.append(current_entry)
                
                # Parse the log line
                parts = line.strip().split(' - ', 3)
                if len(parts) >= 4:
                    timestamp_str, module, log_level, message = parts
                    current_entry = {
                        "timestamp": timestamp_str,
                        "module": module,
                        "level": log_level,
                        "message": message
                    }
                else:
                    current_entry = {"raw": line.strip()}
            elif current_entry and "message" in current_entry:
                # Continuation of previous entry (multiline log)
                current_entry["message"] += "\n" + line.rstrip()
            elif current_entry:
                # Continuation of raw entry
                current_entry["raw"] += "\n" + line.rstrip()
        
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
        
        # Reverse to show newest first
        log_entries.reverse()
        
        # Apply pagination
        total = len(log_entries)
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