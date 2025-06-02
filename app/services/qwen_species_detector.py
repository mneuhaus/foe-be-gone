"""Qwen2.5-VL-3B Species Identification Service for precise animal species identification."""

import base64
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import io
from PIL import Image, ImageDraw
import torch
from pathlib import Path

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import config
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# Check if transformers is available for local Qwen
try:
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer, AutoProcessor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers library not available. Species identification will be disabled.")
    TRANSFORMERS_AVAILABLE = False


class SpeciesIdentification(BaseModel):
    """Structured output for species identification."""
    species: str = Field(description="Specific species name (e.g., 'European Robin', 'House Mouse', 'Domestic Cat')")
    common_name: str = Field(description="Common name for the species")
    foe_type: Optional[str] = Field(description="Foe classification: RATS, CROWS, CATS, or null if not a foe")
    confidence: float = Field(description="Confidence score between 0 and 1", ge=0.0, le=1.0)
    description: str = Field(description="Brief description of identifying features")
    reasoning: str = Field(description="Explanation of identification reasoning")


class SpeciesDetectionResult(BaseModel):
    """Result from species identification."""
    species_identified: bool = Field(description="Whether species could be identified")
    identifications: List[SpeciesIdentification] = Field(default_factory=list)
    scene_description: str = Field(description="Brief description of the cropped image")
    cost: Optional[float] = Field(default=None, description="Estimated cost of the AI call in USD")


class QwenSpeciesDetector:
    """Local Qwen2.5-VL-3B based species identification service for cropped animal images."""
    
    def __init__(self, api_key: Optional[str] = None, session: Optional[Session] = None):
        """Initialize the local Qwen species detector."""
        self.model_name = "Qwen/Qwen2.5-VL-3B-Instruct"
        self.temperature = 0.1
        self.max_tokens = 1500
        self.crop_padding = config.SPECIES_CROP_PADDING
        self.min_crop_size = getattr(config, 'SPECIES_MIN_CROP_SIZE', 224)  # Default 224px minimum
        self.device = self._select_device()
        
        # Initialize model, tokenizer, and processor
        self.model = None
        self.tokenizer = None
        self.processor = None
        self.model_loaded = False
        
        # Don't load model immediately - wait for first use
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available - species identification disabled")
        
        logger.info(f"Local Qwen Species Detector initialized (device: {self.device}, will load on first use)")
    
    def _select_device(self) -> str:
        """Auto-select the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            # For Qwen2.5-VL-3B, use CPU to avoid MPS memory issues
            # The model is quite large (~7GB) and may exceed MPS memory limits
            logger.info("MPS available but using CPU for Qwen2.5-VL-3B to avoid memory issues")
            return "cpu"
        else:
            return "cpu"
    
    def _load_model(self):
        """Load the local Qwen2.5-VL model."""
        try:
            logger.info(f"Loading Qwen2.5-VL-3B model on {self.device}...")
            
            # Load tokenizer and processor
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model with appropriate settings
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                device_map=self.device if self.device != "cpu" else None,
                trust_remote_code=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            self.model.eval()
            self.model_loaded = True
            
            logger.info("Qwen2.5-VL-3B model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Qwen2.5-VL model: {e}")
            self.model_loaded = False
    
    def crop_image_with_padding(self, image: Image.Image, bbox: Tuple[float, float, float, float], 
                               padding_percent: float = 0.5, min_size: int = 224) -> Image.Image:
        """
        Crop image around bounding box with additional padding and minimum size enforcement.
        
        Args:
            image: PIL Image object
            bbox: Bounding box as (x1, y1, x2, y2)
            padding_percent: Percentage of bbox size to add as padding (0.5 = 50%)
            min_size: Minimum width/height for the cropped image in pixels (default: 224)
            
        Returns:
            Cropped PIL Image with padding and minimum size guarantee
        """
        x1, y1, x2, y2 = bbox
        
        # Calculate bbox dimensions
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        
        # Calculate padding based on bbox size
        padding_x = bbox_width * padding_percent
        padding_y = bbox_height * padding_percent
        
        # Calculate initial crop coordinates with padding
        crop_x1 = x1 - padding_x
        crop_y1 = y1 - padding_y
        crop_x2 = x2 + padding_x
        crop_y2 = y2 + padding_y
        
        # Calculate current crop dimensions
        crop_width = crop_x2 - crop_x1
        crop_height = crop_y2 - crop_y1
        
        # Enforce minimum size if needed
        if crop_width < min_size:
            # Need to expand width
            width_deficit = min_size - crop_width
            expand_x = width_deficit / 2
            crop_x1 -= expand_x
            crop_x2 += expand_x
            crop_width = min_size
            logger.debug(f"Expanded crop width from {crop_width:.0f} to {min_size}px")
        
        if crop_height < min_size:
            # Need to expand height
            height_deficit = min_size - crop_height
            expand_y = height_deficit / 2
            crop_y1 -= expand_y
            crop_y2 += expand_y
            crop_height = min_size
            logger.debug(f"Expanded crop height from {crop_height:.0f} to {min_size}px")
        
        # Ensure crop stays within image bounds
        # If crop is larger than image dimension, center it
        if crop_width > image.width:
            crop_x1 = 0
            crop_x2 = image.width
        else:
            # Adjust if crop extends beyond image bounds
            if crop_x1 < 0:
                crop_x2 -= crop_x1  # Shift right by the amount we're negative
                crop_x1 = 0
            if crop_x2 > image.width:
                crop_x1 -= (crop_x2 - image.width)  # Shift left by the overflow
                crop_x2 = image.width
                crop_x1 = max(0, crop_x1)  # Ensure we don't go negative
        
        if crop_height > image.height:
            crop_y1 = 0
            crop_y2 = image.height
        else:
            # Adjust if crop extends beyond image bounds
            if crop_y1 < 0:
                crop_y2 -= crop_y1  # Shift down by the amount we're negative
                crop_y1 = 0
            if crop_y2 > image.height:
                crop_y1 -= (crop_y2 - image.height)  # Shift up by the overflow
                crop_y2 = image.height
                crop_y1 = max(0, crop_y1)  # Ensure we don't go negative
        
        # Final boundary check
        crop_x1 = max(0, crop_x1)
        crop_y1 = max(0, crop_y1)
        crop_x2 = min(image.width, crop_x2)
        crop_y2 = min(image.height, crop_y2)
        
        # Crop the image
        cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        logger.debug(f"Cropped image from bbox {bbox} (size: {bbox_width:.0f}x{bbox_height:.0f}) with "
                    f"{padding_percent*100}% padding to ({crop_x1:.1f}, {crop_y1:.1f}, {crop_x2:.1f}, {crop_y2:.1f}), "
                    f"final size: {cropped.width}x{cropped.height} (min: {min_size}px)")
        
        return cropped
    
    def encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string."""
        buffer = io.BytesIO()
        # Convert to RGB if necessary (removes alpha channel)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    async def identify_species(self, image: Image.Image, bbox: Tuple[float, float, float, float],
                             context: Optional[str] = None) -> SpeciesDetectionResult:
        """
        Identify species in a cropped region of the image using local Qwen2.5-VL.
        
        Args:
            image: Full PIL Image
            bbox: Bounding box of the detected object (x1, y1, x2, y2)
            context: Optional context about the camera location
            
        Returns:
            SpeciesDetectionResult with species identification
        """
        # Load model on first use
        if not self.model_loaded:
            if TRANSFORMERS_AVAILABLE:
                logger.info("Loading Qwen model on first use...")
                self._load_model()
            
            if not self.model_loaded:
                logger.warning("Qwen model not loaded - species identification unavailable")
                return SpeciesDetectionResult(
                    species_identified=False,
                    identifications=[],
                    scene_description="Local Qwen model not available"
            )
        
        try:
            # Crop image around bounding box with configured padding and minimum size
            cropped_image = self.crop_image_with_padding(image, bbox, 
                                                        padding_percent=self.crop_padding,
                                                        min_size=self.min_crop_size)
            
            # Build context-aware prompt
            location_context = f" This image was taken at: {context}." if context else ""
            
            # Comprehensive prompt for species identification
            prompt = f"""You are an expert wildlife biologist. Analyze this cropped image and identify the animal species.{location_context}

TASK: Identify the specific species and classify if it's a target foe type.

FOE TYPES:
- RATS: Any rodents (rats, mice, voles, shrews)
- CROWS: Any corvids (crows, ravens, magpies, jackdaws, jays)  
- CATS: Domestic cats only
- null: If not one of these three types

Respond in JSON format:
{{
  "species_identified": true/false,
  "identifications": [{{
    "species": "Exact species name",
    "common_name": "Common name",
    "foe_type": "RATS"/"CROWS"/"CATS"/null,
    "confidence": 0.0-1.0,
    "description": "Key identifying features",
    "reasoning": "Detailed identification explanation"
  }}],
  "scene_description": "What you see in this cropped image"
}}

Be precise with species names. Focus on visible anatomical features, coloring, and body structure."""

            # Prepare the image and text for the model
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": cropped_image},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Process inputs
            text = self.processor.apply_chat_template(
                conversation, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # Prepare inputs for the model
            inputs = self.processor(
                text=[text],
                images=[cropped_image],
                padding=True,
                return_tensors="pt"
            )
            
            # Move inputs to the correct device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_tokens,
                    temperature=self.temperature,
                    do_sample=True if self.temperature > 0 else False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode the response
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
            ]
            
            response_text = self.processor.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=False
            )[0]
            
            # Parse the JSON response
            try:
                # Clean up the response text - sometimes models add extra text
                response_text = response_text.strip()
                
                # Try to extract JSON from the response
                if "{" in response_text and "}" in response_text:
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}") + 1
                    json_text = response_text[start_idx:end_idx]
                else:
                    json_text = response_text
                
                species_data = json.loads(json_text)
                
                # Convert to our structured format
                identifications = []
                if species_data.get("identifications"):
                    for id_data in species_data["identifications"]:
                        # Validate foe type
                        foe_type = id_data.get("foe_type")
                        if foe_type and foe_type not in ["RATS", "CROWS", "CATS"]:
                            logger.warning(f"Invalid foe type from species ID: {foe_type}, setting to null")
                            foe_type = None
                        
                        identifications.append(SpeciesIdentification(
                            species=id_data.get("species", "Unknown species"),
                            common_name=id_data.get("common_name", "Unknown"),
                            foe_type=foe_type,
                            confidence=min(1.0, max(0.0, id_data.get("confidence", 0.0))),
                            description=id_data.get("description", ""),
                            reasoning=id_data.get("reasoning", "")
                        ))
                
                # Local model has no API cost
                cost = 0.0
                
                logger.info(f"Local Qwen species identification completed - "
                           f"Species: {identifications[0].species if identifications else 'None'}, "
                           f"Foe: {identifications[0].foe_type if identifications else 'None'}")
                
                return SpeciesDetectionResult(
                    species_identified=species_data.get("species_identified", False),
                    identifications=identifications,
                    scene_description=species_data.get("scene_description", "Cropped animal image analyzed"),
                    cost=cost
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Qwen response as JSON: {e}")
                logger.error(f"Raw response: {response_text}")
                
                # Fallback: create a basic identification based on the text response
                return SpeciesDetectionResult(
                    species_identified=False,
                    identifications=[],
                    scene_description=f"Model response (non-JSON): {response_text[:200]}..."
                )
            
        except Exception as e:
            logger.exception(f"Error during local Qwen species identification")
            return SpeciesDetectionResult(
                species_identified=False,
                identifications=[],
                scene_description=f"Error during species identification: {str(e)}"
            )
    
    async def identify_multiple_species(self, image: Image.Image, 
                                       bboxes: List[Tuple[float, float, float, float]],
                                       context: Optional[str] = None) -> List[SpeciesDetectionResult]:
        """
        Identify species for multiple bounding boxes in the same image.
        
        Args:
            image: Full PIL Image
            bboxes: List of bounding boxes (x1, y1, x2, y2)
            context: Optional context about the camera location
            
        Returns:
            List of SpeciesDetectionResult objects
        """
        results = []
        for i, bbox in enumerate(bboxes):
            logger.info(f"Identifying species for detection {i+1}/{len(bboxes)}")
            result = await self.identify_species(image, bbox, context)
            results.append(result)
        
        return results
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for species identification."""
        return [
            "qwen/qwen2-vl-3b-instruct",
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ]
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the local species detector is properly configured."""
        return {
            "model_loaded": self.model_loaded,
            "model_name": self.model_name,
            "device": self.device,
            "transformers_available": TRANSFORMERS_AVAILABLE,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "crop_padding": self.crop_padding,
            "min_crop_size": self.min_crop_size
        }


# Global species detector instance
species_detector = QwenSpeciesDetector()