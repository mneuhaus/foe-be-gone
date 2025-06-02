"""API endpoints for settings management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

from app.core.database import get_session
from app.services.settings_service import SettingsService

router = APIRouter()


class SettingUpdate(BaseModel):
    """Model for updating a setting."""
    value: str


@router.get("/api/settings/{key}")
def get_setting(key: str, session: Session = Depends(get_session)):
    """Get a specific setting value."""
    service = SettingsService(session)
    value = service.get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"key": key, "value": value}


@router.put("/api/settings/{key}")
def update_setting(key: str, update: SettingUpdate, session: Session = Depends(get_session)):
    """Update a specific setting value."""
    service = SettingsService(session)
    service.set_setting(key, update.value)
    return {"key": key, "value": update.value}


@router.put("/api/settings/deterrents/toggle")
def toggle_deterrents(session: Session = Depends(get_session)):
    """Toggle deterrents on/off."""
    service = SettingsService(session)
    current = service.get_setting("deterrents_enabled", "true")
    new_value = "false" if current.lower() == "true" else "true"
    service.set_setting("deterrents_enabled", new_value)
    return {"deterrents_enabled": new_value == "true"}


@router.get("/api/settings/deterrents/status")
def get_deterrent_status(session: Session = Depends(get_session)):
    """Get current deterrent status."""
    service = SettingsService(session)
    enabled = service.get_setting("deterrents_enabled", "true")
    return {"deterrents_enabled": enabled.lower() == "true"}


@router.put("/api/settings/camera-tracking/toggle")
def toggle_camera_tracking(session: Session = Depends(get_session)):
    """Toggle camera tracking on/off."""
    service = SettingsService(session)
    current = service.get_setting("camera_tracking_enabled", "true")
    new_value = "false" if current.lower() == "true" else "true"
    service.set_setting("camera_tracking_enabled", new_value)
    return {"camera_tracking_enabled": new_value == "true"}


@router.get("/api/settings/camera-tracking/status")
def get_camera_tracking_status(session: Session = Depends(get_session)):
    """Get current camera tracking status."""
    service = SettingsService(session)
    enabled = service.get_setting("camera_tracking_enabled", "true")
    return {"camera_tracking_enabled": enabled.lower() == "true"}