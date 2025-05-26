"""Routes for detection management and viewing."""
from fastapi import APIRouter, Request, Depends, HTTPException
import logging
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, delete
from datetime import datetime, timedelta
from typing import Optional
import os
from pathlib import Path
from pydantic import BaseModel

from app.core.database import get_session
from app.models.detection import Detection, Foe
from app.models.device import Device
from app.services.detection_worker import detection_worker
from app.services.sound_player import sound_player
from app.models.setting import Setting

router = APIRouter(prefix="/detections", tags=["detections"])
templates = Jinja2Templates(directory="app/templates")


class IntervalUpdate(BaseModel):
    interval: int


class SoundTest(BaseModel):
    foe_type: str


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
        "available_foe_types": foe_types_result,
        "current_interval": detection_worker.check_interval
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


@router.get("/api/interval")
async def get_detection_interval():
    """Get current detection interval."""
    return {"interval": detection_worker.check_interval}


@router.post("/api/interval")
async def set_detection_interval(
    interval_update: IntervalUpdate,
    session: Session = Depends(get_session)
):
    """Set detection interval (1-30 seconds)."""
    interval = interval_update.interval
    
    # Validate interval range
    if not 1 <= interval <= 30:
        raise HTTPException(status_code=400, detail="Interval must be between 1 and 30 seconds")
    
    # Update the detection worker interval
    detection_worker.check_interval = interval
    # Persist interval to settings
    try:
        setting = session.get(Setting, 'detection_interval')
        if setting:
            setting.value = str(interval)
        else:
            setting = Setting(key='detection_interval', value=str(interval))
            session.add(setting)
        session.commit()
    except Exception as e:
        # Log and continue
        logging.getLogger(__name__).warning(f"Failed to persist detection interval: {e}")
    return {"interval": interval, "message": f"Detection interval updated to {interval} seconds"}


@router.get("/api/sounds")
async def get_available_sounds():
    """Get available deterrent sounds by foe type."""
    return sound_player.list_sounds_by_type()


@router.post("/api/sounds/test")
async def test_sound(sound_test: SoundTest):
    """Test playing a deterrent sound for a specific foe type locally."""
    foe_type = sound_test.foe_type
    
    # Validate foe type
    valid_types = ["rats", "crows", "cats"]
    if foe_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid foe type. Must be one of: {valid_types}")
    
    # Try to play sound locally
    success = sound_player.play_random_sound(foe_type)
    
    if success:
        return {"success": True, "message": f"Played deterrent sound for {foe_type} locally"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to play sound for {foe_type}")


@router.post("/api/sounds/test-camera/{device_id}")
async def test_sound_on_camera(device_id: str, sound_test: SoundTest, session: Session = Depends(get_session)):
    """Test playing a deterrent sound on a specific camera."""
    from app.integrations import get_integration_class
    
    foe_type = sound_test.foe_type
    
    # Validate foe type
    valid_types = ["rats", "crows", "cats"]
    if foe_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid foe type. Must be one of: {valid_types}")
    
    # Get the device from database
    device = session.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get the integration instance
    integration = device.integration
    if not integration:
        raise HTTPException(status_code=400, detail="Device has no integration")
    
    # Get camera ID from device metadata
    camera_id = device.device_metadata.get("camera_id")
    if not camera_id:
        raise HTTPException(status_code=400, detail="Device has no camera_id in metadata")
    
    try:
        # Get integration handler
        integration_class = get_integration_class(integration.integration_type)
        if not integration_class:
            raise HTTPException(status_code=400, detail=f"Unknown integration type: {integration.integration_type}")
        
        handler = integration_class(integration)
        device_interface = await handler.get_device(camera_id)
        
        if not device_interface:
            raise HTTPException(status_code=404, detail="Camera device not found in integration")
        
        # Get a random sound file for this foe type
        available_sounds = sound_player.get_available_sounds(foe_type)
        if not available_sounds:
            raise HTTPException(status_code=404, detail=f"No sounds available for {foe_type}")
        
        selected_sound = sound_player._select_random_sound(available_sounds)
        
        # Play sound on camera
        if hasattr(device_interface, 'play_sound_file'):
            success = await device_interface.play_sound_file(selected_sound)
            if success:
                return {"success": True, "message": f"Played deterrent sound '{selected_sound.name}' on camera {device.name}"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to play sound on camera {device.name}")
        else:
            raise HTTPException(status_code=400, detail="Camera does not support sound playback")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing sound on camera: {str(e)}")