"""Settings page routes."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.integration_instance import IntegrationInstance
from app.models.device import Device

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")


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