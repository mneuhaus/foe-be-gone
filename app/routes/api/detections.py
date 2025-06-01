"""API endpoints for detection data."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sqlalchemy import desc

from app.core.database import get_session
from app.models.detection import Detection, Foe
from app.models.device import Device
from app.services.yolo_detector import YOLOv11DetectionService
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/detections",
    tags=["detections"]
)


@router.get("/latest", summary="Get latest detections for all cameras")
async def get_latest_detections(
    request: Request,
    session: Session = Depends(get_session),
    limit: int = 10
) -> Dict[str, Any]:
    """Get the latest detections across all cameras."""
    detections = session.exec(
        select(Detection)
        .order_by(desc(Detection.timestamp))
        .limit(limit)
    ).all()
    
    results = []
    for detection in detections:
        # Get device info
        device = session.get(Device, detection.device_id)
        
        det_data = {
            "id": detection.id,
            "device_id": detection.device_id,
            "device_name": device.name if device else "Unknown",
            "timestamp": detection.timestamp.isoformat(),
            "status": detection.status,
            "image_path": detection.image_path,
            "foes": [
                {
                    "type": foe.foe_type,
                    "confidence": foe.confidence,
                    "bounding_box": foe.bounding_box
                }
                for foe in detection.foes
            ],
            "yolo_results": detection.ai_response.get("yolo_results") if detection.ai_response else None
        }
        results.append(det_data)
    
    return {"detections": results}


@router.get("/camera/{device_id}/latest", summary="Get latest detection for a specific camera")
async def get_camera_latest_detection(
    device_id: str,
    request: Request,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get the latest detection for a specific camera with YOLO results."""
    
    # Get the latest detection for this camera
    detection = session.exec(
        select(Detection)
        .where(Detection.device_id == device_id)
        .order_by(desc(Detection.timestamp))
        .limit(1)
    ).first()
    
    if not detection:
        return {"detection": None}
    
    # Get device info
    device = session.get(Device, device_id)
    
    # Build response
    result = {
        "id": detection.id,
        "device_id": detection.device_id,
        "device_name": device.name if device else "Unknown",
        "timestamp": detection.timestamp.isoformat(),
        "status": detection.status,
        "image_path": detection.image_path,
        "foes": [
            {
                "type": foe.foe_type,
                "confidence": foe.confidence,
                "bounding_box": foe.bounding_box
            }
            for foe in detection.foes
        ],
        "yolo_results": detection.ai_response.get("yolo_results") if detection.ai_response else None,
        "ai_analysis": detection.ai_response.get("scene_description") if detection.ai_response else None
    }
    
    return {"detection": result}


@router.get("/{detection_id}/with-boxes", summary="Get detection image with bounding boxes")
async def get_detection_with_boxes(
    detection_id: int,
    request: Request,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get detection image with YOLO bounding boxes drawn."""
    
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.image_path:
        raise HTTPException(status_code=404, detail="No image available for this detection")
    
    # Check if we have YOLO results
    yolo_results = detection.ai_response.get("yolo_results") if detection.ai_response else None
    if not yolo_results or not yolo_results.get("detections"):
        raise HTTPException(status_code=404, detail="No YOLO detections available")
    
    try:
        # Load the image
        image = Image.open(detection.image_path)
        
        # Initialize YOLO service for drawing
        yolo_service = YOLOv11DetectionService()
        
        # Convert YOLO results back to detection objects for drawing
        from app.services.yolo_detector import YOLODetection
        detections = []
        for det in yolo_results["detections"]:
            yolo_det = YOLODetection(
                class_id=0,  # Not needed for drawing
                class_name=det["class_name"],
                confidence=det["confidence"],
                bbox=tuple(det["bbox"]),
                category=det["category"]
            )
            detections.append(yolo_det)
        
        # Draw bounding boxes
        image_with_boxes = yolo_service.draw_detections(
            image, 
            detections,
            yolo_results.get("foe_classifications", {})
        )
        
        # Convert to base64 for response
        buffered = io.BytesIO()
        image_with_boxes.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "detection_id": detection_id,
            "image_base64": img_base64,
            "yolo_results": yolo_results
        }
        
    except Exception as e:
        logger.error(f"Error processing detection image: {e}")
        raise HTTPException(status_code=500, detail=str(e))