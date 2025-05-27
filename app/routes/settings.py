"""Settings page routes."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.integration_instance import IntegrationInstance
from app.models.device import Device
from app.models.setting import Setting

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")

# Define default settings structure
DEFAULT_SETTINGS = {
    "openai_api_key": {"value": "", "label": "OpenAI API Key", "type": "password", "required": True, "description": "API key for OpenAI GPT-4 Vision integration"},
    "log_level": {"value": "INFO", "label": "Log Level", "type": "select", "options": ["DEBUG", "INFO", "WARNING", "ERROR"], "description": "Application logging level"},
    "detection_interval": {"value": "10", "label": "Detection Interval (seconds)", "type": "number", "min": 1, "max": 30, "description": "Time between detection checks"},
    "confidence_threshold": {"value": "0.5", "label": "Confidence Threshold", "type": "number", "min": 0.1, "max": 1.0, "step": 0.1, "description": "Minimum confidence for foe detection"},
    "max_image_size_mb": {"value": "10", "label": "Max Image Size (MB)", "type": "number", "min": 1, "max": 50, "description": "Maximum allowed image upload size"},
    "snapshot_retention_days": {"value": "7", "label": "Snapshot Retention (days)", "type": "number", "min": 1, "max": 365, "description": "How long to keep detection snapshots"}
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


@router.get("/", response_class=HTMLResponse)
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


@router.post("/", response_class=RedirectResponse)
async def update_general_settings(
    request: Request,
    session: Session = Depends(get_session)
):
    """Update general settings."""
    form_data = await request.form()
    
    # Update each setting
    for key in DEFAULT_SETTINGS.keys():
        if key in form_data:
            value = form_data[key]
            set_setting_value(session, key, str(value))
    
    return RedirectResponse(url="/settings/", status_code=303)


@router.get("/integrations", response_class=HTMLResponse)
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