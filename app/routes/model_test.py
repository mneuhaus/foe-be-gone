"""Model testing routes for comparing species identification performance."""

import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.templates import templates
from app.models.detection import Detection
from app.services.ollama_species_detector import OllamaSpeciesDetector
import io
from PIL import Image

router = APIRouter(prefix="/model-test", tags=["model-test"])
logger = logging.getLogger(__name__)


async def get_installed_vision_models():
    """Get list of installed vision-capable models from Ollama."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                
                # Filter for vision-capable models and add descriptions
                vision_models = []
                for model in models:
                    name = model['name']
                    size_gb = model.get('size', 0) / (1024**3)
                    
                    # Check if it's a known vision model
                    if any(vision_prefix in name.lower() for vision_prefix in [
                        'llava', 'bakllava', 'moondream', 'minicpm-v', 'cogvlm', 'qwen-vl', 
                        'gemma', 'llava-gemma', 'internvl', 'phi-3-vision', 'pixtral',
                        'molmo', 'aria', 'prismatic'
                    ]):
                        # Generate description based on model name and size
                        description = generate_model_description(name, size_gb)
                        vision_models.append({
                            "name": name,
                            "description": description,
                            "size_gb": round(size_gb, 1)
                        })
                
                # Sort by size (smaller models first for better performance on M4)
                vision_models.sort(key=lambda x: x['size_gb'])
                return vision_models
            else:
                logger.error(f"Failed to get Ollama models: HTTP {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return []


def generate_model_description(name: str, size_gb: float) -> str:
    """Generate a descriptive label for a model based on its name and size."""
    name_lower = name.lower()
    
    # Speed indicators based on size
    if size_gb < 2:
        speed = "⚡⚡⚡⚡"
        speed_desc = "Ultra Fast"
    elif size_gb < 4:
        speed = "⚡⚡⚡"
        speed_desc = "Very Fast"
    elif size_gb < 6:
        speed = "⚡⚡"
        speed_desc = "Fast"
    elif size_gb < 10:
        speed = "⚡"
        speed_desc = "Moderate"
    else:
        speed = "🐌"
        speed_desc = "Slow"
    
    # Model type detection
    if "moondream" in name_lower:
        model_type = "Tiny & Efficient"
    elif "phi3" in name_lower or "phi-3" in name_lower:
        model_type = "M4 Optimized"
    elif "minicpm" in name_lower:
        model_type = "Edge Optimized"
    elif "bakllava" in name_lower:
        model_type = "Alternative Architecture"
    elif "gemma" in name_lower:
        model_type = "Gemma Vision"
    elif "llava-gemma" in name_lower:
        model_type = "LLaVA-Gemma"
    elif "internvl" in name_lower:
        model_type = "InternVL"
    elif "pixtral" in name_lower:
        model_type = "Pixtral (Mistral Vision)"
    elif "molmo" in name_lower:
        model_type = "Molmo (AllenAI)"
    elif "aria" in name_lower:
        model_type = "Aria (Rhymes AI)"
    elif "prismatic" in name_lower:
        model_type = "Prismatic VLM"
    elif "vicuna" in name_lower:
        model_type = "Vicuna Base"
    elif "mistral" in name_lower:
        model_type = "Mistral Base"
    elif "cogvlm" in name_lower:
        model_type = "CogVLM"
    elif "qwen" in name_lower:
        model_type = "Qwen Vision"
    elif "llava" in name_lower:
        model_type = "LLaVA"
    else:
        model_type = "Vision Model"
    
    # Quantization detection
    quant = ""
    if "q4_0" in name_lower:
        quant = ", 4-bit"
    elif "q8_0" in name_lower:
        quant = ", 8-bit"
    elif "q2" in name_lower:
        quant = ", 2-bit"
    
    return f"{model_type} ({size_gb:.1f}GB{quant}) {speed} {speed_desc}"


@router.get("/{detection_id}", response_class=HTMLResponse)
async def model_test_page(
    detection_id: int,
    request: Request,
    db: Session = Depends(get_session)
):
    """Display model testing page for a specific detection."""
    # Get detection
    detection = db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    # Get installed vision models from Ollama
    available_models = await get_installed_vision_models()
    
    # If no models found, show helpful message
    if not available_models:
        available_models = [{
            "name": "no-models-found",
            "description": "No vision models found. Install with: ollama pull llava-phi3:3.8b-mini-q4_0",
            "size_gb": 0
        }]
    
    return templates.TemplateResponse(
        request,
        "model_test.html",
        {
            "detection": detection,
            "available_models": available_models
        }
    )


async def warmup_model(model_name: str) -> Dict[str, Any]:
    """Warmup model with a simple text prompt to ensure it's loaded."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            warmup_start = time.time()
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Ready?",
                    "stream": False,
                    "options": {
                        "num_predict": 1,  # Just one token
                        "temperature": 0
                    }
                }
            )
            warmup_duration = time.time() - warmup_start
            
            if response.status_code == 200:
                result = response.json()
                load_time = result.get('load_duration', 0) / 1e9 if 'load_duration' in result else 0
                return {
                    "success": True,
                    "warmup_duration": warmup_duration,
                    "load_duration": load_time,
                    "model_loaded": load_time < 1.0  # Model was already loaded if < 1s
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "warmup_duration": warmup_duration
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "warmup_duration": time.time() - warmup_start if 'warmup_start' in locals() else 0
        }


@router.post("/api/test-model")
async def test_model(
    data: dict,
    db: Session = Depends(get_session)
):
    """Test a specific model on a detection with proper warmup."""
    detection_id = data.get("detection_id")
    model_name = data.get("model_name")
    
    if not detection_id or not model_name:
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Get detection
    detection = db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    # Load image
    try:
        with open(detection.image_path, 'rb') as f:
            image_data = f.read()
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load image: {e}")
    
    # Get bounding boxes from YOLO results if available
    bboxes = []
    if detection.ai_response and "yolo_results" in detection.ai_response:
        yolo_detections = detection.ai_response["yolo_results"].get("detections", [])
        for det in yolo_detections:
            if "bbox" in det:
                bboxes.append(tuple(det["bbox"]))
    
    if not bboxes:
        # Use full image if no detections
        bboxes = [(0, 0, image.width, image.height)]
    
    # Step 1: Warmup model to ensure it's loaded
    logger.info(f"Warming up model {model_name}...")
    warmup_result = await warmup_model(model_name)
    
    if not warmup_result["success"]:
        return {
            "model": model_name,
            "duration_seconds": 0,
            "duration_formatted": "0s",
            "error": f"Model warmup failed: {warmup_result.get('error', 'Unknown error')}",
            "success": False,
            "warmup_info": warmup_result
        }
    
    # Step 2: Test the model (pure inference time)
    inference_start = time.time()
    results = []
    
    try:
        # Create detector with specific model
        detector = OllamaSpeciesDetector(model=model_name)
        
        # Test each bounding box
        for i, bbox in enumerate(bboxes):
            try:
                # Get the cropped image that will be sent to the model
                cropped_image = detector.crop_image_with_padding(image, bbox)
                
                # Save the cropped image temporarily for display
                import os
                from pathlib import Path
                temp_dir = Path("data") / "temp_crops"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Clean filename for filesystem
                clean_model_name = model_name.replace(':', '_').replace('/', '_')
                crop_filename = f"test_{detection_id}_{clean_model_name}_{i}.jpg"
                crop_path = temp_dir / crop_filename
                cropped_image.save(crop_path, "JPEG", quality=90)
                
                result = await detector.identify_species(image, bbox)
                results.append({
                    "bbox_index": i,
                    "bbox": bbox,
                    "result": result.model_dump(),
                    "cropped_image_path": str(crop_path),
                    "cropped_image_url": f"/data/temp_crops/{crop_filename}",
                    "crop_size": f"{cropped_image.width}x{cropped_image.height}"
                })
            except Exception as e:
                results.append({
                    "bbox_index": i,
                    "bbox": bbox,
                    "error": str(e)
                })
        
        inference_duration = time.time() - inference_start
        total_duration = warmup_result["warmup_duration"] + inference_duration
        
        return {
            "model": model_name,
            "duration_seconds": round(inference_duration, 3),  # Pure inference time
            "duration_formatted": f"{inference_duration:.1f}s" if inference_duration >= 1 else f"{int(inference_duration * 1000)}ms",
            "total_duration_seconds": round(total_duration, 3),  # Including warmup
            "results": results,
            "success": True,
            "warmup_info": {
                "warmup_duration": round(warmup_result["warmup_duration"], 3),
                "load_duration": round(warmup_result.get("load_duration", 0), 3),
                "model_was_loaded": warmup_result.get("model_loaded", False)
            }
        }
        
    except Exception as e:
        inference_duration = time.time() - inference_start
        return {
            "model": model_name,
            "duration_seconds": round(inference_duration, 3),
            "duration_formatted": f"{inference_duration:.1f}s",
            "error": str(e),
            "success": False,
            "warmup_info": warmup_result
        }


@router.get("/api/installed-models")
async def get_installed_models():
    """Get list of currently installed vision models."""
    models = await get_installed_vision_models()
    return {"models": models}


@router.delete("/api/cleanup-temp")
async def cleanup_temp_images():
    """Clean up temporary crop images older than 1 hour."""
    import os
    import time
    from pathlib import Path
    
    temp_dir = Path("data") / "temp_crops"
    if not temp_dir.exists():
        return {"message": "No temp directory found"}
    
    cleaned = 0
    current_time = time.time()
    one_hour_ago = current_time - 3600  # 1 hour in seconds
    
    try:
        for file_path in temp_dir.glob("test_*.jpg"):
            if file_path.stat().st_mtime < one_hour_ago:
                file_path.unlink()
                cleaned += 1
        
        return {"message": f"Cleaned up {cleaned} temporary images"}
    except Exception as e:
        return {"error": f"Cleanup failed: {e}"}


@router.get("/api/check-model/{model_name}")
async def check_model_availability(model_name: str):
    """Check if a specific model is available in Ollama."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                # Check if model exists
                model_exists = any(m['name'] == model_name for m in models)
                return {
                    "available": model_exists,
                    "all_models": [m['name'] for m in models]
                }
    except:
        pass
    
    return {"available": False, "error": "Could not connect to Ollama"}