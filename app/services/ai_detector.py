"""AI-powered foe detection service using OpenAI GPT-4o."""
import os
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
import logging
from pydantic import BaseModel, Field
from app.models.detection import FoeType
import json

# Logger for AI detector
logger = logging.getLogger(__name__)

# Pricing for GPT-4o (USD per 1K tokens); override via environment variables if needed
_INPUT_COST_PER_1K = float(os.getenv("OPENAI_INPUT_COST_PER_1K", "0.03"))
_OUTPUT_COST_PER_1K = float(os.getenv("OPENAI_OUTPUT_COST_PER_1K", "0.06"))


class DetectedFoe(BaseModel):
    """Structured output for a detected foe."""
    foe_type: str = Field(description="Type of foe: rats, crows, cats, or unknown (must match exactly)")
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
    # Estimated cost of the AI call in USD
    cost: Optional[float] = Field(default=None, description="Estimated cost of the AI call in USD")


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
        system_prompt = """You are a high-precision wildlife detection system for SECURITY PURPOSES. This is critical infrastructure protection that requires MAXIMUM ACCURACY and CAREFUL ANALYSIS.

EXAMINE THE IMAGE EXTREMELY CAREFULLY and identify any of these specific target animals (foes):

**TARGET SPECIES (analyze with extreme precision):**

1. **RATS** (all rodents including mice): 
   - Brown rats (Rattus norvegicus) - gray-brown fur, long tail, large ears
   - Black rats (Rattus rattus) - darker fur, pointed snout, large ears
   - House mice (Mus musculus) - small, gray-brown, large ears relative to head
   - Look for: distinctive body shape, long bare tail, quick movements, small size

2. **CROWS** (ALL corvids - crows, ravens, magpies, jackdaws):
   - Carrion Crow (Corvus corone) - completely black, robust build, thick bill
   - Hooded Crow (Corvus cornix) - black with gray body, same size as carrion crow
   - Eurasian Magpie (Pica pica) - black and white, long iridescent tail, distinctive pattern
   - Western Jackdaw (Coloeus monedula) - smaller than crow, gray neck/nape, pale eyes
   - Northern Raven (Corvus corax) - much larger than crow, wedge-shaped tail, shaggy throat feathers
   - Look for: corvid family characteristics - intelligent eyes, sturdy bills, confident posture

3. **CATS** (Felis catus):
   - Domestic cats of any color/pattern
   - Look for: feline body shape, pointed ears, whiskers, typical cat posture and movement

**CRITICAL CLASSIFICATION RULES:**
- Use EXACTLY these foe_type values: "rats", "crows", "cats", or "unknown"
- Group ALL rodents (rats, mice) under "rats"
- Group ALL corvids (crows, ravens, magpies, jackdaws) under "crows"
- These names MUST match exactly for the countermeasure sound system

**DETECTION REQUIREMENTS:**
- LOOK LONG AND HARD - scan every part of the image systematically
- Only report detections you are HIGHLY CONFIDENT about (>0.7 confidence minimum)
- Consider size, posture, coloration, and behavioral cues
- For partially obscured animals, be extra cautious with identification

**CRITICAL**: False positives can trigger unnecessary security responses. False negatives can miss genuine threats. PRECISION IS PARAMOUNT.

For each detection, provide:
- Exact type: "rats", "crows", "cats", or "unknown" (MUST match exactly)
- Confidence score (0.7-1.0 for security-grade detections)
- Precise bounding box coordinates
- Detailed description including key identifying features

If no target species are present, report foes_detected: false."""

        user_prompt = """SECURITY ANALYSIS REQUEST: Examine this surveillance image with MAXIMUM PRECISION for the presence of target foe species.

INSTRUCTIONS:
1. Scan the ENTIRE image systematically - check corners, shadows, partial obscured areas
2. Look for ANY signs of: rats (all rodents), crows (all corvids), or cats
3. Pay special attention to movement blur, partial visibility, or camouflaged animals
4. Consider the setting/context (indoor/outdoor, day/night, etc.) for species likelihood
5. Only report detections with HIGH CONFIDENCE (≥0.7) suitable for security applications
6. Provide detailed reasoning for each detection including specific identifying features
7. CRITICAL: Use EXACTLY "rats", "crows", "cats", or "unknown" as foe_type values

This is critical security infrastructure - accuracy is essential."""
        
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
                temperature=0.1  # Very low temperature for maximum precision and consistency
            )
            
            # Debug-log the raw API response structure
            logger.debug(f"AI parse response object: {response}")
            try:
                raw_data = getattr(response, '_raw', None)
                logger.debug(f"AI raw underlying data: {raw_data}")
            except Exception as _dl_exc:
                logger.debug(f"Error accessing raw response data: {_dl_exc}")

            # Compute cost based on returned usage info
            cost = 0.0
            usage = getattr(response, 'usage', None)
            if usage:
                prompt_tokens = getattr(usage, 'prompt_tokens', None)
                completion_tokens = getattr(usage, 'completion_tokens', None)
                total_tokens = getattr(usage, 'total_tokens', None)
                if prompt_tokens is not None:
                    cost += prompt_tokens * (_INPUT_COST_PER_1K / 1000)
                if completion_tokens is not None:
                    cost += completion_tokens * (_OUTPUT_COST_PER_1K / 1000)
                logger.info(
                    f"OpenAI GPT-4o usage: prompt_tokens={prompt_tokens}, "
                    f"completion_tokens={completion_tokens}, total_tokens={total_tokens}, "
                    f"estimated_cost=${cost:.6f}"
                )
            else:
                logger.debug("No usage info on response; response.usage is None; cost remains 0.0")
            
            result = response.choices[0].message.parsed
            # Attach estimated cost to the result
            try:
                result.cost = cost
            except Exception:
                pass
            
            # Validate foe types match our enum values (no mapping needed since AI uses correct names)
            for foe in result.foes:
                if foe.foe_type not in ["rats", "crows", "cats", "unknown"]:
                    logger.warning(f"AI returned invalid foe_type '{foe.foe_type}', changing to 'unknown'")
                    foe.foe_type = "unknown"
                    
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