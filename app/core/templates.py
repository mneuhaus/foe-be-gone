"""Shared template configuration with URL helpers."""

from fastapi.templating import Jinja2Templates
from datetime import datetime
import pytz
from app.core.url_helpers import url_for, static_url, get_base_url
from app.core.localization import t, translator

# Create templates instance
templates = Jinja2Templates(directory="app/templates")

# Add URL helpers to template globals
templates.env.globals["url_for"] = url_for
templates.env.globals["static_url"] = static_url
templates.env.globals["get_base_url"] = get_base_url

# Add translation helpers to template globals
templates.env.globals["t"] = t
templates.env.globals["translator"] = translator

def format_datetime_tz(dt: datetime, timezone_str: str = "UTC", format_str: str = "%b %d, %H:%M:%S") -> str:
    """Format datetime with timezone conversion."""
    if dt is None:
        return ""
    
    # Ensure datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    try:
        # Convert to requested timezone
        tz = pytz.timezone(timezone_str)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime(format_str)
    except:
        # Fallback to UTC if timezone is invalid
        return dt.strftime(format_str)

# Add timezone helper to template globals
templates.env.globals["format_datetime_tz"] = format_datetime_tz

# Export configured templates
__all__ = ["templates"]