"""Routes for test image management."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.templates import templates
from app.models.test_image import TestImage, GroundTruthLabel

router = APIRouter(prefix="/settings/test-images", tags=["test-images"])
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
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


@router.get("/{test_image_id}/edit", response_class=HTMLResponse)
async def edit_test_image_page(
    test_image_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    """Display test image editor with bounding box drawing."""
    test_image = session.get(TestImage, test_image_id)
    if not test_image:
        raise HTTPException(status_code=404, detail="Test image not found")
    
    return templates.TemplateResponse(
        request,
        "settings/test_image_editor.html",
        {
            "test_image": test_image,
            "foe_types": ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"]
        }
    )