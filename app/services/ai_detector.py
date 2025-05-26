"""AI-powered foe detection service using OpenAI GPT-4o."""
import os
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from app.models.detection import FoeType
import json


class DetectedFoe(BaseModel):
    """Structured output for a detected foe."""
    foe_type: str = Field(description="Type of foe: rodent, crow, crow_like, cat, or unknown")
    confidence: float = Field(description="Confidence score between 0 and 1", ge=0.0, le=1.0)
    bounding_box: Optional[Dict[str, int]] = Field(
        default=None,
        description="Approximate bounding box with x, y, width, height in pixels"
    )
    description: str = Field(description="Brief description of what was detected")


class DetectionResult(BaseModel):
    """Structured output for the detection result."""
    foes_detected: bool = Field(description="Whether any foes were detected")
    foes: List[DetectedFoe] = Field(default_factory=list, description="List of detected foes")
    scene_description: str = Field(description="Brief description of the overall scene")


class AIDetector:
    """AI-powered foe detection using OpenAI GPT-4o."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI detector."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")
        
        self.client = OpenAI(api_key=self.api_key)
        
    def detect_foes(self, image_data: bytes) -> DetectionResult:
        """
        Detect foes in an image using GPT-4o.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            DetectionResult with structured detection data
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare the prompt
        system_prompt = """You are a wildlife detection system. Analyze the provided image and identify any of the following target animals (foes):

1. **Rodents** (rats, mice, etc.)
2. **Crows** (carrion crow, hooded crow)
3. **Crow-like birds** (magpies, jackdaws, ravens, etc.)
4. **Cats** (domestic cats)

For each detected foe, provide:
- The type (use exactly: "rodent", "crow", "crow_like", or "cat")
- A confidence score (0.0 to 1.0)
- An approximate bounding box if the animal is clearly visible
- A brief description

If the animal doesn't match any category, mark it as "unknown".
Be conservative with confidence scores - only high confidence for clear, unobstructed views."""

        user_prompt = "Analyze this image for the presence of any foes (rodents, crows, crow-like birds, or cats)."
        
        try:
            # Call GPT-4o with structured output
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format=DetectionResult,
                temperature=0.3  # Lower temperature for more consistent detection
            )
            
            result = response.choices[0].message.parsed
            
            # Map foe types to our enum
            for foe in result.foes:
                if foe.foe_type == "crow_like":
                    foe.foe_type = FoeType.CROW_LIKE.value
                elif foe.foe_type == "rodent":
                    foe.foe_type = FoeType.RODENT.value
                elif foe.foe_type == "crow":
                    foe.foe_type = FoeType.CROW.value
                elif foe.foe_type == "cat":
                    foe.foe_type = FoeType.CAT.value
                else:
                    foe.foe_type = FoeType.UNKNOWN.value
                    
            return result
            
        except Exception as e:
            # Return empty result on error
            return DetectionResult(
                foes_detected=False,
                foes=[],
                scene_description=f"Error during detection: {str(e)}"
            )
    
    def test_connection(self) -> bool:
        """Test the connection to OpenAI API."""
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False