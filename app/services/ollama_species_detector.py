"""Species detection using Ollama with vision models."""

import base64
import json
import logging
from typing import Optional, Tuple, List
from PIL import Image
import io
import httpx
from pydantic import BaseModel

from app.core.config import config

logger = logging.getLogger(__name__)


class SpeciesIdentification(BaseModel):
    """Single species identification result."""
    species: str
    foe_type: Optional[str] = None
    confidence: float
    description: str


class SpeciesDetectionResult(BaseModel):
    """Result from species detection."""
    identifications: List[SpeciesIdentification]
    raw_response: str
    error: Optional[str] = None
    cost: float = 0.0  # Ollama is free/local


class OllamaSpeciesDetector:
    """Species detector using Ollama with vision models."""
    
    def __init__(self, 
                 model: str = "llava:13b",  # or "bakllava", "llava:34b" for better quality
                 ollama_host: str = "http://localhost:11434"):
        """
        Initialize the Ollama species detector.
        
        Args:
            model: Ollama model to use (must support vision)
            ollama_host: Ollama API endpoint
        """
        self.model = model
        self.ollama_host = ollama_host
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Check if Ollama is available
        self._check_ollama_availability()
    
    def _check_ollama_availability(self):
        """Check if Ollama is running and model is available."""
        try:
            response = httpx.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if self.model not in model_names:
                    logger.warning(f"Model {self.model} not found in Ollama. Available models: {model_names}")
                    logger.info(f"Pull the model with: ollama pull {self.model}")
                else:
                    logger.info(f"Ollama species detector initialized with model: {self.model}")
            else:
                logger.error(f"Ollama API returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama at {self.ollama_host}: {e}")
            logger.info("Make sure Ollama is running: https://ollama.ai")
    
    def crop_image_with_padding(self, image: Image.Image, bbox: Tuple[int, int, int, int], 
                               padding_percent: float = 0.5, min_size: int = None) -> Image.Image:
        """
        Crop image with padding around bounding box and minimum size enforcement.
        
        Args:
            image: PIL Image object
            bbox: Bounding box (x1, y1, x2, y2) of the animal
            padding_percent: Percentage of bbox size to add as padding (default: 0.5 = 50%)
            min_size: Minimum crop size in pixels (default: from config)
            
        Returns:
            Cropped PIL Image
        """
        x1, y1, x2, y2 = bbox
        
        # Calculate bbox dimensions
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        
        # Use 50% padding like identify_species method
        padding_x = bbox_width * padding_percent
        padding_y = bbox_height * padding_percent
        
        # Calculate initial crop with padding
        crop_x1 = x1 - padding_x
        crop_y1 = y1 - padding_y
        crop_x2 = x2 + padding_x
        crop_y2 = y2 + padding_y
        
        # Calculate current crop dimensions
        crop_width = crop_x2 - crop_x1
        crop_height = crop_y2 - crop_y1
        
        # Enforce minimum size from config (default 224px)
        if min_size is None:
            min_size = config.SPECIES_MIN_CROP_SIZE
        
        if crop_width < min_size:
            # Expand width to minimum
            width_deficit = min_size - crop_width
            expand_x = width_deficit / 2
            crop_x1 -= expand_x
            crop_x2 += expand_x
            crop_width = min_size
        
        if crop_height < min_size:
            # Expand height to minimum
            height_deficit = min_size - crop_height
            expand_y = height_deficit / 2
            crop_y1 -= expand_y
            crop_y2 += expand_y
            crop_height = min_size
        
        # Same boundary logic as identify_species method
        if crop_width > image.width:
            crop_x1 = 0
            crop_x2 = image.width
        else:
            if crop_x1 < 0:
                crop_x2 -= crop_x1
                crop_x1 = 0
            if crop_x2 > image.width:
                crop_x1 -= (crop_x2 - image.width)
                crop_x2 = image.width
                crop_x1 = max(0, crop_x1)
        
        if crop_height > image.height:
            crop_y1 = 0
            crop_y2 = image.height
        else:
            if crop_y1 < 0:
                crop_y2 -= crop_y1
                crop_y1 = 0
            if crop_y2 > image.height:
                crop_y1 -= (crop_y2 - image.height)
                crop_y2 = image.height
                crop_y1 = max(0, crop_y1)
        
        # Final boundary check
        crop_x1 = max(0, crop_x1)
        crop_y1 = max(0, crop_y1)
        crop_x2 = min(image.width, crop_x2)
        crop_y2 = min(image.height, crop_y2)
        
        # Crop and return the image
        return image.crop((crop_x1, crop_y1, crop_x2, crop_y2))

    async def identify_species(self, image: Image.Image, bbox: Tuple[int, int, int, int]) -> SpeciesDetectionResult:
        """
        Identify species in a cropped region of an image.
        
        Args:
            image: PIL Image object
            bbox: Bounding box (x1, y1, x2, y2) of the animal
            
        Returns:
            SpeciesDetectionResult with identification details
        """
        try:
            # Crop and prepare image with minimum size enforcement
            x1, y1, x2, y2 = bbox
            
            # Calculate bbox dimensions
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            
            # Use 50% padding like Qwen detector for consistency
            padding_percent = 0.5
            padding_x = bbox_width * padding_percent
            padding_y = bbox_height * padding_percent
            
            # Calculate initial crop with padding
            crop_x1 = x1 - padding_x
            crop_y1 = y1 - padding_y
            crop_x2 = x2 + padding_x
            crop_y2 = y2 + padding_y
            
            # Calculate current crop dimensions
            crop_width = crop_x2 - crop_x1
            crop_height = crop_y2 - crop_y1
            
            # Enforce minimum size from config (default 224px)
            min_size = config.SPECIES_MIN_CROP_SIZE
            
            if crop_width < min_size:
                # Expand width to minimum
                width_deficit = min_size - crop_width
                expand_x = width_deficit / 2
                crop_x1 -= expand_x
                crop_x2 += expand_x
                crop_width = min_size
            
            if crop_height < min_size:
                # Expand height to minimum
                height_deficit = min_size - crop_height
                expand_y = height_deficit / 2
                crop_y1 -= expand_y
                crop_y2 += expand_y
                crop_height = min_size
            
            # Ensure crop stays within image bounds
            if crop_width > image.width:
                crop_x1 = 0
                crop_x2 = image.width
            else:
                if crop_x1 < 0:
                    crop_x2 -= crop_x1
                    crop_x1 = 0
                if crop_x2 > image.width:
                    crop_x1 -= (crop_x2 - image.width)
                    crop_x2 = image.width
                    crop_x1 = max(0, crop_x1)
            
            if crop_height > image.height:
                crop_y1 = 0
                crop_y2 = image.height
            else:
                if crop_y1 < 0:
                    crop_y2 -= crop_y1
                    crop_y1 = 0
                if crop_y2 > image.height:
                    crop_y1 -= (crop_y2 - image.height)
                    crop_y2 = image.height
                    crop_y1 = max(0, crop_y1)
            
            # Final boundary check
            crop_x1 = max(0, crop_x1)
            crop_y1 = max(0, crop_y1)
            crop_x2 = min(image.width, crop_x2)
            crop_y2 = min(image.height, crop_y2)
            
            # Crop the image
            cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            logger.debug(f"Cropped for Ollama: bbox {bbox} (size: {bbox_width:.0f}x{bbox_height:.0f}) "
                        f"to ({crop_x1:.0f}, {crop_y1:.0f}, {crop_x2:.0f}, {crop_y2:.0f}), "
                        f"final size: {cropped.width}x{cropped.height} (min: {min_size}px)")
            
            # Convert to base64
            buffered = io.BytesIO()
            cropped.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Prepare the prompt
            prompt = """You are a wildlife expert analyzing a security camera image of an animal. 

Identify the animal species and provide a structured response in JSON format:
{
  "identifications": [
    {
      "species": "specific species name (e.g., 'Norway Rat', 'House Cat', 'European Magpie')",
      "foe_type": "category if it's a pest/foe: RATS, CROWS, CATS, HERONS, PIGEONS, or null if friendly",
      "confidence": 0.0-1.0,
      "description": "brief description of identifying features"
    }
  ]
}

Focus on:
1. Specific species identification (not just general categories)
2. Distinguishing features visible in the image
3. Whether this animal is typically considered a pest/foe in gardens and farms
4. Be precise - if unsure, indicate lower confidence

Respond ONLY with valid JSON."""

            # Call Ollama API
            response = await self.client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [img_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent results
                        "top_p": 0.9,
                        "seed": 42  # For reproducibility
                    }
                }
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return SpeciesDetectionResult(
                    identifications=[],
                    raw_response="",
                    error=error_msg
                )
            
            # Parse response
            result = response.json()
            raw_response = result.get("response", "")
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    parsed = json.loads(json_str)
                    
                    # Convert to our format
                    identifications = []
                    for item in parsed.get("identifications", []):
                        # Map foe_type strings to our enum values
                        foe_type = item.get("foe_type")
                        if foe_type and isinstance(foe_type, str):
                            foe_type = foe_type.upper()
                            if foe_type not in ["RATS", "CROWS", "CATS", "HERONS", "PIGEONS"]:
                                foe_type = None
                        
                        identifications.append(SpeciesIdentification(
                            species=item.get("species", "Unknown"),
                            foe_type=foe_type,
                            confidence=float(item.get("confidence", 0.5)),
                            description=item.get("description", "")
                        ))
                    
                    return SpeciesDetectionResult(
                        identifications=identifications,
                        raw_response=raw_response
                    )
                else:
                    logger.error(f"No JSON found in Ollama response: {raw_response}")
                    return SpeciesDetectionResult(
                        identifications=[],
                        raw_response=raw_response,
                        error="No valid JSON in response"
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Ollama response as JSON: {e}")
                return SpeciesDetectionResult(
                    identifications=[],
                    raw_response=raw_response,
                    error=f"JSON parse error: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Error during Ollama species identification: {e}")
            return SpeciesDetectionResult(
                identifications=[],
                raw_response="",
                error=str(e)
            )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_detector():
        detector = OllamaSpeciesDetector()
        
        # Test with a dummy image
        test_image = Image.new('RGB', (640, 480), color='white')
        bbox = (100, 100, 200, 200)
        
        result = await detector.identify_species(test_image, bbox)
        print(f"Result: {result}")
        
        await detector.close()
    
    asyncio.run(test_detector())