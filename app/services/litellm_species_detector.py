"""Species detection using LiteLLM for cloud AI providers."""

import base64
import json
import logging
import os
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image
import io
import litellm
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
    cost: float = 0.0
    provider: str = ""
    model: str = ""


class LiteLLMSpeciesDetector:
    """Species detector using LiteLLM for cloud AI providers."""
    
    def __init__(self, provider_config: Dict[str, Any], model_config: Dict[str, Any]):
        """
        Initialize the LiteLLM species detector.
        
        Args:
            provider_config: Provider configuration from database
            model_config: Model configuration from database
        """
        self.provider_config = provider_config
        self.model_config = model_config
        self.provider_name = provider_config.get("name", "unknown")
        self.model_id = model_config.get("model_id", "")
        
        # Set up LiteLLM configuration
        self._setup_litellm()
        
        logger.info(f"LiteLLM species detector initialized with {self.provider_name}/{self.model_id}")
    
    def _setup_litellm(self):
        """Configure LiteLLM - let it handle provider routing."""
        # No need for manual environment variable setup
        # LiteLLM will handle this when we pass api_key and api_base directly
        pass
    
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
        
        # Use 50% padding like other detectors for consistency
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
        
        # Same boundary logic as other detectors
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
            cropped = self.crop_image_with_padding(image, bbox)
            
            logger.debug(f"Cropped for {self.provider_name}: bbox {bbox} to final size: {cropped.width}x{cropped.height}")
            
            # Convert to base64
            buffered = io.BytesIO()
            cropped.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Log image size for debugging
            logger.debug(f"Sending image to {self.provider_name}: size={len(img_base64)} chars, crop_size={cropped.width}x{cropped.height}")
            
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

            # Call LiteLLM API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Let LiteLLM handle everything! Just pass the model name and credentials
            logger.debug(f"Calling LiteLLM with model: {self.model_id}, provider: {self.provider_name}")
            
            try:
                response = await litellm.acompletion(
                    model=self.model_id,  # Just the model name - let LiteLLM route it
                    messages=messages,
                    api_key=self.provider_config.get("api_key"),  # Let LiteLLM handle auth
                    api_base=self.provider_config.get("api_base"),  # For custom endpoints
                    max_tokens=1000,
                    temperature=0.1  # LiteLLM should handle compatibility automatically
                )
            except Exception as api_error:
                logger.error(f"LiteLLM API call failed: {api_error}")
                # Re-raise with more context
                raise Exception(f"LiteLLM API error for {self.provider_name}/{self.model_id}: {str(api_error)}")
            
            # Extract response content
            raw_response = response.choices[0].message.content or ""
            
            # Log the raw response for debugging
            logger.debug(f"Raw response from {self.provider_name}: {raw_response}")
            
            # Calculate cost if usage info is available
            cost = 0.0
            if hasattr(response, 'usage') and response.usage:
                total_tokens = response.usage.total_tokens
                cost_per_1k = self.model_config.get("cost_per_1k_tokens", 0.0)
                if cost_per_1k and total_tokens:
                    cost = (total_tokens / 1000) * cost_per_1k
            
            # Check if we have a response to parse
            if not raw_response or raw_response.strip() == "":
                logger.error(f"Empty response from {self.provider_name}")
                return SpeciesDetectionResult(
                    identifications=[],
                    raw_response=raw_response,
                    error="Empty response from model",
                    cost=cost,
                    provider=self.provider_name,
                    model=self.model_id
                )
            
            # Parse JSON response
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
                        raw_response=raw_response,
                        cost=cost,
                        provider=self.provider_name,
                        model=self.model_id
                    )
                else:
                    logger.error(f"No JSON found in {self.provider_name} response: {raw_response}")
                    return SpeciesDetectionResult(
                        identifications=[],
                        raw_response=raw_response,
                        error="No valid JSON in response",
                        cost=cost,
                        provider=self.provider_name,
                        model=self.model_id
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {self.provider_name} response as JSON: {e}")
                return SpeciesDetectionResult(
                    identifications=[],
                    raw_response=raw_response,
                    error=f"JSON parse error: {str(e)}",
                    cost=cost,
                    provider=self.provider_name,
                    model=self.model_id
                )
                
        except Exception as e:
            logger.error(f"Error during {self.provider_name} species identification: {e}", exc_info=True)
            # Add more detailed error information
            error_msg = str(e)
            if hasattr(e, 'response'):
                try:
                    error_details = e.response.json() if hasattr(e.response, 'json') else str(e.response)
                    error_msg = f"{error_msg} - Response: {error_details}"
                except:
                    pass
            
            return SpeciesDetectionResult(
                identifications=[],
                raw_response="",
                error=error_msg,
                provider=self.provider_name,
                model=self.model_id
            )
    

def create_cloud_detector(provider_config: Dict[str, Any], model_config: Dict[str, Any]) -> LiteLLMSpeciesDetector:
    """Factory function to create a cloud detector."""
    return LiteLLMSpeciesDetector(provider_config, model_config)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_detector():
        # Example provider config
        provider_config = {
            "name": "openai",
            "api_key": "your-api-key",
            "config": {"temperature": 0.1}
        }
        
        model_config = {
            "model_id": "gpt-4o-mini",
            "cost_per_1k_tokens": 0.00015,
            "config": {}
        }
        
        detector = LiteLLMSpeciesDetector(provider_config, model_config)
        
        # Test with a dummy image
        test_image = Image.new('RGB', (640, 480), color='white')
        bbox = (100, 100, 200, 200)
        
        result = await detector.identify_species(test_image, bbox)
        print(f"Result: {result}")
    
    asyncio.run(test_detector())