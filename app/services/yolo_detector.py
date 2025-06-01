"""YOLOv11 Detection Service for multi-species animal detection."""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from PIL import Image
import torch
from ultralytics import YOLO
from dataclasses import dataclass
import time
import psutil
import os

from app.services.species_config import SpeciesClassifier, COCO_CLASSES
from app.core.config import config

logger = logging.getLogger(__name__)


@dataclass
class YOLODetection:
    """Represents a single YOLO detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    category: str  # bird, mammal, etc.


class YOLOv11DetectionService:
    """Service for detecting animals using YOLOv11 model."""
    
    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """Initialize the YOLO detection service.
        
        Args:
            model_path: Path to the YOLO model file. If None, uses default model location
            device: Device to run inference on ('cpu', 'cuda', 'mps'). Auto-selects if None
        """
        # Use configured model path
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = str(config.MODELS_DIR / config.YOLO_MODEL_NAME)
            
        self.device = device or self._select_device()
        self.model = None
        self.species_classifier = SpeciesClassifier()
        self._load_model()
        
    def _select_device(self) -> str:
        """Auto-select the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _load_model(self):
        """Load the YOLO model, downloading if necessary."""
        try:
            model_file = Path(self.model_path)
            
            # Check if model exists, if not it will be downloaded automatically
            if not model_file.exists():
                logger.info(f"YOLOv11 model not found at {self.model_path}, will download automatically")
                # Ensure parent directory exists
                model_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Loading YOLOv11 model from {self.model_path} on device {self.device}")
            
            # YOLO will automatically download the model if it doesn't exist
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            
            # Verify model loaded correctly by checking model info
            if hasattr(self.model, 'model') and self.model.model is not None:
                logger.info(f"YOLOv11 model loaded successfully on {self.device}")
                logger.info(f"Model has {len(self.model.model.names)} classes")
            else:
                raise RuntimeError("Model loaded but appears to be invalid")
                
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(self, image: Image.Image, confidence_threshold: float = 0.25) -> List[YOLODetection]:
        """Detect animals in an image.
        
        Args:
            image: PIL Image to process
            confidence_threshold: Minimum confidence score for detections
            
        Returns:
            List of YOLODetection objects
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        # Get memory usage before inference
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Run inference
            results = self.model(image, conf=confidence_threshold, verbose=False)
            
            detections = []
            for r in results:
                if r.boxes is not None:
                    for box in r.boxes:
                        class_id = int(box.cls)
                        
                        # Get class name from COCO classes
                        if class_id in COCO_CLASSES:
                            class_name = COCO_CLASSES[class_id]
                            
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            
                            # Check if this is an animal we care about
                            is_foe, foe_type, _ = self.species_classifier.classify_detection(
                                class_name, float(box.conf), (x1, y1, x2, y2)
                            )
                            
                            # Determine category
                            if class_name in ["bird"]:
                                category = "avian"
                            elif class_name in ["cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"]:
                                category = "mammal"
                            else:
                                continue  # Skip non-animal classes
                            
                            detection = YOLODetection(
                                class_id=class_id,
                                class_name=class_name,
                                confidence=float(box.conf),
                                bbox=(x1, y1, x2, y2),
                                category=category
                            )
                            detections.append(detection)
            
            # Get memory usage after inference
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            processing_time = time.time() - start_time
            
            # Log performance metrics
            logger.info(f"YOLO inference completed in {processing_time:.3f}s, "
                       f"found {len(detections)} animals, "
                       f"memory used: {memory_used:.1f}MB (total: {memory_after:.1f}MB)")
            
            return detections
            
        except Exception as e:
            logger.error(f"Error during YOLO detection: {e}")
            raise
    
    def detect_from_path(self, image_path: str, confidence_threshold: float = 0.25) -> List[YOLODetection]:
        """Detect animals in an image from file path.
        
        Args:
            image_path: Path to image file
            confidence_threshold: Minimum confidence score for detections
            
        Returns:
            List of YOLODetection objects
        """
        image = Image.open(image_path)
        return self.detect(image, confidence_threshold)
    
    def classify_as_foe(self, detection: YOLODetection) -> Optional[str]:
        """Classify a detection as a specific type of foe.
        
        Uses the species classifier for consistent classification.
        
        Args:
            detection: YOLODetection object
            
        Returns:
            Foe type string or None if not a foe
        """
        is_foe, foe_type, _ = self.species_classifier.classify_detection(
            detection.class_name, 
            detection.confidence, 
            detection.bbox
        )
        
        return foe_type if is_foe else None
    
    def get_all_detections_with_foe_classification(
        self, 
        image: Image.Image, 
        confidence_threshold: float = 0.25
    ) -> Tuple[List[YOLODetection], Dict[str, List[YOLODetection]]]:
        """Detect all animals and classify them as foes or friends.
        
        Args:
            image: PIL Image to process
            confidence_threshold: Minimum confidence score
            
        Returns:
            Tuple of (all_detections, foe_detections_by_type)
        """
        all_detections = self.detect(image, confidence_threshold)
        
        foe_detections = {}
        for detection in all_detections:
            foe_type = self.classify_as_foe(detection)
            if foe_type:
                if foe_type not in foe_detections:
                    foe_detections[foe_type] = []
                foe_detections[foe_type].append(detection)
        
        return all_detections, foe_detections
    
    def draw_detections(
        self, 
        image: Image.Image, 
        detections: List[YOLODetection],
        foe_classifications: Optional[Dict[str, List[YOLODetection]]] = None
    ) -> Image.Image:
        """Draw bounding boxes on image.
        
        Args:
            image: Original image
            detections: List of detections to draw
            foe_classifications: Optional dict mapping foe types to detections
            
        Returns:
            Image with drawn bounding boxes
        """
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Create a mapping of detections to foe types for coloring
        detection_to_foe = {}
        if foe_classifications:
            for foe_type, foe_detections in foe_classifications.items():
                for det in foe_detections:
                    detection_to_foe[id(det)] = foe_type
        
        # Define colors for different categories
        colors = {
            "CROW": (0, 0, 255),      # Red for crows
            "CAT": (255, 0, 0),       # Blue for cats
            "RAT": (0, 165, 255),     # Orange for rats
            "friend": (0, 255, 0),     # Green for non-foes
            "unknown": (128, 128, 128) # Gray for unknown
        }
        
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection.bbox)
            
            # Determine color based on foe classification
            foe_type = detection_to_foe.get(id(detection))
            if foe_type:
                color = colors.get(foe_type, colors["unknown"])
                label = f"{foe_type}: {detection.confidence:.2f}"
            else:
                color = colors["friend"]
                label = f"{detection.class_name}: {detection.confidence:.2f}"
            
            # Draw bounding box
            cv2.rectangle(img_cv, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img_cv, (x1, y1 - label_size[1] - 4), 
                         (x1 + label_size[0], y1), color, -1)
            
            # Draw label text
            cv2.putText(img_cv, label, (x1, y1 - 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Convert back to PIL
        img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        return img_pil