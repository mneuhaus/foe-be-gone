"""Standardized API response helpers."""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


def success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response


def error_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "success": False,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response