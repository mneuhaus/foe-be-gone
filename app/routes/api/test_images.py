"""API endpoints for test image management."""

import os
import shutil
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from PIL import Image

from app.core.database import get_session
from app.models.detection import Detection
from app.models.test_image import TestImage, GroundTruthLabel, TestRun, TestResult
from app.services.ollama_species_detector import OllamaSpeciesDetector
from app.services.litellm_species_detector import LiteLLMSpeciesDetector
from app.models.provider import Provider, ProviderModel

router = APIRouter(prefix="/api/tests", tags=["tests"])


@router.post("/from-detection/{detection_id}")
async def create_test_image_from_detection(
    detection_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a test image from an existing detection."""
    # Get the detection with device relationship
    from sqlmodel import select
    from sqlalchemy.orm import selectinload
    
    statement = select(Detection).where(Detection.id == detection_id).options(selectinload(Detection.device))
    detection = session.exec(statement).first()
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
        device_name = detection.device.name if detection.device else "Unknown"
        name = f"{device_name} - {detection.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
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
    session.flush()  # Flush to get the test_image.id
    
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


@router.get("/available-models", summary="Get available models for testing")
async def get_available_models(session: Session = Depends(get_session)):
    """Get list of available models for testing (both Ollama and cloud)."""
    import httpx
    
    # Get Ollama models
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                
                # Filter for vision-capable models
                for model in models:
                    name = model['name']
                    size_gb = model.get('size', 0) / (1024**3)
                    
                    # Check if it's a known vision model
                    if any(vision_prefix in name.lower() for vision_prefix in [
                        'llava', 'bakllava', 'moondream', 'minicpm-v', 'cogvlm', 'qwen-vl', 
                        'gemma', 'llava-gemma', 'internvl', 'phi-3-vision', 'pixtral',
                        'molmo', 'aria', 'prismatic'
                    ]):
                        description = f"Vision Model ({size_gb:.1f}GB)"
                        ollama_models.append({
                            "name": name,
                            "description": description,
                            "size_gb": round(size_gb, 1)
                        })
                
                # Sort by size (smaller models first)
                ollama_models.sort(key=lambda x: x['size_gb'])
    except Exception as e:
        print(f"Error fetching Ollama models: {e}")
    
    # Get cloud models from configured providers
    cloud_models_by_provider = {}
    try:
        providers = session.exec(
            select(Provider).where(Provider.enabled == True)
        ).all()
        
        for provider in providers:
            models = session.exec(
                select(ProviderModel)
                .where(ProviderModel.provider_id == provider.id)
                .where(ProviderModel.supports_vision == True)
                .where(ProviderModel.enabled == True)
            ).all()
            
            if models:
                provider_models = []
                for model in models:
                    cost_desc = "Free" if model.cost_per_1k_tokens == 0 else f"${model.cost_per_1k_tokens}/1K tokens"
                    provider_models.append({
                        "name": f"cloud:{provider.name}:{model.model_id}",
                        "display_name": model.display_name,
                        "description": cost_desc,
                        "provider": provider.name,
                        "model_id": model.model_id,
                        "cost_per_1k_tokens": model.cost_per_1k_tokens,
                        "type": "cloud"
                    })
                
                provider_models.sort(key=lambda x: x.get('cost_per_1k_tokens', 0))
                cloud_models_by_provider[provider.name] = {
                    "display_name": provider.display_name,
                    "models": provider_models
                }
    except Exception as e:
        print(f"Error fetching cloud models: {e}")
    
    # Format response with provider grouping
    available_models = {
        "ollama": {
            "display_name": "Local Models (Ollama)",
            "models": [
                {
                    "name": model["name"],
                    "display_name": model["name"],
                    "description": model["description"],
                    "type": "ollama"
                }
                for model in ollama_models
            ]
        },
        "providers": {}
    }
    
    # Group cloud models by provider
    for provider_name, provider_data in cloud_models_by_provider.items():
        available_models["providers"][provider_name] = {
            "display_name": provider_data["display_name"],
            "models": [
                {
                    "name": model["name"],
                    "display_name": model["display_name"],
                    "description": model["description"],
                    "provider": model["provider"],
                    "type": "cloud"
                }
                for model in provider_data["models"]
            ]
        }
    
    return available_models


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


@router.post("/test-run", summary="Create and start a test run on selected images and models")
async def create_test_run(
    data: dict,
    session: Session = Depends(get_session)
):
    """Create and start a test run on selected test images with selected models. Returns immediately and runs in background."""
    name = data.get("name", f"Test Run {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    description = data.get("description")
    test_image_ids = data.get("test_image_ids", [])
    model_names = data.get("model_names", [])
    
    if not test_image_ids:
        raise HTTPException(status_code=400, detail="No test images selected")
    if not model_names:
        raise HTTPException(status_code=400, detail="No models selected")
    
    # Validate that test images exist
    test_images = []
    for image_id in test_image_ids:
        test_image = session.get(TestImage, image_id)
        if not test_image:
            raise HTTPException(status_code=404, detail=f"Test image {image_id} not found")
        test_images.append(test_image)
    
    # Create test run
    test_run = TestRun(
        name=name,
        description=description,
        test_image_ids=test_image_ids,
        model_names=model_names,
        total_images=len(test_image_ids),
        total_models=len(model_names),
        total_tests=len(test_image_ids) * len(model_names),
        status="running",
        started_at=datetime.utcnow(),
        created_by="user"
    )
    
    session.add(test_run)
    session.commit()
    session.refresh(test_run)
    
    # Start background task to run tests
    import asyncio
    asyncio.create_task(run_test_background(test_run.id, test_image_ids, model_names))
    
    # Return immediately
    return {
        "test_run_id": test_run.id,
        "name": test_run.name,
        "status": test_run.status,
        "total_tests": test_run.total_tests,
        "message": f"Test run started with {len(test_image_ids)} images and {len(model_names)} models"
    }


async def run_test_background(test_run_id: int, test_image_ids: List[int], model_names: List[str]):
    """Run tests in the background."""
    from app.core.database import get_session
    
    # Create a new session for the background task
    with next(get_session()) as session:
        test_run = session.get(TestRun, test_run_id)
        if not test_run:
            return
        
        # Get test images
        test_images = []
        for image_id in test_image_ids:
            test_image = session.get(TestImage, image_id)
            if test_image:
                test_images.append(test_image)
        
        # Run the original test logic
        completed_tests = 0
        failed_tests = 0
        total_cost = 0.0
        total_time = 0.0
        
        import time
        
        try:
            for test_image in test_images:
                # Load image
                try:
                    with Image.open(test_image.image_path) as img:
                        image = img.copy()
                except Exception as e:
                    # Mark all tests for this image as failed
                    for model_name in model_names:
                        test_result = TestResult(
                            test_image_id=test_image.id,
                            test_run_id=test_run.id,
                            model_name=model_name,
                            provider_name="unknown",
                            inference_time_ms=0,
                            total_time_ms=0,
                            error=f"Failed to load image: {e}"
                        )
                        session.add(test_result)
                        failed_tests += 1
                    continue
                
                # Get ground truth bounding boxes
                bboxes = []
                for label in test_image.ground_truth_labels:
                    bboxes.append((label.bbox_x1, label.bbox_y1, label.bbox_x2, label.bbox_y2))
                
                # If no ground truth labels, use full image
                if not bboxes:
                    bboxes = [(0, 0, image.width, image.height)]
                
                # Test each model
                for model_name in model_names:
                    test_start = time.time()
                    
                    try:
                        # Create appropriate detector
                        if model_name.startswith("cloud:"):
                            # Parse cloud model format: cloud:provider:model_id
                            parts = model_name.split(":", 2)
                            if len(parts) != 3:
                                raise ValueError("Invalid cloud model format")
                            
                            provider_name = parts[1]
                            model_id = parts[2]
                            
                            # Get provider and model config
                            provider = session.exec(
                                select(Provider).where(Provider.name == provider_name)
                            ).first()
                            
                            if not provider:
                                raise ValueError(f"Provider {provider_name} not found")
                            
                            model_config = session.exec(
                                select(ProviderModel)
                                .where(ProviderModel.provider_id == provider.id)
                                .where(ProviderModel.model_id == model_id)
                            ).first()
                            
                            if not model_config:
                                raise ValueError(f"Model {model_id} not found")
                            
                            detector = LiteLLMSpeciesDetector(
                                provider_config={
                                    "name": provider.name,
                                    "api_key": provider.api_key,
                                    "api_base": provider.api_base,
                                    "config": provider.config
                                },
                                model_config={
                                    "model_id": model_config.model_id,
                                    "cost_per_1k_tokens": model_config.cost_per_1k_tokens,
                                    "config": model_config.config
                                }
                            )
                            provider_display = provider_name
                        else:
                            # Ollama model
                            detector = OllamaSpeciesDetector(model=model_name)
                            provider_display = "ollama"
                        
                        # Test on all bounding boxes
                        detections = []
                        test_cost = 0.0
                        
                        for i, bbox in enumerate(bboxes):
                            try:
                                result = await detector.identify_species(image, bbox)
                                detection_dict = result.model_dump()
                                detection_dict["bbox_index"] = i
                                detection_dict["bbox"] = bbox
                                detections.append(detection_dict)
                                
                                if hasattr(result, 'cost'):
                                    test_cost += result.cost
                                    
                            except Exception as e:
                                detections.append({
                                    "bbox_index": i,
                                    "bbox": bbox,
                                    "error": str(e)
                                })
                        
                        test_duration = (time.time() - test_start) * 1000  # Convert to ms
                        
                        # Calculate evaluation metrics (simplified)
                        true_positives = len([d for d in detections if "species" in d and d.get("species")])
                        false_positives = 0  # Would need ground truth comparison
                        false_negatives = max(0, len(test_image.ground_truth_labels) - true_positives)
                        
                        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
                        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
                        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                        
                        # Create test result
                        test_result = TestResult(
                            test_image_id=test_image.id,
                            test_run_id=test_run.id,
                            model_name=model_name,
                            provider_name=provider_display,
                            inference_time_ms=test_duration,
                            total_time_ms=test_duration,
                            cost=test_cost,
                            detections={"detections": detections},
                            true_positives=true_positives,
                            false_positives=false_positives,
                            false_negatives=false_negatives,
                            precision=precision,
                            recall=recall,
                            f1_score=f1_score
                        )
                        
                        session.add(test_result)
                        completed_tests += 1
                        total_cost += test_cost
                        total_time += test_duration / 1000  # Convert back to seconds
                        
                        # Commit after each test for live progress
                        session.commit()
                        
                    except Exception as e:
                        # Record failed test
                        test_result = TestResult(
                            test_image_id=test_image.id,
                            test_run_id=test_run.id,
                            model_name=model_name,
                            provider_name=provider_display if 'provider_display' in locals() else "unknown",
                            inference_time_ms=0,
                            total_time_ms=(time.time() - test_start) * 1000,
                            error=str(e)
                        )
                        session.add(test_result)
                        failed_tests += 1
                        session.commit()
            
            # Update test run with final results
            test_run.completed_tests = completed_tests
            test_run.failed_tests = failed_tests
            test_run.total_cost = total_cost
            test_run.total_time_seconds = total_time
            test_run.status = "completed"
            test_run.completed_at = datetime.utcnow()
            session.commit()
            
        except Exception as e:
            # Mark test run as failed
            test_run.status = "failed"
            test_run.completed_at = datetime.utcnow()
            session.commit()


@router.get("/test-runs", summary="List all test runs")
async def list_test_runs(
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """List all test runs with summary information."""
    query = select(TestRun).offset(skip).limit(limit).order_by(TestRun.created_at.desc())
    test_runs = session.exec(query).all()
    
    return {
        "items": [
            {
                "id": run.id,
                "name": run.name,
                "description": run.description,
                "status": run.status,
                "total_tests": run.total_tests,
                "completed_tests": run.completed_tests,
                "failed_tests": run.failed_tests,
                "total_cost": run.total_cost,
                "total_time_seconds": run.total_time_seconds,
                "created_at": run.created_at,
                "completed_at": run.completed_at
            }
            for run in test_runs
        ]
    }


@router.get("/test-runs/{test_run_id}", summary="Get detailed test run results")
async def get_test_run(
    test_run_id: int,
    session: Session = Depends(get_session)
):
    """Get detailed results for a specific test run."""
    from sqlalchemy.orm import selectinload
    
    # Get test run with all results
    query = select(TestRun).where(TestRun.id == test_run_id).options(
        selectinload(TestRun.results)
    )
    test_run = session.exec(query).first()
    
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # Group results by test image and model
    results_by_image = {}
    for result in test_run.results:
        if result.test_image_id not in results_by_image:
            test_image = session.get(TestImage, result.test_image_id)
            results_by_image[result.test_image_id] = {
                "test_image": {
                    "id": test_image.id,
                    "name": test_image.name,
                    "thumbnail_path": test_image.thumbnail_path
                },
                "results": []
            }
        
        results_by_image[result.test_image_id]["results"].append({
            "id": result.id,
            "model_name": result.model_name,
            "provider_name": result.provider_name,
            "inference_time_ms": result.inference_time_ms,
            "cost": result.cost or 0,
            "detections": result.detections,
            "true_positives": result.true_positives or 0,
            "false_positives": result.false_positives or 0,
            "false_negatives": result.false_negatives or 0,
            "precision": result.precision or 0,
            "recall": result.recall or 0,
            "f1_score": result.f1_score or 0,
            "error": result.error
        })
    
    return {
        "id": test_run.id,
        "name": test_run.name,
        "description": test_run.description,
        "status": test_run.status,
        "total_tests": test_run.total_tests,
        "completed_tests": test_run.completed_tests,
        "failed_tests": test_run.failed_tests,
        "total_cost": test_run.total_cost,
        "total_time_seconds": test_run.total_time_seconds,
        "created_at": test_run.created_at,
        "completed_at": test_run.completed_at,
        "results_by_image": results_by_image
    }


@router.delete("/test-runs/{test_run_id}", summary="Delete a test run")
async def delete_test_run(
    test_run_id: int,
    session: Session = Depends(get_session)
):
    """Delete a test run and all its results."""
    # Get test run
    test_run = session.get(TestRun, test_run_id)
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # Delete all associated test results first
    results = session.exec(
        select(TestResult).where(TestResult.test_run_id == test_run_id)
    ).all()
    
    for result in results:
        session.delete(result)
    
    # Delete the test run
    session.delete(test_run)
    session.commit()
    
    return {"message": f"Test run '{test_run.name}' deleted successfully"}