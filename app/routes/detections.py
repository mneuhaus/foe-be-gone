"""Routes for detection management and viewing."""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlmodel import Session, select, delete

from app.core.database import get_session
from app.models.detection import Detection, Foe
from app.models.device import Device
from app.services.detection_worker import detection_worker
from app.services.sound_player import sound_player
from app.services.effectiveness_tracker import effectiveness_tracker
from app.services.camera_diagnostics import camera_diagnostics
from app.models.setting import Setting
from app.models.sound_effectiveness import SoundEffectiveness

router = APIRouter(prefix="/detections", tags=["detections"])
templates = Jinja2Templates(directory="app/templates")


class IntervalUpdate(BaseModel):
    """Request model for updating detection interval."""
    interval: int = Field(ge=1, le=30, description="Detection interval in seconds (1-30)")


class SoundTest(BaseModel):
    """Request model for testing deterrent sounds."""
    foe_type: str = Field(description="Type of foe to test sound for (rats, crows, cats)")


@router.get("/diagnostics", response_class=HTMLResponse, summary="Camera diagnostics page", include_in_schema=False)
async def diagnostics_page(request: Request):
    """Camera diagnostics page."""
    context = {
        "request": request,
        "title": "Camera Diagnostics",
        "page": "diagnostics"
    }
    return templates.TemplateResponse(request, "diagnostics.html", context)


@router.get("/", response_class=HTMLResponse, summary="Detections page", include_in_schema=False)
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
    
    # Get effectiveness data for each detection and convert to dict for template
    detections_with_effectiveness = []
    for detection in detections:
        effectiveness = session.exec(
            select(SoundEffectiveness)
            .where(SoundEffectiveness.detection_id == detection.id)
            .limit(1)
        ).first()
        
        # Convert to dict for template usage - use mode='json' for datetime serialization
        detection_dict = detection.model_dump(mode='json')
        detection_dict['id'] = detection.id
        detection_dict['effectiveness'] = effectiveness.model_dump(mode='json') if effectiveness else None
        detection_dict['device'] = detection.device.model_dump(mode='json') if detection.device else None
        detection_dict['foes'] = [foe.model_dump(mode='json') for foe in detection.foes] if detection.foes else []
        detection_dict['played_sounds'] = detection.played_sounds or []
        detection_dict['video_path'] = detection.video_path
        detection_dict['image_path'] = detection.image_path
        detection_dict['timestamp'] = detection.timestamp
        detection_dict['status'] = detection.status.value if hasattr(detection.status, 'value') else detection.status
        detection_dict['ai_cost_usd'] = detection.ai_cost
        
        # Convert foe_type enums to strings in foes list
        if detection_dict['foes']:
            for foe in detection_dict['foes']:
                if hasattr(foe.get('foe_type'), 'value'):
                    foe['foe_type'] = foe['foe_type'].value
        
        detections_with_effectiveness.append(detection_dict)
    
    context = {
        "request": request,
        "title": "Detections",
        "page": "detections",
        "detections": detections_with_effectiveness,
        "hours": hours,
        "foe_type": foe_type,
        "available_foe_types": foe_types_result,
        "current_interval": detection_worker.check_interval
    }
    
    return templates.TemplateResponse(request, "detections.html", context)


@router.post("/clear-all", response_class=RedirectResponse, summary="Clear all detections", include_in_schema=False)
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


@router.get("/api/interval", summary="Get detection interval", response_model=Dict[str, int])
async def get_detection_interval() -> Dict[str, int]:
    """Get current detection interval.
    
    Returns:
        Dict containing the current detection interval in seconds
    """
    return {"interval": detection_worker.check_interval}


@router.post("/api/interval", summary="Set detection interval", response_model=Dict[str, Any])
async def set_detection_interval(
    interval_update: IntervalUpdate,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Set detection interval (1-30 seconds).
    
    Args:
        interval_update: New interval value
        session: Database session
        
    Returns:
        Dict containing the new interval and success message
        
    Raises:
        HTTPException: If interval is not between 1-30 seconds
    """
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


@router.get("/api/sounds", summary="List available deterrent sounds", response_model=Dict[str, Dict[str, Any]])
async def get_available_sounds() -> Dict[str, Dict[str, Any]]:
    """Get available deterrent sounds by foe type.
    
    Returns:
        Dict mapping foe types to their available sound files
    """
    return sound_player.list_sounds_by_type()


@router.post("/api/sounds/test", summary="Test deterrent sound locally", response_model=Dict[str, Any])
async def test_sound(sound_test: SoundTest) -> Dict[str, Any]:
    """Test playing a deterrent sound for a specific foe type locally.
    
    Args:
        sound_test: Foe type to test sound for
        
    Returns:
        Dict with success status and message
        
    Raises:
        HTTPException: If foe type is invalid or sound playback fails
    """
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


@router.post("/api/sounds/test-camera/{device_id}", summary="Test deterrent sound on camera", response_model=Dict[str, Any])
async def test_sound_on_camera(
    device_id: str, 
    sound_test: SoundTest, 
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Test playing a deterrent sound on a specific camera.
    
    Args:
        device_id: ID of the camera device
        sound_test: Foe type to test sound for
        session: Database session
        
    Returns:
        Dict with success status and message
        
    Raises:
        HTTPException: If device not found, invalid foe type, or playback fails
    """
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


@router.get("/video/{detection_id}", include_in_schema=False)
async def serve_detection_video(detection_id: int, session: Session = Depends(get_session)):
    """Serve video file for a detection."""
    detection = session.get(Detection, detection_id)
    if not detection or not detection.video_path:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_path = Path(detection.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=video_path.name
    )


@router.get("/api/effectiveness/summary", summary="Get effectiveness summary")
async def get_effectiveness_summary(foe_type: Optional[str] = None) -> Dict[str, Any]:
    """Get summary of sound effectiveness statistics.
    
    Args:
        foe_type: Optional filter by foe type
        
    Returns:
        Summary of effectiveness statistics
    """
    return effectiveness_tracker.get_statistics_summary(foe_type)


@router.get("/api/effectiveness/time-patterns/{foe_type}", summary="Get time-based patterns")
async def get_time_patterns(foe_type: str) -> List[Dict[str, Any]]:
    """Get effectiveness patterns by time of day for a specific foe type.
    
    Args:
        foe_type: Type of foe to get patterns for
        
    Returns:
        List of hourly effectiveness patterns
    """
    return effectiveness_tracker.get_time_patterns(foe_type)


@router.get("/api/diagnostics/cameras", summary="Get camera health status")
async def get_camera_diagnostics() -> Dict[str, Any]:
    """Get diagnostic information about camera health and errors.
    
    Returns:
        Camera health status and error information
    """
    return camera_diagnostics.get_camera_health_status()


@router.get("/api/diagnostics/camera/{camera_id}/errors", summary="Get camera error history")
async def get_camera_errors(camera_id: str, limit: int = 10) -> Dict[str, Any]:
    """Get error history for a specific camera.
    
    Args:
        camera_id: ID of the camera
        limit: Maximum number of errors to return
        
    Returns:
        Error history and suggested fixes
    """
    errors = camera_diagnostics.get_camera_error_history(camera_id, limit)
    suggestions = camera_diagnostics.suggest_fixes(camera_id)
    
    return {
        "camera_id": camera_id,
        "error_count": len(errors),
        "errors": errors,
        "suggestions": suggestions
    }