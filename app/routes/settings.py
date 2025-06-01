"""Settings page routes."""

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List
import os
import shutil
from pathlib import Path

from app.core.database import get_session
from app.core.templates import templates
from app.core.url_helpers import url_for
from app.core.responses import success_response, error_response
from app.models.integration_instance import IntegrationInstance
from app.models.device import Device
from app.models.setting import Setting
from app.services.sound_player import sound_player

router = APIRouter(prefix="/settings", tags=["settings"])

# Define default settings structure
DEFAULT_SETTINGS = {
    "openai_api_key": {"value": "", "label": "OpenAI API Key", "type": "password", "required": True, "description": "API key for OpenAI GPT-4 Vision integration"},
    "log_level": {"value": "INFO", "label": "Log Level", "type": "select", "options": ["DEBUG", "INFO", "WARNING", "ERROR"], "description": "Application logging level"},
    "detection_interval": {"value": "10", "label": "Detection Interval (seconds)", "type": "number", "min": 1, "max": 30, "description": "Time between detection checks"},
    "confidence_threshold": {"value": "0.5", "label": "Confidence Threshold", "type": "number", "min": 0.1, "max": 1.0, "step": 0.1, "description": "Minimum confidence for foe detection"},
    "max_image_size_mb": {"value": "10", "label": "Max Image Size (MB)", "type": "number", "min": 1, "max": 50, "description": "Maximum allowed image upload size"},
    "snapshot_retention_days": {"value": "7", "label": "Snapshot Retention (days)", "type": "number", "min": 1, "max": 365, "description": "How long to keep detection snapshots"},
    "timezone": {"value": "UTC", "label": "Timezone", "type": "select", "options": ["UTC", "Europe/Berlin", "Europe/London", "Europe/Paris", "Europe/Rome", "Europe/Madrid", "Europe/Vienna", "Europe/Warsaw", "Europe/Amsterdam", "Europe/Brussels", "Europe/Zurich", "America/New_York", "America/Chicago", "America/Los_Angeles", "America/Toronto", "America/Mexico_City", "Asia/Tokyo", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Singapore", "Australia/Sydney", "Australia/Melbourne"], "description": "Timezone for displaying dates and times"},
    "yolo_enabled": {"value": "true", "label": "Enable YOLO Detection", "type": "checkbox", "description": "Use YOLO for fast local animal detection"},
    "yolo_confidence_threshold": {"value": "0.25", "label": "YOLO Confidence Threshold", "type": "number", "min": 0.1, "max": 0.9, "step": 0.05, "description": "Minimum confidence for YOLO detections"}
}


def get_setting_value(session: Session, key: str) -> str:
    """Get setting value from database, return default if not found."""
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if setting:
        return setting.value
    return DEFAULT_SETTINGS.get(key, {}).get("value", "")


def set_setting_value(session: Session, key: str, value: str) -> None:
    """Set setting value in database, create if not exists."""
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        session.add(setting)
    session.commit()


@router.get("/", response_class=HTMLResponse, name="settings_general")
async def general_settings_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display general settings page."""
    # Get all current setting values
    current_settings = {}
    for key, config in DEFAULT_SETTINGS.items():
        current_settings[key] = {
            **config,
            "current_value": get_setting_value(session, key)
        }
    
    return templates.TemplateResponse(
        "settings/general.html",
        {
            "request": request,
            "page": "settings",
            "settings": current_settings
        }
    )


@router.post("/", response_class=RedirectResponse, name="update_general_settings")
async def update_general_settings(
    request: Request,
    session: Session = Depends(get_session)
):
    """Update general settings."""
    form_data = await request.form()
    
    # Update each setting
    for key, config in DEFAULT_SETTINGS.items():
        if config.get("type") == "checkbox":
            # Checkboxes are only in form_data when checked
            value = "true" if key in form_data else "false"
            set_setting_value(session, key, value)
        elif key in form_data:
            value = form_data[key]
            set_setting_value(session, key, str(value))
    
    return RedirectResponse(url=url_for(request, "settings_general"), status_code=303)


@router.get("/integrations", response_class=HTMLResponse, name="settings_integrations")
async def integrations_page(
    request: Request, 
    session: Session = Depends(get_session)
):
    """Display integrations settings page."""
    # Get all integration instances with their devices
    integrations = session.exec(
        select(IntegrationInstance)
        .options(selectinload(IntegrationInstance.devices))
        .order_by(IntegrationInstance.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        "settings/integrations.html",
        {
            "request": request,
            "page": "settings",
            "integrations": integrations
        }
    )


@router.get("/sounds", response_class=HTMLResponse, name="settings_sounds")
async def sounds_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display sound management page."""
    # Get available sounds organized by foe type
    sounds_by_type = sound_player.list_sounds_by_type()
    
    # Get the foe types we support
    foe_types = ["crows", "rats", "cats", "herons", "pigeons"]  # Hardcoded as requested
    
    # Ensure all foe types are in the dict even if they have no sounds
    for foe_type in foe_types:
        if foe_type not in sounds_by_type:
            sounds_by_type[foe_type] = {"count": 0, "files": []}
    
    return templates.TemplateResponse(
        "settings/sounds.html",
        {
            "request": request,
            "page": "settings",
            "sounds_by_type": sounds_by_type,
            "foe_types": foe_types
        }
    )


@router.post("/sounds/upload", response_model=Dict[str, Any], name="upload_sound")
async def upload_sound(
    foe_type: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Upload a new sound file for a specific foe type."""
    # Validate foe type
    valid_foe_types = ["crows", "rats", "cats", "herons", "pigeons"]
    if foe_type not in valid_foe_types:
        raise HTTPException(status_code=400, detail=f"Invalid foe type: {foe_type}")
    
    # Validate file extension
    allowed_extensions = [".mp3", ".wav"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Create directory if it doesn't exist
    sounds_dir = Path("public/sounds") / foe_type
    sounds_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    file_path = sounds_dir / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return success_response(f"Sound '{file.filename}' uploaded successfully for {foe_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.delete("/sounds/{foe_type}/{filename}", response_model=Dict[str, Any], name="delete_sound")
async def delete_sound(
    foe_type: str,
    filename: str,
    session: Session = Depends(get_session)
):
    """Delete a sound file."""
    # Validate foe type
    valid_foe_types = ["crows", "rats", "cats", "herons", "pigeons"]
    if foe_type not in valid_foe_types:
        raise HTTPException(status_code=400, detail=f"Invalid foe type: {foe_type}")
    
    # Construct file path
    file_path = Path("public/sounds") / foe_type / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Sound file not found: {filename}")
    
    # Delete the file
    try:
        file_path.unlink()
        return success_response(f"Sound '{filename}' deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/language", response_model=Dict[str, Any], name="set_language")
async def set_language(
    language: str = Form(...),
    session: Session = Depends(get_session)
):
    """Set the user's language preference."""
    # Validate language
    valid_languages = ["en", "de"]
    if language not in valid_languages:
        raise HTTPException(status_code=400, detail=f"Invalid language: {language}")
    
    # Store language preference in settings
    setting = session.get(Setting, 'user_language')
    if setting:
        setting.value = language
    else:
        setting = Setting(key='user_language', value=language)
        session.add(setting)
    
    session.commit()
    
    return success_response(f"Language set to {language}")