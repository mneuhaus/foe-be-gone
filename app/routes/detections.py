"""Routes for detection management and viewing."""
import logging
import os
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.core.templates import templates
from app.core.responses import success_response, error_response
from app.core.config import config
from app.models.detection import Detection, Foe
from app.models.device import Device
from app.services.detection_worker import detection_worker
from app.services.sound_player import sound_player
from app.services.effectiveness_tracker import effectiveness_tracker
from app.services.camera_diagnostics import camera_diagnostics
from app.models.setting import Setting
from app.models.sound_effectiveness import SoundEffectiveness
from app.services.settings_service import SettingsService
from app.services.qwen_species_detector import QwenSpeciesDetector
from app.services.detection_grouping_service import DetectionGroupingService
from app.utils.image_utils import crop_image_with_padding, get_cached_resized_image, create_cached_resized_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detections", tags=["detections"])


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


@router.get("/", response_class=HTMLResponse, summary="Detections page", include_in_schema=False, name="view_detections")
async def detections_page(
    request: Request,
    session: Session = Depends(get_session),
    page: int = 1,
    per_page: int = 30,
    hours: Optional[int] = None,  # Filter by hours if provided
    foe_type: Optional[str] = None,
    device_id: Optional[str] = None,
    group_similar: bool = True  # Enable visual similarity grouping by default
):
    """Detections page showing detection events with pagination."""
    # Build base query
    query = select(Detection)
    count_query = select(Detection)
    
    # Apply time filter if specified
    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.where(Detection.timestamp >= since)
        count_query = count_query.where(Detection.timestamp >= since)
    
    # Apply foe type filter if specified
    if foe_type:
        query = query.join(Foe).where(Foe.foe_type == foe_type)
        count_query = count_query.join(Foe).where(Foe.foe_type == foe_type)
    
    # Apply device filter if specified
    if device_id:
        query = query.where(Detection.device_id == device_id)
        count_query = count_query.where(Detection.device_id == device_id)
    
    # Execute query with eager loading of relationships
    query = query.options(
        selectinload(Detection.foes),
        selectinload(Detection.device)
    )
    
    if group_similar:
        # For grouping, we need to fetch more detections to properly group them
        # Get up to 200 recent detections for grouping (adjust based on needs)
        all_detections = session.exec(
            query.order_by(Detection.timestamp.desc()).limit(200)
        ).all()
        
        # Group detections by visual similarity  
        detection_groups = DetectionGroupingService.group_detections(all_detections)
        
        # Apply pagination to groups
        total_groups = len(detection_groups)
        total_pages = (total_groups + per_page - 1) // per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        
        # Calculate group pagination
        group_offset = (page - 1) * per_page
        paginated_groups = detection_groups[group_offset:group_offset + per_page]
        
        # Extract detections from groups for template compatibility
        detections = [group.primary_detection for group in paginated_groups]
        group_info = {group.primary_detection.id: group for group in paginated_groups}
        
        # Use group count as total count
        total_count = total_groups
        
    else:
        # Original pagination logic for non-grouped view
        total_count = len(session.exec(count_query).all())
        total_pages = (total_count + per_page - 1) // per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Order by most recent first and apply pagination
        detections = session.exec(
            query.order_by(Detection.timestamp.desc()).offset(offset).limit(per_page)
        ).all()
        
        group_info = {}  # No grouping
    
    # Get unique foe types for filter dropdown
    foe_types_result = session.exec(
        select(Foe.foe_type).distinct()
    ).all()
    
    # Get available devices for filter dropdown
    available_devices = session.exec(
        select(Device).where(Device.device_type == "camera")
    ).all()
    
    # Get effectiveness data for each detection and convert to dict for template
    detections_with_effectiveness = []
    for detection in detections:
        effectiveness = session.exec(
            select(SoundEffectiveness)
            .where(SoundEffectiveness.detection_id == detection.id)
            .limit(1)
        ).first()
        
        # Convert to dict for template usage - keep datetime objects for template, convert for JS
        detection_dict = detection.model_dump()
        detection_dict['id'] = detection.id
        detection_dict['effectiveness'] = effectiveness.model_dump() if effectiveness else None
        detection_dict['device'] = detection.device.model_dump() if detection.device else None
        detection_dict['foes'] = [foe.model_dump() for foe in detection.foes] if detection.foes else []
        detection_dict['played_sounds'] = detection.played_sounds or []
        detection_dict['video_path'] = detection.video_path
        detection_dict['image_path'] = detection.image_path
        detection_dict['timestamp'] = detection.timestamp  # Keep as datetime for template
        detection_dict['processed_at'] = detection.processed_at
        detection_dict['created_at'] = detection.created_at
        detection_dict['status'] = detection.status.value if hasattr(detection.status, 'value') else detection.status
        detection_dict['ai_cost_usd'] = detection.ai_cost  # Keep as ai_cost_usd for template compatibility
        
        # Convert foe_type enums to strings in foes list
        if detection_dict['foes']:
            for foe in detection_dict['foes']:
                if hasattr(foe.get('foe_type'), 'value'):
                    foe['foe_type'] = foe['foe_type'].value
        
        detections_with_effectiveness.append(detection_dict)
    
    # Get current detection settings
    snapshot_capture_level = 1
    
    capture_level_setting = session.get(Setting, 'snapshot_capture_level')
    if capture_level_setting:
        try:
            snapshot_capture_level = int(capture_level_setting.value)
        except ValueError:
            pass
    
    # Map capture levels to human-readable labels
    capture_level_labels = {
        0: "Foe Identified",      # Only save when a foe (crow, rat, etc.) is detected
        1: "Object Recognized",   # Save when any object/animal is detected
        2: "All Snapshots"        # Save all snapshots regardless of detection
    }
    
    # Get timezone setting
    settings_service = SettingsService(session)
    timezone = settings_service.get_timezone()
    
    context = {
        "request": request,
        "title": "Detections",
        "page": "detections",
        "detections": detections_with_effectiveness,
        "hours": hours,
        "foe_type": foe_type,
        "device_id": device_id,
        "group_similar": group_similar,
        "available_foe_types": foe_types_result,
        "available_devices": available_devices,
        "current_interval": detection_worker.check_interval,
        "snapshot_capture_level": snapshot_capture_level,
        "capture_level_label": capture_level_labels.get(snapshot_capture_level, "Unknown"),
        "timezone": timezone,
        # Pagination data
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else 1,
        "next_page": page + 1 if page < total_pages else total_pages,
        "page_range": list(range(max(1, page - 2), min(total_pages + 1, page + 3))),
        # Grouping data
        "group_info": group_info if group_similar else {}
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
    old_interval = detection_worker.check_interval
    detection_worker.check_interval = interval
    logger.info(f"Updated detection interval from {old_interval}s to {interval}s")
    
    # Persist interval to settings
    try:
        setting = session.get(Setting, 'detection_interval')
        if setting:
            setting.value = str(interval)
            logger.debug(f"Updated existing detection_interval setting to {interval}")
        else:
            setting = Setting(key='detection_interval', value=str(interval))
            session.add(setting)
            logger.debug(f"Created new detection_interval setting with value {interval}")
        session.commit()
        logger.info(f"Successfully persisted detection interval {interval}s to database")
    except Exception as e:
        # Log and continue
        logger.error(f"Failed to persist detection interval: {e}")
    return {
        "interval": interval, 
        "message": f"Detection interval updated to {interval} seconds",
        "persisted": True
    }


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
        return success_response(f"Played deterrent sound for {foe_type} locally")
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
                return success_response(f"Played deterrent sound '{selected_sound.name}' on camera {device.name}")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to play sound on camera {device.name}")
        else:
            raise HTTPException(status_code=400, detail="Camera does not support sound playback")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing sound on camera: {str(e)}")


@router.get("/image-with-boxes/{detection_id}", include_in_schema=False)
async def serve_detection_image_with_boxes(
    detection_id: int,
    session: Session = Depends(get_session)
):
    """Serve detection image with bounding boxes drawn."""
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.image_path or not Path(detection.image_path).exists():
        raise HTTPException(status_code=404, detail="No image available for this detection")
    
    try:
        # Load the original image
        image = Image.open(detection.image_path).convert('RGB')
        
        # Check if we have YOLO results or foe bounding boxes
        draw_boxes = False
        
        # Option 1: Use YOLO results if available
        if detection.ai_response and "yolo_results" in detection.ai_response:
            yolo_results = detection.ai_response["yolo_results"]
            if yolo_results.get("detections"):
                draw_boxes = True
                # Use YOLO service to draw boxes
                from app.services.yolo_detector import YOLOv11DetectionService, YOLODetection
                
                yolo_service = YOLOv11DetectionService()
                detections_list = []
                
                for det in yolo_results["detections"]:
                    yolo_det = YOLODetection(
                        class_id=0,  # Not needed for drawing
                        class_name=det["class_name"],
                        confidence=det["confidence"],
                        bbox=tuple(det["bbox"]),
                        category=det.get("category", "unknown")
                    )
                    detections_list.append(yolo_det)
                
                # Draw bounding boxes
                image = yolo_service.draw_detections(
                    image, 
                    detections_list,
                    yolo_results.get("foe_classifications", {})
                )
        
        # Option 2: Fall back to foe bounding boxes if no YOLO results
        if not draw_boxes and detection.foes:
            draw = ImageDraw.Draw(image)
            
            # Define colors for different foe types
            colors = {
                "rats": "#ef4444",     # red
                "crows": "#f59e0b",    # amber
                "cats": "#10b981",     # green
                "herons": "#3b82f6",   # blue
                "pigeons": "#8b5cf6",  # purple
                "unknown": "#6b7280"   # gray
            }
            
            for foe in detection.foes:
                if foe.bounding_box and "x" in foe.bounding_box:
                    # Extract coordinates
                    x = foe.bounding_box.get("x", 0)
                    y = foe.bounding_box.get("y", 0)
                    width = foe.bounding_box.get("width", 0)
                    height = foe.bounding_box.get("height", 0)
                    
                    # Calculate box corners
                    x1, y1 = x, y
                    x2, y2 = x + width, y + height
                    
                    # Get color for foe type
                    color = colors.get(foe.foe_type.lower(), colors["unknown"])
                    
                    # Draw rectangle
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                    
                    # Draw label with confidence
                    label = f"{foe.foe_type} {foe.confidence:.0%}"
                    try:
                        # Try to use a system font
                        font = None
                        font_paths = [
                            "/System/Library/Fonts/Helvetica.ttc",
                            "/Library/Fonts/Arial.ttf",
                            "/System/Library/Fonts/Avenir.ttc"
                        ]
                        for font_path in font_paths:
                            if Path(font_path).exists():
                                font = ImageFont.truetype(font_path, 16)
                                break
                        if not font:
                            font = ImageFont.load_default()
                    except:
                        font = ImageFont.load_default()
                    
                    # Get text bbox for background
                    bbox = draw.textbbox((x1, y1), label, font=font)
                    
                    # Draw label background
                    draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=color)
                    
                    # Draw label text
                    draw.text((x1, y1), label, fill="white", font=font)
        
        # Convert image to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)
        
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/jpeg"
        )
        
    except Exception as e:
        logger.error(f"Error processing detection image: {e}")
        # Fall back to original image
        return FileResponse(detection.image_path)


@router.get("/cropped-image/{detection_id}/{crop_index}", include_in_schema=False)
async def serve_cropped_species_image(
    detection_id: int,
    crop_index: int,
    session: Session = Depends(get_session)
):
    """Serve cropped image used for species identification."""
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.image_path or not Path(detection.image_path).exists():
        raise HTTPException(status_code=404, detail="No image available for this detection")
    
    # Check if species results exist
    species_results = detection.ai_response.get("species_results") if detection.ai_response else None
    if not species_results or not species_results.get("species_identifications"):
        raise HTTPException(status_code=404, detail="No species identification data available")
    
    species_identifications = species_results.get("species_identifications", [])
    if crop_index >= len(species_identifications):
        raise HTTPException(status_code=404, detail="Crop index out of range")
    
    try:
        # Load the original image
        image = Image.open(detection.image_path).convert('RGB')
        
        # Get the bounding box for this crop
        species_data = species_identifications[crop_index]
        bbox = species_data.get("bbox")
        
        if not bbox or len(bbox) != 4:
            raise HTTPException(status_code=400, detail="Invalid bounding box data")
        
        # Import the cropping functionality
        from app.core.config import config
        
        # Crop the image with the same padding used during analysis
        cropped_image = crop_image_with_padding(
            image, 
            tuple(bbox), 
            padding_percent=config.SPECIES_CROP_PADDING
        )
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        cropped_image.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)
        
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename=detection_{detection_id}_crop_{crop_index}.jpg"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating cropped image: {e}")
        raise HTTPException(status_code=500, detail="Error generating cropped image")


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


@router.get("/image-resized/{detection_id}", include_in_schema=False)
async def serve_resized_detection_image(
    detection_id: int,
    width: int = 300,
    height: int = 200,
    quality: int = 85,
    session: Session = Depends(get_session)
):
    """Serve a resized and cached detection image for thumbnails."""
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.image_path or not Path(detection.image_path).exists():
        raise HTTPException(status_code=404, detail="No image available for this detection")
    
    # Validate parameters
    width = max(50, min(width, 2000))  # Limit width between 50-2000px
    height = max(50, min(height, 2000))  # Limit height between 50-2000px
    quality = max(10, min(quality, 100))  # Limit quality between 10-100
    
    try:
        # Check for cached version first
        cached_path = get_cached_resized_image(
            detection.image_path, width, height, quality
        )
        
        if cached_path:
            return FileResponse(
                path=cached_path,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "Content-Disposition": f"inline; filename=detection_{detection_id}_{width}x{height}.jpg"
                }
            )
        
        # Create and cache resized image
        cached_path = create_cached_resized_image(
            detection.image_path, width, height, quality
        )
        
        if cached_path:
            return FileResponse(
                path=cached_path,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "Content-Disposition": f"inline; filename=detection_{detection_id}_{width}x{height}.jpg"
                }
            )
        else:
            # Fall back to original image if resizing fails
            return FileResponse(
                path=detection.image_path,
                headers={
                    "Cache-Control": "public, max-age=3600"  # Shorter cache for fallback
                }
            )
            
    except Exception as e:
        logger.error(f"Error serving resized image: {e}")
        # Fall back to original image
        return FileResponse(detection.image_path)


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


@router.get("/api/detections", summary="Get recent detections", response_model=List[Dict[str, Any]])
async def get_recent_detections(
    session: Session = Depends(get_session),
    since: Optional[datetime] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent detections for auto-refresh.
    
    Args:
        since: Only get detections after this timestamp
        limit: Maximum number of detections to return
        
    Returns:
        List of detection dictionaries
    """
    # Build query
    query = select(Detection)
    if since:
        query = query.where(Detection.timestamp > since)
    
    # Order by most recent first and apply limit
    query = query.order_by(Detection.timestamp.desc()).limit(limit)
    
    # Execute query
    detections = session.exec(query).all()
    
    # Convert to dict format for JSON response
    result = []
    for detection in detections:
        effectiveness = session.exec(
            select(SoundEffectiveness)
            .where(SoundEffectiveness.detection_id == detection.id)
            .limit(1)
        ).first()
        
        detection_dict = detection.model_dump(mode='json')
        detection_dict['id'] = detection.id
        detection_dict['effectiveness'] = effectiveness.model_dump(mode='json') if effectiveness else None
        detection_dict['device'] = detection.device.model_dump(mode='json') if detection.device else None
        detection_dict['foes'] = [foe.model_dump(mode='json') for foe in detection.foes] if detection.foes else []
        detection_dict['played_sounds'] = detection.played_sounds or []
        detection_dict['video_path'] = detection.video_path
        detection_dict['image_path'] = detection.image_path
        detection_dict['timestamp'] = detection.timestamp.isoformat()
        detection_dict['status'] = detection.status.value if hasattr(detection.status, 'value') else detection.status
        detection_dict['ai_cost_usd'] = detection.ai_cost
        
        # Convert foe_type enums to strings
        if detection_dict['foes']:
            for foe in detection_dict['foes']:
                if hasattr(foe.get('foe_type'), 'value'):
                    foe['foe_type'] = foe['foe_type'].value
        
        result.append(detection_dict)
    
    return result


@router.get("/api/settings", summary="Get detection settings", response_model=Dict[str, Any])
async def get_detection_settings(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get current detection settings.
    
    Returns:
        Dict containing detection settings
    """
    # Default values
    settings = {
        "capture_all_snapshots": False
    }
    
    # Get capture_all_snapshots setting
    capture_all = session.get(Setting, 'capture_all_snapshots')
    if capture_all:
        settings["capture_all_snapshots"] = capture_all.value.lower() == 'true'
    
    
    return settings


class CaptureAllUpdate(BaseModel):
    """Request model for updating capture all snapshots setting."""
    enabled: bool = Field(description="Whether to capture all snapshots")


class CaptureLevelUpdate(BaseModel):
    """Request model for updating snapshot capture level."""
    level: int = Field(ge=0, le=2, description="Capture level (0-2)")




@router.post("/api/settings/capture-all", summary="Set capture all snapshots setting", response_model=Dict[str, Any])
async def set_capture_all_snapshots(
    update: CaptureAllUpdate,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Set whether to capture all snapshots even without foes.
    
    Args:
        update: CaptureAllUpdate request body
        session: Database session
        
    Returns:
        Dict with success status
    """
    enabled = update.enabled
    setting = session.get(Setting, 'capture_all_snapshots')
    if setting:
        setting.value = str(enabled).lower()
    else:
        setting = Setting(key='capture_all_snapshots', value=str(enabled).lower())
        session.add(setting)
    
    session.commit()
    
    return success_response(f"Capture all snapshots {'enabled' if enabled else 'disabled'}")




@router.post("/api/settings/capture-level", summary="Set snapshot capture level", response_model=Dict[str, Any])
async def set_capture_level(
    update: CaptureLevelUpdate,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Set the snapshot capture level.
    
    Args:
        update: CaptureLevelUpdate request body
        session: Database session
        
    Returns:
        Dict with success status
    """
    level = update.level
    level_names = {
        0: "Foe Identified",
        1: "Object Recognized",
        2: "All Snapshots"
    }
    
    setting = session.get(Setting, 'snapshot_capture_level')
    if setting:
        setting.value = str(level)
    else:
        setting = Setting(key='snapshot_capture_level', value=str(level))
        session.add(setting)
    
    session.commit()
    
    return success_response(f"Capture level set to: {level_names.get(level, 'Unknown')}")


@router.get("/api/species-detector/health", summary="Get species detector health status")
async def get_species_detector_health(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """Get health status of the species identification system.
    
    Returns:
        Dict containing health status and configuration
    """
    try:
        species_detector = QwenSpeciesDetector(session=session)
        health_status = species_detector.health_check()
        
        return {
            "status": "healthy" if health_status["model_loaded"] else "degraded",
            "details": health_status,
            "enabled": config.SPECIES_IDENTIFICATION_ENABLED,
            "model_type": "local",
            "crop_padding": config.SPECIES_CROP_PADDING
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "enabled": config.SPECIES_IDENTIFICATION_ENABLED,
            "model": config.SPECIES_MODEL,
            "crop_padding": config.SPECIES_CROP_PADDING
        }