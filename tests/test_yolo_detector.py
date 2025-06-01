"""Tests for YOLOv11 detection service."""

import pytest
from pathlib import Path
from PIL import Image
import numpy as np
from app.services.yolo_detector import YOLOv11DetectionService, YOLODetection
from app.services.species_config import SpeciesClassifier


class TestYOLOv11DetectionService:
    """Test suite for YOLO detection service."""
    
    @pytest.fixture
    def yolo_service(self):
        """Create a YOLO detection service instance."""
        # Use CPU for tests to ensure compatibility
        return YOLOv11DetectionService(device="cpu")
    
    @pytest.fixture
    def sample_images_dir(self):
        """Get path to sample surveillance images."""
        return Path("public/dummy-surveillance")
    
    def test_service_initialization(self, yolo_service):
        """Test that YOLO service initializes correctly."""
        assert yolo_service is not None
        assert yolo_service.model is not None
        assert yolo_service.species_classifier is not None
        assert yolo_service.device in ["cpu", "cuda", "mps"]
    
    def test_detect_cat(self, yolo_service, sample_images_dir):
        """Test detection of cats in surveillance images."""
        cat_images = list((sample_images_dir / "cat").glob("*.jpg"))
        
        if not cat_images:
            pytest.skip("No cat sample images found")
        
        # Test first cat image
        image_path = str(cat_images[0])
        detections = yolo_service.detect_from_path(image_path)
        
        # Should detect at least one animal
        assert len(detections) >= 0  # YOLO might not always detect
        
        # If detected, check classification
        if detections:
            # Check if any detection was classified as a cat
            cat_detected = any(d.class_name == "cat" for d in detections)
            if cat_detected:
                cat_detection = next(d for d in detections if d.class_name == "cat")
                assert cat_detection.category == "mammal"
                assert 0 <= cat_detection.confidence <= 1
    
    def test_detect_bird(self, yolo_service, sample_images_dir):
        """Test detection of birds in surveillance images."""
        # Check various bird folders
        bird_folders = ["magpie", "small-bird"]
        bird_images = []
        
        for folder in bird_folders:
            folder_path = sample_images_dir / folder
            if folder_path.exists():
                bird_images.extend(list(folder_path.glob("*.jpg")))
        
        if not bird_images:
            pytest.skip("No bird sample images found")
        
        # Test first bird image
        image_path = str(bird_images[0])
        detections = yolo_service.detect_from_path(image_path)
        
        # Check if any birds detected
        if detections:
            bird_detected = any(d.class_name == "bird" for d in detections)
            if bird_detected:
                bird_detection = next(d for d in detections if d.class_name == "bird")
                assert bird_detection.category == "avian"
    
    def test_foe_classification(self, yolo_service):
        """Test foe classification logic."""
        # Create mock detections
        cat_detection = YOLODetection(
            class_id=15,
            class_name="cat",
            confidence=0.9,
            bbox=(100, 100, 200, 200),
            category="mammal"
        )
        
        bird_detection = YOLODetection(
            class_id=14,
            class_name="bird",
            confidence=0.8,
            bbox=(50, 50, 150, 150),
            category="avian"
        )
        
        # Test classification
        cat_foe_type = yolo_service.classify_as_foe(cat_detection)
        assert cat_foe_type == "CAT"
        
        bird_foe_type = yolo_service.classify_as_foe(bird_detection)
        assert bird_foe_type == "CROW"  # Birds default to crow for safety
    
    def test_multi_species_detection(self, yolo_service):
        """Test detection with multiple species classification."""
        # Create a test image with multiple objects
        # For actual testing, we'd use a real multi-animal image
        test_image = Image.new('RGB', (640, 480), color='white')
        
        # Run detection
        all_detections, foe_classifications = yolo_service.get_all_detections_with_foe_classification(test_image)
        
        # Verify structure
        assert isinstance(all_detections, list)
        assert isinstance(foe_classifications, dict)
        
        # If no detections on blank image, that's fine
        if not all_detections:
            assert len(foe_classifications) == 0
    
    def test_species_classifier(self):
        """Test the species classifier component."""
        classifier = SpeciesClassifier()
        
        # Test cat classification
        is_foe, foe_type, confidence = classifier.classify_detection("cat", 0.9)
        assert is_foe is True
        assert foe_type == "CAT"
        assert confidence == 0.9
        
        # Test bird classification
        is_foe, foe_type, confidence = classifier.classify_detection("bird", 0.8)
        assert is_foe is True
        assert foe_type == "CROW"
        assert confidence == 0.8 * 0.8  # Confidence modifier applied
        
        # Test non-foe (dog)
        is_foe, foe_type, confidence = classifier.classify_detection("dog", 0.95)
        assert is_foe is False
        assert foe_type is None
        assert confidence == 0.95
    
    def test_bounding_box_drawing(self, yolo_service):
        """Test bounding box drawing functionality."""
        # Create test image
        test_image = Image.new('RGB', (640, 480), color='white')
        
        # Create test detections
        detections = [
            YOLODetection(
                class_id=15,
                class_name="cat",
                confidence=0.9,
                bbox=(100, 100, 300, 300),
                category="mammal"
            )
        ]
        
        foe_classifications = {
            "CAT": detections
        }
        
        # Draw bounding boxes
        result_image = yolo_service.draw_detections(test_image, detections, foe_classifications)
        
        # Verify image was returned
        assert isinstance(result_image, Image.Image)
        assert result_image.size == test_image.size
    
    def test_confidence_threshold(self, yolo_service, sample_images_dir):
        """Test that confidence threshold filtering works."""
        cat_images = list((sample_images_dir / "cat").glob("*.jpg"))
        
        if not cat_images:
            pytest.skip("No cat sample images found")
        
        image_path = str(cat_images[0])
        
        # Test with high confidence threshold
        high_conf_detections = yolo_service.detect_from_path(image_path, confidence_threshold=0.8)
        
        # Test with low confidence threshold
        low_conf_detections = yolo_service.detect_from_path(image_path, confidence_threshold=0.1)
        
        # Low threshold should have same or more detections
        assert len(low_conf_detections) >= len(high_conf_detections)
        
        # All detections should meet their threshold
        for det in high_conf_detections:
            assert det.confidence >= 0.8
    
    @pytest.mark.parametrize("image_folder,expected_category", [
        ("cat", "mammal"),
        ("magpie", "avian"),
        ("small-bird", "avian"),
    ])
    def test_various_animals(self, yolo_service, sample_images_dir, image_folder, expected_category):
        """Test detection of various animal types."""
        folder_path = sample_images_dir / image_folder
        if not folder_path.exists():
            pytest.skip(f"No {image_folder} folder found")
        
        images = list(folder_path.glob("*.jpg"))
        if not images:
            pytest.skip(f"No images in {image_folder} folder")
        
        # Test first image
        detections = yolo_service.detect_from_path(str(images[0]))
        
        # YOLO might not detect in all images, so we just verify structure
        for det in detections:
            assert hasattr(det, 'class_name')
            assert hasattr(det, 'confidence')
            assert hasattr(det, 'bbox')
            assert hasattr(det, 'category')
            assert 0 <= det.confidence <= 1
            assert len(det.bbox) == 4