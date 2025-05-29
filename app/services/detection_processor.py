"""Detection processing service for analyzing images and managing detections."""

import logging
import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import imagehash
from PIL import Image
from sqlmodel import Session

from app.models.device import Device
from app.models.detection import Detection, Foe, DetectionStatus, DeterrentAction, FoeType
from app.models.setting import Setting
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
            # Get threshold from settings
            threshold = self.change_threshold
            with get_db_session() as session:
                phash_setting = session.get(Setting, 'phash_threshold')
                if phash_setting:
                    try:
                        threshold = int(phash_setting.value)
                    except ValueError:
                        pass
            
            hash1 = imagehash.hex_to_hash(current_hash)
            hash2 = imagehash.hex_to_hash(previous_hash)
            distance = hash1 - hash2
            
            logger.debug(f"Image hash distance: {distance} (threshold: {threshold})")
            return distance >= threshold
            
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
        # Get settings from database
        capture_all_snapshots = False
        phash_threshold = self.change_threshold
        
        with get_db_session() as session:
            # Check if we should capture all snapshots
            capture_all_setting = session.get(Setting, 'capture_all_snapshots')
            if capture_all_setting:
                capture_all_snapshots = capture_all_setting.value.lower() == 'true'
            
            # Get phash threshold
            phash_setting = session.get(Setting, 'phash_threshold')
            if phash_setting:
                try:
                    phash_threshold = int(phash_setting.value)
                except ValueError:
                    pass
        
        # Calculate image hash
        current_hash = self.calculate_image_hash(image_data)
        
        # Check if image has changed significantly
        if camera.last_image_hash and current_hash:
            try:
                hash1 = imagehash.hex_to_hash(current_hash)
                hash2 = imagehash.hex_to_hash(camera.last_image_hash)
                hash_distance = hash1 - hash2
                logger.info(f"Image change detected in {camera.name}: hash distance = {hash_distance} (threshold = {phash_threshold})")
            except Exception as e:
                logger.error(f"Error calculating hash distance: {e}")
                hash_distance = None
        else:
            hash_distance = None
            logger.info(f"No previous hash for {camera.name}, processing snapshot")
        
        # Check if there's significant change
        has_change = self.has_significant_change(current_hash, camera.last_image_hash)
        
        if not has_change and not capture_all_snapshots:
            logger.debug(f"No significant change in {camera.name}, skipping detection")
            return None
        
        # Update camera's last image hash
        with get_db_session() as session:
            camera_db = session.get(Device, camera.id)
            if camera_db:
                camera_db.last_image_hash = current_hash
                safe_commit(session)
        
        # Save snapshot
        image_path = self.save_snapshot(image_data, camera.name)
        
        # Only run AI detection if there's significant change
        if has_change:
            logger.info(f"Running AI detection for {camera.name} (change threshold exceeded)")
            # Run AI detection
            try:
                with get_db_session() as ai_session:
                    ai_detector = AIDetector(session=ai_session)
                    result = await ai_detector.detect_foes(image_data)
            
                if not result.foes_detected:
                    logger.info(f"No foes detected in {camera.name}")
                    return None
                
                # Create detection record with foes
                with get_db_session() as session:
                    detection = Detection(
                        device_id=camera.id,
                        image_path=str(image_path),
                        timestamp=datetime.utcnow(),
                        status=DetectionStatus.PROCESSED,
                        ai_response={
                            "scene_description": result.scene_description,
                            "hash_distance": hash_distance,
                            "phash_threshold": phash_threshold
                        },
                        processed_at=datetime.utcnow(),
                        ai_cost=result.cost
                    )
                    
                    # Add detected foes
                    for detected_foe in result.foes:
                        # Normalize foe type to uppercase string
                        foe_type_str = detected_foe.foe_type.upper()
                        # Validate it's a known type
                        if foe_type_str not in ["RATS", "CROWS", "CATS", "UNKNOWN"]:
                            foe_type_str = "UNKNOWN"
                        
                        foe = Foe(
                            detection=detection,
                            foe_type=foe_type_str,  # Store as string
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
                
        else:
            # No AI detection needed - just save snapshot if capture_all_snapshots is enabled
            if capture_all_snapshots:
                logger.info(f"Saving snapshot for {camera.name} without AI detection (below threshold)")
                with get_db_session() as session:
                    detection = Detection(
                        device_id=camera.id,
                        image_path=str(image_path),
                        timestamp=datetime.utcnow(),
                        status=DetectionStatus.PROCESSED,
                        ai_response={
                            "scene_description": "Snapshot saved without AI analysis (below change threshold)",
                            "hash_distance": hash_distance,
                            "phash_threshold": phash_threshold,
                            "skipped_ai": True
                        },
                        processed_at=datetime.utcnow(),
                        ai_cost=0.0  # No AI cost
                    )
                    session.add(detection)
                    safe_commit(session)
                    logger.info(f"Saved snapshot for {camera.name} without AI analysis")
                    return detection
            else:
                logger.debug(f"Skipping snapshot for {camera.name} (below threshold and capture_all_snapshots disabled)")
                # Delete the saved image since we're not keeping it
                try:
                    os.remove(image_path)
                except Exception:
                    pass
                return None
    
    def get_primary_foe_type(self, detection: Detection) -> Optional[str]:
        """Get the primary foe type from a detection (highest confidence)."""
        # Handle detached objects by getting fresh data from session
        try:
            if not detection.foes:
                # Try to get fresh detection with foes if object is detached
                with get_db_session() as session:
                    fresh_detection = session.get(Detection, detection.id)
                    if not fresh_detection or not fresh_detection.foes:
                        return None
                    primary_foe = max(fresh_detection.foes, key=lambda f: f.confidence)
                    return primary_foe.foe_type  # Already a string now
            else:
                primary_foe = max(detection.foes, key=lambda f: f.confidence)
                return primary_foe.foe_type  # Already a string now
        except Exception as e:
            logger.error(f"Error getting primary foe type: {e}")
            return None
    
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
                detection.status = DetectionStatus.DETERRED if success else DetectionStatus.FAILED
                safe_commit(session)