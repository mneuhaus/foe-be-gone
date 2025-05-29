"""AI-powered foe detection service using LiteLLM for multi-model support."""
import base64
import json
import logging
from typing import List, Dict, Any, Optional

import litellm
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import config
from app.models.detection import FoeType
from app.services.settings_service import SettingsService

# Logger for AI detector
logger = logging.getLogger(__name__)

# Set LiteLLM logging level to reduce noise
litellm.set_verbose = False


class DetectedFoe(BaseModel):
    """Structured output for a detected foe."""
    foe_type: str = Field(description="Type of foe: RATS, CROWS, CATS, or UNKNOWN (must match exactly, uppercase)")
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
    # Estimated cost of the AI call in USD (automatically calculated by LiteLLM)
    cost: Optional[float] = Field(default=None, description="Estimated cost of the AI call in USD")


class AIDetector:
    """AI-powered foe detection using LiteLLM for multi-model support."""
    
    def __init__(self, api_key: Optional[str] = None, session: Optional[Session] = None):
        """Initialize the AI detector."""
        # Set model configuration first
        self.model = config.AI_MODEL
        self.temperature = config.AI_TEMPERATURE
        self.max_tokens = config.AI_MAX_TOKENS
        
        # Get API key
        if api_key:
            self.api_key = api_key
        elif session:
            settings_service = SettingsService(session)
            self.api_key = settings_service.get_openai_api_key()
        else:
            self.api_key = None
            
        # Set the API key for LiteLLM (handles multiple providers)
        if self.api_key:
            import os
            # LiteLLM automatically detects provider from model name
            # For Anthropic models (claude-*), it uses ANTHROPIC_API_KEY
            # For OpenAI models (gpt-*), it uses OPENAI_API_KEY
            if self.model.startswith("claude"):
                os.environ["ANTHROPIC_API_KEY"] = self.api_key
            else:
                os.environ["OPENAI_API_KEY"] = self.api_key
        
        logger.info(f"AI Detector initialized with model: {self.model}")
    
    def encode_image(self, image_data: bytes) -> str:
        """Encode image data to base64 string."""
        return base64.b64encode(image_data).decode('utf-8')
    
    async def detect_foes(self, image_data: bytes, context: Optional[str] = None) -> DetectionResult:
        """
        Detect foes in the provided image using AI vision.
        
        Args:
            image_data: Raw image bytes
            context: Optional context about the camera location
            
        Returns:
            DetectionResult with detected foes and cost information
        """
        if not self.api_key:
            logger.error("No OpenAI API key available for detection")
            return DetectionResult(
                foes_detected=False,
                foes=[],
                scene_description="No API key configured for AI detection"
            )
        
        try:
            # Encode image
            base64_image = self.encode_image(image_data)
            
            # Build context-aware prompt
            location_context = f" The camera is monitoring: {context}." if context else ""
            
            # System prompt for structured output
            system_prompt = """You are an expert wildlife detection system. Analyze the image and detect any of these foe types:

**Target Foes:**
- **RATS**: Any rodents (rats, mice, shrews, voles)
- **CROWS**: Any corvids (crows, ravens, magpies, jackdaws, jays)  
- **CATS**: Domestic cats (not wildcats or large cats)

**What to IGNORE (these are friends, not foes):**
- Small birds (sparrows, finches, tits, robins, wrens, etc.)
- Squirrels and chipmunks
- Hedgehogs and other small mammals that aren't rodents
- Beneficial insects
- Humans, pets (dogs), livestock
- Any wildlife that doesn't match the three foe categories above

Return a JSON object with:
- foes_detected: boolean
- foes: array of detected foes with foe_type (UPPERCASE: RATS, CROWS, CATS, or UNKNOWN), confidence (0-1), optional bounding_box, and description
- scene_description: brief overall scene description

Only detect the specific foe types listed above. Be conservative - if unsure, classify as UNKNOWN or don't detect. IMPORTANT: foe_type must be in UPPERCASE."""

            user_prompt = f"""Analyze this image for the target foe types (RATS, CROWS, CATS only).{location_context}
            
Return structured JSON with your analysis. Be precise and only detect the specified foe types. Remember: foe_type must be UPPERCASE."""

            # Make API call using LiteLLM
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                detection_data = json.loads(content)
                
                # Convert to our structured format
                foes = []
                if detection_data.get("foes"):
                    for foe_data in detection_data["foes"]:
                        # Validate foe type - ensure uppercase
                        foe_type = foe_data.get("foe_type", "").upper()
                        if foe_type not in ["RATS", "CROWS", "CATS", "UNKNOWN"]:
                            logger.warning(f"Invalid foe type detected: {foe_type}, setting to UNKNOWN")
                            foe_type = "UNKNOWN"
                        
                        foes.append(DetectedFoe(
                            foe_type=foe_type,
                            confidence=min(1.0, max(0.0, foe_data.get("confidence", 0.0))),
                            bounding_box=foe_data.get("bounding_box"),
                            description=foe_data.get("description", f"Detected {foe_type}")
                        ))
                
                # Calculate cost using LiteLLM's automatic cost calculation
                cost = 0.0
                if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
                    cost = response._hidden_params['response_cost']
                elif hasattr(response, 'usage') and response.usage:
                    # Fallback: try to calculate cost using LiteLLM's cost calculator
                    try:
                        cost = litellm.completion_cost(completion_response=response)
                    except Exception as e:
                        logger.warning(f"Could not calculate cost: {e}")
                        cost = 0.0
                
                logger.info(f"AI Detection completed - Model: {self.model}, Cost: ${cost:.6f}")
                
                return DetectionResult(
                    foes_detected=detection_data.get("foes_detected", False),
                    foes=foes,
                    scene_description=detection_data.get("scene_description", "Scene analyzed"),
                    cost=cost
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Raw response: {content}")
                return DetectionResult(
                    foes_detected=False,
                    foes=[],
                    scene_description=f"Error parsing AI response: {str(e)}"
                )
            
        except Exception as e:
            logger.exception(f"Error during AI detection")
            return DetectionResult(
                foes_detected=False,
                foes=[],
                scene_description=f"Error during detection: {str(e)}"
            )
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported models through LiteLLM."""
        return [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the AI detector is properly configured."""
        return {
            "api_key_configured": bool(self.api_key),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "supported_models": self.get_supported_models()
        }


# Global AI detector instance
ai_detector = AIDetector()