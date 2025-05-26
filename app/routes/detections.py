"""Routes for detection management and viewing."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, delete
from datetime import datetime, timedelta
from typing import Optional
import os
from pathlib import Path

from app.core.database import get_session
from app.models.detection import Detection, Foe
from app.models.device import Device

router = APIRouter(prefix="/detections", tags=["detections"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def detections_page(
    request: Request,
    session: Session = Depends(get_session),
    hours: Optional[int] = 24,  # Show last 24 hours by default
    foe_type: Optional[str] = None
):
    """Detections page showing recent detection events."""
    # Calculate time filter
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Build query
    query = select(Detection).where(Detection.timestamp >= since)
    
    # Apply foe type filter if specified
    if foe_type:
        query = query.join(Foe).where(Foe.foe_type == foe_type)
    
    # Order by most recent first
    query = query.order_by(Detection.timestamp.desc())
    
    # Execute query
    detections = session.exec(query).all()
    
    # Get unique foe types for filter dropdown
    foe_types_result = session.exec(
        select(Foe.foe_type).distinct()
    ).all()
    
    context = {
        "request": request,
        "title": "Detections",
        "page": "detections",
        "detections": detections,
        "hours": hours,
        "foe_type": foe_type,
        "available_foe_types": foe_types_result
    }
    
    return templates.TemplateResponse(request, "detections.html", context)


@router.post("/clear-all", response_class=RedirectResponse)
async def clear_all_detections(
    request: Request,
    session: Session = Depends(get_session)
):
    """Clear all detection records and their associated data."""
    # Get all detections to delete their image files
    detections = session.exec(select(Detection)).all()
    
    # Delete image files from disk
    for detection in detections:
        if detection.image_path:
            image_path = Path(detection.image_path)
            if image_path.exists():
                try:
                    os.remove(image_path)
                except Exception as e:
                    # Log error but continue
                    pass
    
    # Delete all foes (cascading delete should handle this, but being explicit)
    session.exec(delete(Foe))
    
    # Delete all detections
    session.exec(delete(Detection))
    
    session.commit()
    
    return RedirectResponse(url="/detections/", status_code=303)