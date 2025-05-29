"""Shared template configuration with URL helpers."""

from fastapi.templating import Jinja2Templates
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

# Export configured templates
__all__ = ["templates"]