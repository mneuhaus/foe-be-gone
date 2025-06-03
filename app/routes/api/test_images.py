"""API endpoints for test image management."""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from PIL import Image

from app.core.database import get_session
from app.models.detection import Detection
from app.models.test_image import TestImage, GroundTruthLabel, TestRun, TestResult

router = APIRouter(prefix="/api/test-images", tags=["test-images"])


@router.post("/from-detection/{detection_id}")
async def create_test_image_from_detection(
    detection_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a test image from an existing detection."""
    # Get the detection
    detection = session.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    if not detection.image_path or not os.path.exists(detection.image_path):
        raise HTTPException(status_code=400, detail="Detection image not found")
    
    # Create test images directory
    test_images_dir = Path("data/test_images")
    test_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    source_path = Path(detection.image_path)
    new_filename = f"test_{timestamp}_{source_path.name}"
    new_path = test_images_dir / new_filename
    
    # Copy the image
    shutil.copy2(detection.image_path, new_path)
    
    # Open image to get dimensions
    with Image.open(new_path) as img:
        width, height = img.size
    
    # Create thumbnail
    thumbnail_path = test_images_dir / f"thumb_{new_filename}"
    with Image.open(new_path) as img:
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        img.save(thumbnail_path, "JPEG", quality=85)
    
    # Use provided name or generate from detection info
    if not name:
        name = f"{detection.device_name} - {detection.detected_at.strftime('%Y-%m-%d %H:%M')}"
    
    # Create test image record
    test_image = TestImage(
        name=name,
        description=description,
        image_path=str(new_path),
        thumbnail_path=str(thumbnail_path),
        source_detection_id=detection_id,
        source_type="detection",
        image_width=width,
        image_height=height
    )
    
    session.add(test_image)
    
    # If detection has YOLO results, create initial ground truth labels
    if detection.ai_response and "yolo_results" in detection.ai_response:
        yolo_results = detection.ai_response["yolo_results"]
        if "detections" in yolo_results:
            for yolo_det in yolo_results["detections"]:
                if "bbox" in yolo_det:
                    bbox = yolo_det["bbox"]
                    
                    # Create ground truth label from YOLO detection
                    label = GroundTruthLabel(
                        test_image_id=test_image.id,
                        bbox_x1=int(bbox[0]),
                        bbox_y1=int(bbox[1]),
                        bbox_x2=int(bbox[2]),
                        bbox_y2=int(bbox[3]),
                        species=yolo_det.get("class_name", "Unknown"),
                        confidence=yolo_det.get("confidence", 0.5),
                        notes="Auto-generated from YOLO detection",
                        created_by="system"
                    )
                    
                    # Map YOLO category to foe_type if possible
                    category = yolo_det.get("category", "").upper()
                    if category in ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"]:
                        label.foe_type = category
                    
                    session.add(label)
    
    session.commit()
    session.refresh(test_image)
    
    return {
        "id": test_image.id,
        "name": test_image.name,
        "image_path": test_image.image_path,
        "thumbnail_path": test_image.thumbnail_path,
        "ground_truth_count": len(test_image.ground_truth_labels)
    }


@router.get("")
async def list_test_images(
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """List all test images."""
    query = select(TestImage).offset(skip).limit(limit)
    test_images = session.exec(query).all()
    
    return {
        "items": [
            {
                "id": img.id,
                "name": img.name,
                "description": img.description,
                "thumbnail_path": img.thumbnail_path,
                "source_type": img.source_type,
                "created_at": img.created_at,
                "ground_truth_count": len(img.ground_truth_labels)
            }
            for img in test_images
        ],
        "total": session.exec(select(TestImage)).count()
    }


@router.get("/{test_image_id}")
async def get_test_image(
    test_image_id: int,
    session: Session = Depends(get_session)
):
    """Get a test image with its ground truth labels."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    return {
        "id": test_image.id,
        "name": test_image.name,
        "description": test_image.description,
        "image_path": test_image.image_path,
        "thumbnail_path": test_image.thumbnail_path,
        "image_width": test_image.image_width,
        "image_height": test_image.image_height,
        "source_type": test_image.source_type,
        "created_at": test_image.created_at,
        "ground_truth_labels": [
            {
                "id": label.id,
                "bbox": [label.bbox_x1, label.bbox_y1, label.bbox_x2, label.bbox_y2],
                "foe_type": label.foe_type,
                "species": label.species,
                "confidence": label.confidence,
                "notes": label.notes
            }
            for label in test_image.ground_truth_labels
        ]
    }


@router.put("/{test_image_id}")
async def update_test_image(
    test_image_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Update test image metadata."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    test_image.name = name
    test_image.description = description
    test_image.updated_at = datetime.utcnow()
    
    session.add(test_image)
    session.commit()
    
    return {"success": True}


@router.delete("/{test_image_id}")
async def delete_test_image(
    test_image_id: int,
    session: Session = Depends(get_session)
):
    """Delete a test image and its files."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    # Delete files
    for path in [test_image.image_path, test_image.thumbnail_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
    
    # Delete from database (cascade will handle labels and results)
    session.delete(test_image)
    session.commit()
    
    return {"success": True}


@router.post("/{test_image_id}/labels")
async def add_ground_truth_label(
    test_image_id: int,
    bbox_x1: int = Form(...),
    bbox_y1: int = Form(...),
    bbox_x2: int = Form(...),
    bbox_y2: int = Form(...),
    species: str = Form(...),
    foe_type: Optional[str] = Form(None),
    confidence: float = Form(1.0),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Add a ground truth label to a test image."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    label = GroundTruthLabel(
        test_image_id=test_image_id,
        bbox_x1=bbox_x1,
        bbox_y1=bbox_y1,
        bbox_x2=bbox_x2,
        bbox_y2=bbox_y2,
        species=species,
        foe_type=foe_type if foe_type in ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"] else None,
        confidence=confidence,
        notes=notes,
        created_by="user"
    )
    
    session.add(label)
    session.commit()
    session.refresh(label)
    
    return {
        "id": label.id,
        "bbox": [label.bbox_x1, label.bbox_y1, label.bbox_x2, label.bbox_y2],
        "species": label.species,
        "foe_type": label.foe_type
    }


@router.put("/{test_image_id}/labels/{label_id}")
async def update_ground_truth_label(
    test_image_id: int,
    label_id: int,
    species: str = Form(...),
    foe_type: Optional[str] = Form(None),
    confidence: float = Form(1.0),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Update a ground truth label."""
    label = session.get(GroundTruthLabel, label_id)
    if not label or label.test_image_id != test_image_id:
        raise HTTPException(status_code=404, detail="Label not found")
    
    label.species = species
    label.foe_type = foe_type if foe_type in ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"] else None
    label.confidence = confidence
    label.notes = notes
    
    session.add(label)
    session.commit()
    
    return {"success": True}


@router.delete("/{test_image_id}/labels/{label_id}")
async def delete_ground_truth_label(
    test_image_id: int,
    label_id: int,
    session: Session = Depends(get_session)
):
    """Delete a ground truth label."""
    label = session.get(GroundTruthLabel, label_id)
    if not label or label.test_image_id != test_image_id:
        raise HTTPException(status_code=404, detail="Label not found")
    
    session.delete(label)
    session.commit()
    
    return {"success": True}