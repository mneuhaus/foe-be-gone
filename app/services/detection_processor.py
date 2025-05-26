"""Detection processing service for analyzing images and managing detections."""

import logging
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import imagehash
from PIL import Image
from sqlmodel import Session

from app.models.device import Device
from app.models.detection import Detection, Foe, DetectionStatus, DeterrentAction, FoeType
from app.services.ai_detector import AIDetector
from app.core.session import get_db_session, safe_commit
from app.core.config import config

logger = logging.getLogger(__name__)


class DetectionProcessor:
    """Processes camera snapshots to detect foes and manage detection records."""
    
    def __init__(self, change_threshold: int = 10):
        """
        Initialize the detection processor.
        
        Args:
            change_threshold: Hamming distance threshold for significant image changes
        """
        self.change_threshold = change_threshold
        self.ai_detector = AIDetector()
        
    def calculate_image_hash(self, image_data: bytes) -> str:
        """Calculate perceptual hash of image data."""
        try:
            image = Image.open(io.BytesIO(image_data))
            # Use average hash for good balance of speed and accuracy
            hash_value = imagehash.average_hash(image)
            return str(hash_value)
        except Exception as e:
            logger.error(f"Error calculating image hash: {e}")
            return ""
    
    def has_significant_change(self, current_hash: str, previous_hash: Optional[str]) -> bool:
        """Check if image has changed significantly from previous."""
        if not previous_hash or not current_hash:
            return True
            
        try:
            hash1 = imagehash.hex_to_hash(current_hash)
            hash2 = imagehash.hex_to_hash(previous_hash)
            distance = hash1 - hash2
            
            logger.debug(f"Image hash distance: {distance} (threshold: {self.change_threshold})")
            return distance >= self.change_threshold
            
        except Exception as e:
            logger.error(f"Error comparing image hashes: {e}")
            return True
    
    def save_snapshot(self, image_data: bytes, camera_name: str) -> Path:
        """Save snapshot image to disk."""
        # Create snapshots directory if needed
        config.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_name}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = config.SNAPSHOTS_DIR / filename
        
        # Save image
        try:
            with open(filepath, 'wb') as f:
                f.write(image_data)
            logger.info(f"Saved snapshot to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            raise
    
    async def process_snapshot(self, camera: Device, image_data: bytes) -> Optional[Detection]:
        """
        Process a camera snapshot to detect foes.
        
        Args:
            camera: Camera device that captured the image
            image_data: Raw image bytes
            
        Returns:
            Detection record if foes were found, None otherwise
        """
        # Calculate image hash
        current_hash = self.calculate_image_hash(image_data)
        
        # Check if image has changed significantly
        if not self.has_significant_change(current_hash, camera.last_image_hash):
            logger.debug(f"No significant change in {camera.name}, skipping detection")
            return None
        
        # Update camera's last image hash
        with get_db_session() as session:
            camera_db = session.get(Device, camera.device_id)
            if camera_db:
                camera_db.last_image_hash = current_hash
                safe_commit(session)
        
        # Save snapshot
        image_path = self.save_snapshot(image_data, camera.name)
        
        # Run AI detection
        try:
            result = self.ai_detector.detect_foes(image_data)
            
            if not result.foes_detected:
                logger.info(f"No foes detected in {camera.name}")
                return None
            
            # Create detection record
            with get_db_session() as session:
                detection = Detection(
                    device_id=camera.device_id,
                    image_path=str(image_path),
                    timestamp=datetime.utcnow(),
                    status=DetectionStatus.detected,
                    ai_model=result.model_used,
                    ai_response_time=result.processing_time,
                    ai_cost_usd=result.cost_estimate
                )
                
                # Add detected foes
                for detected_foe in result.foes:
                    # Map string to enum
                    try:
                        foe_type = FoeType(detected_foe.foe_type)
                    except ValueError:
                        foe_type = FoeType.unknown
                    
                    foe = Foe(
                        detection=detection,
                        foe_type=foe_type,
                        confidence=detected_foe.confidence,
                        bounding_box=detected_foe.bounding_box,
                        description=detected_foe.description
                    )
                    detection.foes.append(foe)
                
                session.add(detection)
                safe_commit(session)
                
                logger.info(
                    f"Created detection for {camera.name}: "
                    f"{len(detection.foes)} foe(s) detected"
                )
                
                return detection
                
        except Exception as e:
            logger.error(f"Error processing detection for {camera.name}: {e}")
            return None
    
    def get_primary_foe_type(self, detection: Detection) -> Optional[str]:
        """Get the primary foe type from a detection (highest confidence)."""
        if not detection.foes:
            return None
            
        primary_foe = max(detection.foes, key=lambda f: f.confidence)
        return primary_foe.foe_type.value
    
    def record_deterrent_action(self, detection_id: int, action_type: str, success: bool, details: Optional[str] = None):
        """Record a deterrent action taken for a detection."""
        with get_db_session() as session:
            action = DeterrentAction(
                detection_id=detection_id,
                action_type=action_type,
                timestamp=datetime.utcnow(),
                success=success,
                details=details
            )
            session.add(action)
            safe_commit(session)
            
            # Update detection status
            detection = session.get(Detection, detection_id)
            if detection:
                detection.status = DetectionStatus.deterred if success else DetectionStatus.failed
                safe_commit(session)