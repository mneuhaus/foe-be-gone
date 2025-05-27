"""URL helpers for handling Home Assistant ingress paths."""

from fastapi import Request
from typing import Optional


def get_base_url(request: Request) -> str:
    """Get the base URL for the application, handling HA ingress paths.
    
    When running as a Home Assistant add-on with ingress, the app is served
    at a path like /api/hassio_ingress/XXXXX/ instead of /
    
    This function detects the ingress path from request headers and returns
    the appropriate base URL.
    """
    # Check for Home Assistant ingress headers
    ingress_path = request.headers.get("X-Ingress-Path", "")
    
    if ingress_path:
        # Remove trailing slash if present
        return ingress_path.rstrip("/")
    
    # Check if we're behind a proxy with a base path
    script_name = request.scope.get("root_path", "")
    if script_name:
        return script_name.rstrip("/")
    
    # Default to empty (root)
    return ""


def url_for(request: Request, name: str, **path_params) -> str:
    """Generate URL with proper base path for the application.
    
    This wraps FastAPI's url_for to handle Home Assistant ingress paths.
    """
    base_url = get_base_url(request)
    
    # Get the URL from FastAPI's url_for
    url = request.url_for(name, **path_params)
    
    # If we have a base URL, prepend it
    if base_url:
        # Get the path portion of the URL
        path = url.path
        return f"{base_url}{path}"
    
    return str(url.path)


def static_url(request: Request, path: str) -> str:
    """Generate URL for static files with proper base path."""
    base_url = get_base_url(request)
    
    # Ensure path starts with /
    if not path.startswith("/"):
        path = f"/{path}"
    
    return f"{base_url}{path}"