"""Species configuration for YOLO-based foe detection.

This module defines how YOLO-detected animals are classified as foes or friends.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SpeciesMapping:
    """Maps YOLO classes to foe types and behaviors."""
    yolo_class: str
    category: str
    is_foe: bool
    foe_type: Optional[str] = None
    confidence_modifier: float = 1.0  # Adjust confidence based on species
    notes: str = ""


# YOLO COCO class names for reference
COCO_CLASSES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep",
    19: "cow", 20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe",
    24: "backpack", 25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase",
    29: "frisbee", 30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard", 37: "surfboard",
    38: "tennis racket", 39: "bottle", 40: "wine glass", 41: "cup", 42: "fork",
    43: "knife", 44: "spoon", 45: "bowl", 46: "banana", 47: "apple",
    48: "sandwich", 49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog",
    53: "pizza", 54: "donut", 55: "cake", 56: "chair", 57: "couch",
    58: "potted plant", 59: "bed", 60: "dining table", 61: "toilet", 62: "tv",
    63: "laptop", 64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone",
    68: "microwave", 69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator",
    73: "book", 74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
    78: "hair drier", 79: "toothbrush"
}

# Species mapping configuration
SPECIES_MAPPINGS = {
    # Birds - Generic bird class needs further classification
    "bird": SpeciesMapping(
        yolo_class="bird",
        category="avian",
        is_foe=True,  # Assume corvids by default for safety
        foe_type="CROW",
        confidence_modifier=0.8,  # Lower confidence since we can't distinguish species
        notes="Generic bird detection - assumes corvid for deterrent purposes"
    ),
    
    # Mammals - Foes
    "cat": SpeciesMapping(
        yolo_class="cat",
        category="mammal",
        is_foe=True,
        foe_type="CAT",
        confidence_modifier=1.0,
        notes="Domestic cats that hunt birds"
    ),
    
    # Mammals - Potential helpers (deter other animals)
    "dog": SpeciesMapping(
        yolo_class="dog",
        category="mammal",
        is_foe=False,
        foe_type=None,
        confidence_modifier=1.0,
        notes="Dogs may help deter foes"
    ),
    
    # Mammals - Neutral/Friends
    "horse": SpeciesMapping(
        yolo_class="horse",
        category="mammal",
        is_foe=False,
        foe_type=None,
        notes="Large herbivore, not a threat"
    ),
    "sheep": SpeciesMapping(
        yolo_class="sheep",
        category="mammal",
        is_foe=False,
        foe_type=None,
        notes="Herbivore, not a threat"
    ),
    "cow": SpeciesMapping(
        yolo_class="cow",
        category="mammal",
        is_foe=False,
        foe_type=None,
        notes="Large herbivore, not a threat"
    ),
    
    # Note: COCO doesn't include specific classes for:
    # - Crows, magpies, ravens (all detected as "bird")
    # - Rats, mice (would need custom model)
    # - Squirrels (would need custom model)
    # - Hedgehogs (would need custom model)
}

# Enhanced foe type mapping for future custom models
FOE_TYPE_BEHAVIORS = {
    "CROW": {
        "species": ["crow", "raven", "magpie", "jackdaw"],
        "deterrent_sounds": ["predator_calls", "distress_signals"],
        "detection_priority": "high",
        "typical_size_range": (30, 60),  # cm
    },
    "CAT": {
        "species": ["domestic_cat", "feral_cat"],
        "deterrent_sounds": ["dog_barks", "ultrasonic"],
        "detection_priority": "high",
        "typical_size_range": (20, 40),  # cm
    },
    "RAT": {
        "species": ["brown_rat", "black_rat", "mouse"],
        "deterrent_sounds": ["owl_calls", "hawk_screeches"],
        "detection_priority": "medium",
        "typical_size_range": (10, 25),  # cm
    },
    "HERON": {
        "species": ["grey_heron", "great_blue_heron"],
        "deterrent_sounds": ["predator_calls"],
        "detection_priority": "medium",
        "typical_size_range": (80, 100),  # cm
    },
    "PIGEON": {
        "species": ["rock_pigeon", "wood_pigeon"],
        "deterrent_sounds": ["hawk_calls"],
        "detection_priority": "low",
        "typical_size_range": (25, 35),  # cm
    }
}


class SpeciesClassifier:
    """Enhanced species classifier using YOLO detections and additional heuristics."""
    
    def __init__(self):
        self.mappings = SPECIES_MAPPINGS
        self.behaviors = FOE_TYPE_BEHAVIORS
    
    def classify_detection(self, yolo_class: str, confidence: float, 
                          bbox: Optional[Tuple[float, float, float, float]] = None) -> Tuple[bool, Optional[str], float]:
        """
        Classify a YOLO detection as foe or friend.
        
        Args:
            yolo_class: YOLO class name
            confidence: Detection confidence
            bbox: Bounding box (x1, y1, x2, y2) for size-based classification
            
        Returns:
            Tuple of (is_foe, foe_type, adjusted_confidence)
        """
        if yolo_class not in self.mappings:
            return False, None, confidence
        
        mapping = self.mappings[yolo_class]
        adjusted_confidence = confidence * mapping.confidence_modifier
        
        # Future enhancement: Use bbox size to better classify birds
        # (larger birds more likely to be corvids)
        if yolo_class == "bird" and bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            size = max(width, height)
            
            # Rough heuristic: larger birds more likely to be corvids
            # This would need calibration based on camera distance
            if size > 100:  # pixels
                adjusted_confidence *= 1.2  # Boost confidence for larger birds
        
        return mapping.is_foe, mapping.foe_type, min(adjusted_confidence, 1.0)
    
    def get_deterrent_sounds(self, foe_type: str) -> List[str]:
        """Get recommended deterrent sounds for a foe type."""
        if foe_type in self.behaviors:
            return self.behaviors[foe_type]["deterrent_sounds"]
        return []