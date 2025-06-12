"""Detection processing service for analyzing images and managing detections."""

import logging
import io
import os
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image
from sqlmodel import Session, select

from app.models.device import Device
from app.models.detection import Detection, Foe, DetectionStatus, DeterrentAction, FoeType
from app.models.setting import Setting
from app.services.yolo_detector import YOLOv11DetectionService, YOLODetection
from app.services.visual_hash_service import calculate_detection_hash
from app.core.session import get_db_session, safe_commit
from app.core.config import config

logger = logging.getLogger(__name__)


class DetectionProcessor:
    """Processes camera snapshots to detect foes and manage detection records."""
    
    def __init__(self, use_yolo: Optional[bool] = None):
        """
        Initialize the detection processor.
        
        Args:
            use_yolo: Whether to use YOLO for initial animal detection (None = use config)
        """
        self.use_yolo = use_yolo if use_yolo is not None else config.YOLO_ENABLED
        self.yolo_confidence_threshold = config.YOLO_CONFIDENCE_THRESHOLD
        self.yolo_detector = None
        self.species_detector = None
        self._ollama_detector = None  # Keep reference for cleanup
        
        # Initialize YOLO detector if enabled
        if self.use_yolo:
            try:
                self.yolo_detector = YOLOv11DetectionService()
                logger.info(f"YOLOv11 detector initialized successfully (confidence threshold: {self.yolo_confidence_threshold})")
            except Exception as e:
                logger.error(f"Failed to initialize YOLO detector: {e}")
                self.use_yolo = False
        
        # Initialize species detector if enabled
        self.use_species_identification = config.SPECIES_IDENTIFICATION_ENABLED
        if self.use_species_identification:
            try:
                if config.SPECIES_IDENTIFICATION_PROVIDER == "ollama":
                    from app.services.ollama_species_detector import OllamaSpeciesDetector
                    self._ollama_detector = OllamaSpeciesDetector(
                        model=config.OLLAMA_MODEL,
                        ollama_host=config.OLLAMA_HOST
                    )
                    self.species_detector = self._ollama_detector
                    logger.info(f"Ollama species detector initialized with model: {config.OLLAMA_MODEL}")
                else:
                    # Use Qwen detector - import only when needed
                    from app.services.qwen_species_detector import QwenSpeciesDetector
                    self.species_detector = QwenSpeciesDetector()
                    logger.info("Qwen species detector initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize species detector ({config.SPECIES_IDENTIFICATION_PROVIDER}): {e}")
                self.species_detector = None
                self.use_species_identification = False
        else:
            self.species_detector = None
            logger.info("Species identification disabled via config")
        
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
    
    def run_yolo_detection(self, image_data: bytes) -> Dict[str, Any]:
        """Run YOLO detection on image data.
        
        Returns:
            Dict containing detection results and metadata
        """
        if not self.yolo_detector:
            return {"detections": [], "foe_classifications": {}, "yolo_duration_ms": 0}
        
        start_time = time.time()
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Get YOLO detections (animals only) with configured confidence threshold
            detections = self.yolo_detector.detect_animals(
                image, 
                confidence_threshold=self.yolo_confidence_threshold
            )
            
            # Convert to serializable format
            detection_data = []
            for det in detections:
                detection_data.append({
                    "class_name": det.class_name,
                    "confidence": det.confidence,
                    "bbox": det.bbox,
                    "category": det.category
                })
            
            duration_ms = round((time.time() - start_time) * 1000)
            logger.info(f"YOLO detection completed in {duration_ms}ms, found {len(detections)} animals")
            
            return {
                "detections": detection_data,
                "foe_classifications": {},  # No longer done by YOLO
                "total_animals": len(detections),  # All detections are animals
                "total_foes": 0,  # Will be determined by species ID
                "yolo_duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000)
            logger.error(f"Error running YOLO detection after {duration_ms}ms: {e}")
            return {"detections": [], "foe_classifications": {}, "error": str(e), "yolo_duration_ms": duration_ms}
    
    async def run_species_identification(self, image_data: bytes, yolo_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run species identification on detected objects using Ollama or Qwen.
        
        Args:
            image_data: Raw image bytes
            yolo_results: Results from YOLO detection
            
        Returns:
            Dict containing species identification results
        """
        if not self.species_detector or not yolo_results.get("detections"):
            return {"species_identifications": [], "total_cost": 0.0, "species_duration_ms": 0}
        
        start_time = time.time()
        detections_count = len(yolo_results.get("detections", []))
        
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            species_results = []
            total_cost = 0.0
            
            # Identify species for each detected object
            for i, detection in enumerate(yolo_results["detections"]):
                bbox = detection.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                
                detection_start = time.time()
                try:
                    # Run species identification on cropped region
                    species_result = await self.species_detector.identify_species(
                        image, 
                        tuple(bbox)  # Convert to tuple (x1, y1, x2, y2)
                    )
                    
                    detection_duration = round((time.time() - detection_start) * 1000)
                    
                    # Add detection context
                    result_dict = {
                        "original_detection": detection,
                        "species_result": species_result.model_dump(),
                        "bbox": bbox,
                        "detection_duration_ms": detection_duration
                    }
                    
                    species_results.append(result_dict)
                    
                    if species_result.cost:
                        total_cost += species_result.cost
                    
                    # Log the identification
                    if species_result.identifications:
                        species_id = species_result.identifications[0]
                        logger.info(f"Species identified in {detection_duration}ms: {species_id.species} "
                                  f"(foe_type: {species_id.foe_type}, "
                                  f"confidence: {species_id.confidence:.2f})")
                    else:
                        logger.info(f"No species identified in {detection_duration}ms for detection {i+1}")
                
                except Exception as e:
                    detection_duration = round((time.time() - detection_start) * 1000)
                    logger.error(f"Error identifying species for detection {i+1} after {detection_duration}ms: {e}")
                    continue
            
            total_duration_ms = round((time.time() - start_time) * 1000)
            avg_duration_per_detection = round(total_duration_ms / detections_count) if detections_count > 0 else 0
            
            logger.info(f"Species identification completed in {total_duration_ms}ms for {detections_count} detections "
                       f"(avg {avg_duration_per_detection}ms per detection)")
            
            return {
                "species_identifications": species_results,
                "total_cost": total_cost,
                "identifications_count": len(species_results),
                "species_duration_ms": total_duration_ms,
                "avg_duration_per_detection_ms": avg_duration_per_detection
            }
            
        except Exception as e:
            total_duration_ms = round((time.time() - start_time) * 1000)
            logger.error(f"Error during species identification after {total_duration_ms}ms: {e}")
            return {"species_identifications": [], "total_cost": 0.0, "error": str(e), "species_duration_ms": total_duration_ms}
    
    async def process_snapshot(self, camera: Device, image_data: bytes) -> Optional[Detection]:
        """
        Process a camera snapshot using YOLO + Ollama species identification.
        
        Uses YOLO for fast animal detection, then Ollama for species identification
        to determine if detected animals are foes. No OpenAI API calls are made.
        
        Args:
            camera: Camera device that captured the image
            image_data: Raw image bytes
            
        Returns:
            Detection record if snapshot should be saved based on capture level, None otherwise
        """
        # Get settings from database
        snapshot_capture_level = 1  # Default: AI Detection
        
        with get_db_session() as session:
            # Get snapshot capture level (0=Foe Deterred, 1=AI Detection, 2=All Snapshots)
            capture_level_setting = session.get(Setting, 'snapshot_capture_level')
            if capture_level_setting:
                try:
                    snapshot_capture_level = int(capture_level_setting.value)
                except ValueError:
                    pass
        
        # Track overall processing time
        processing_start_time = time.time()
        
        # Save snapshot
        image_path = self.save_snapshot(image_data, camera.name)
        
        # Run YOLO detection first if enabled
        yolo_results = None
        species_results = None
        animals_detected = False
        foes_detected = False
        total_ai_cost = 0.0
        
        if self.use_yolo:
            logger.info(f"Running YOLO animal detection for {camera.name}")
            yolo_results = self.run_yolo_detection(image_data)
            animals_detected = yolo_results.get("total_animals", 0) > 0
            
            # Run species identification on detected animals
            if yolo_results.get("detections") and self.species_detector:
                logger.info(f"Running species identification for {len(yolo_results['detections'])} detected animals in {camera.name}")
                species_results = await self.run_species_identification(image_data, yolo_results)
                total_ai_cost += species_results.get("total_cost", 0.0)
                
                # Check if species identification found any foes
                for species_data in species_results.get("species_identifications", []):
                    species_result = species_data.get("species_result", {})
                    for identification in species_result.get("identifications", []):
                        if identification.get("foe_type"):
                            foes_detected = True
                            break
                    if foes_detected:
                        break
                
                if foes_detected:
                    logger.info(f"Species identification found foes in {camera.name}")
                elif animals_detected:
                    logger.info(f"YOLO found {yolo_results.get('total_animals', 0)} animals in {camera.name}, but no foes identified by species detector")
            elif animals_detected:
                logger.info(f"YOLO found {yolo_results.get('total_animals', 0)} animals in {camera.name}, but no species detector available")
            else:
                logger.info(f"YOLO found no animals in {camera.name}")
        
        # Determine if we should save this snapshot based on capture level and what we found
        should_save_snapshot = False
        
        if snapshot_capture_level == 2:  # All snapshots
            should_save_snapshot = True
            logger.info(f"Saving snapshot for {camera.name} (capture level: all snapshots)")
        elif snapshot_capture_level == 1:  # Object recognized
            should_save_snapshot = animals_detected
            if should_save_snapshot:
                logger.info(f"Saving snapshot for {camera.name} (capture level: object recognized, animals detected)")
        elif snapshot_capture_level == 0:  # Foe identified only
            should_save_snapshot = foes_detected
            if should_save_snapshot:
                logger.info(f"Saving snapshot for {camera.name} (capture level: foe identified, foes detected)")
        
        # Save detection if we should
        if should_save_snapshot:
            # Create appropriate scene description
            if foes_detected:
                scene_description = f"YOLO detected {yolo_results.get('total_animals', 0)} animal(s), species identification found foes"
            elif animals_detected:
                if self.species_detector:
                    scene_description = f"YOLO detected {yolo_results.get('total_animals', 0)} animal(s), species identification found no foes"
                else:
                    scene_description = f"YOLO detected {yolo_results.get('total_animals', 0)} animal(s), no species identification available"
            else:
                scene_description = f"Snapshot saved without animal detection (capture level: {snapshot_capture_level})"
            
            # Calculate total processing time
            total_processing_ms = round((time.time() - processing_start_time) * 1000)
            
            # Calculate visual hash for similarity grouping
            visual_hash = calculate_detection_hash(str(image_path))
            if visual_hash:
                logger.debug(f"Calculated visual hash for detection: {visual_hash}")
            else:
                logger.warning(f"Failed to calculate visual hash for image: {image_path}")
            
            with get_db_session() as session:
                detection = Detection(
                    device_id=camera.id,
                    image_path=str(image_path),
                    timestamp=datetime.utcnow(),
                    status=DetectionStatus.PROCESSED,
                    visual_hash=visual_hash,
                    ai_response={
                        "scene_description": scene_description,
                        "yolo_results": yolo_results,
                        "species_results": species_results,
                        "yolo_only": True,  # No OpenAI used
                        "performance_metrics": {
                            "yolo_enabled": self.use_yolo,
                            "yolo_threshold": self.yolo_confidence_threshold if self.use_yolo else None,
                            "species_identification_enabled": bool(self.species_detector),
                            "total_processing_ms": total_processing_ms,
                            "yolo_duration_ms": yolo_results.get("yolo_duration_ms", 0) if yolo_results else 0,
                            "species_duration_ms": species_results.get("species_duration_ms", 0) if species_results else 0,
                            "species_avg_per_detection_ms": species_results.get("avg_duration_per_detection_ms", 0) if species_results else 0
                        }
                    },
                    processed_at=datetime.utcnow(),
                    ai_cost=total_ai_cost  # Only Ollama costs, no OpenAI
                )
                session.add(detection)
                session.flush()  # Flush to get the detection ID
                
                # Add foes from species identification results if any
                if foes_detected and species_results:
                    for species_data in species_results.get("species_identifications", []):
                        species_result = species_data.get("species_result", {})
                        bbox = species_data.get("bbox", [])
                        
                        for identification in species_result.get("identifications", []):
                            foe_type = identification.get("foe_type")
                            if foe_type:
                                # Convert bbox format if available
                                bounding_box = {}
                                if len(bbox) == 4:
                                    bounding_box = {
                                        "x": bbox[0],
                                        "y": bbox[1], 
                                        "width": bbox[2] - bbox[0],
                                        "height": bbox[3] - bbox[1]
                                    }
                                
                                foe = Foe(
                                    foe_type=foe_type,
                                    confidence=identification.get("confidence", 0.0),
                                    bounding_box=bounding_box,
                                    detection_id=detection.id,
                                    description=f"Species: {identification.get('species', 'Unknown')} - {identification.get('description', '')}"
                                )
                                session.add(foe)
                                logger.info(f"Added species ID {foe_type} foe: {identification.get('species')} "
                                          f"(confidence: {identification.get('confidence', 0.0):.2f})")
                
                safe_commit(session)
                
                if foes_detected:
                    logger.info(f"Created detection for {camera.name} with {len(detection.foes)} foe(s) in {total_processing_ms}ms "
                              f"(YOLO: {yolo_results.get('yolo_duration_ms', 0)}ms, "
                              f"Species: {species_results.get('species_duration_ms', 0)}ms, "
                              f"Cost: ${total_ai_cost:.6f})")
                else:
                    logger.info(f"Created detection for {camera.name} with no foes in {total_processing_ms}ms "
                              f"(YOLO: {yolo_results.get('yolo_duration_ms', 0)}ms, "
                              f"Animals detected: {animals_detected})")
                
                return detection
        
        # If we reach here, we're not saving the snapshot
        if animals_detected:
            
            logger.info(f"Not saving snapshot for {camera.name} - animals detected but capture level requires foes (level: {snapshot_capture_level})")
        else:
            logger.debug(f"Not saving snapshot for {camera.name} - no animals detected and capture level {snapshot_capture_level} doesn't require saving")
        
        # Delete the saved image since we're not keeping it
        try:
            os.remove(image_path)
        except Exception:
            pass
        return None
    
    def get_primary_foe_type(self, detection_id: int) -> Optional[str]:
        """Get the primary foe type from a detection (highest confidence)."""
        # Always get fresh data from session to avoid detached object issues
        try:
            with get_db_session() as session:
                # Use joinedload to eagerly load foes relationship
                from sqlalchemy.orm import joinedload
                fresh_detection = session.exec(
                    select(Detection)
                    .options(joinedload(Detection.foes))
                    .where(Detection.id == detection_id)
                ).first()
                
                if not fresh_detection or not fresh_detection.foes:
                    return None
                    
                primary_foe = max(fresh_detection.foes, key=lambda f: f.confidence)
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
    
    async def cleanup(self):
        """Clean up resources like HTTP clients."""
        if self._ollama_detector:
            await self._ollama_detector.close()