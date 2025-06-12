"""Routes for test image management."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.templates import templates
from app.models.test_image import TestImage, GroundTruthLabel, TestRun

router = APIRouter(prefix="/settings/tests", tags=["tests"])
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def tests_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display main tests page with test runs list."""
    # Get all test runs
    test_runs = session.exec(
        select(TestRun).order_by(TestRun.created_at.desc())
    ).all()
    
    # Get test images count
    test_images = session.exec(select(TestImage)).all()
    
    return templates.TemplateResponse(
        request,
        "settings/tests.html",
        {
            "test_runs": test_runs,
            "test_images": test_images
        }
    )


@router.get("/images", response_class=HTMLResponse)
async def test_images_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display test images management page."""
    # Get all test images with their labels
    test_images = session.exec(
        select(TestImage).order_by(TestImage.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        request,
        "settings/test_images.html",
        {
            "test_images": test_images
        }
    )


@router.get("/new", response_class=HTMLResponse)
async def new_test_run_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display new test run page (image selection)."""
    # Get all test images with their labels
    test_images = session.exec(
        select(TestImage).order_by(TestImage.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        request,
        "settings/test_images.html",  # Reuse the same template for now
        {
            "test_images": test_images,
            "new_test_mode": True  # Flag to show this is for new test creation
        }
    )


@router.get("/images/{test_image_id}/edit", response_class=HTMLResponse)
async def edit_test_image_page(
    test_image_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """Display test image editor with bounding box drawing."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    # Convert ground truth labels to JSON-serializable format
    labels_json = [
        {
            "id": label.id,
            "bbox_x1": label.bbox_x1,
            "bbox_y1": label.bbox_y1,
            "bbox_x2": label.bbox_x2,
            "bbox_y2": label.bbox_y2,
            "species": label.species,
            "foe_type": label.foe_type,
            "confidence": label.confidence,
            "notes": label.notes
        }
        for label in test_image.ground_truth_labels
    ]
    
    return templates.TemplateResponse(
        request,
        "settings/test_image_editor.html",
        {
            "test_image": test_image,
            "labels_json": labels_json,
            "foe_types": ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"]
        }
    )