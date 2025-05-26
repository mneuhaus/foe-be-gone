"""Background worker for periodic detection checks."""
import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import uuid
import io

import imagehash
from PIL import Image
from sqlmodel import Session, select
from app.core.database import engine
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.models.detection import Detection, Foe, DetectionStatus, DeterrentAction
from app.services.ai_detector import AIDetector
from app.services.sound_player import sound_player
from app.integrations.dummy_surveillance.dummy_surveillance import DummySurveillanceIntegration
from app.integrations import get_integration_class

logger = logging.getLogger(__name__)


class DetectionWorker:
    """Background worker that periodically checks cameras for foes."""
    
    def __init__(self, check_interval: int = 10, change_threshold: int = 10):
        """
        Initialize the detection worker.
        
        Args:
            check_interval: Seconds between detection checks (default: 10)
            change_threshold: Hamming distance threshold for significant image changes (default: 10)
        """
        self.check_interval = check_interval
        self.change_threshold = change_threshold
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.ai_detector = AIDetector()
        self._integrations: Dict[str, Any] = {}
        
    def _calculate_image_hash(self, image_data: bytes) -> str:
        """Calculate perceptual hash of image data."""
        try:
            image = Image.open(io.BytesIO(image_data))
            # Use average hash for good balance of speed and accuracy
            hash_value = imagehash.average_hash(image)
            return str(hash_value)
        except Exception as e:
            logger.error(f"Failed to calculate image hash: {e}")
            return ""
    
    def _has_significant_change(self, current_hash: str, previous_hash: Optional[str]) -> bool:
        """Check if image has changed significantly based on hash comparison."""
        if not previous_hash:
            # First image, consider it a change
            return True
            
        if not current_hash or not previous_hash:
            # Failed to calculate hash, assume change
            return True
            
        try:
            # Calculate Hamming distance between hashes
            current = imagehash.hex_to_hash(current_hash)
            previous = imagehash.hex_to_hash(previous_hash)
            distance = current - previous
            
            # If distance exceeds threshold, consider it a significant change
            is_changed = distance >= self.change_threshold
            if is_changed:
                logger.info(f"Significant image change detected (distance: {distance}, threshold: {self.change_threshold})")
            else:
                logger.debug(f"No significant change (distance: {distance}, threshold: {self.change_threshold})")
            
            return is_changed
            
        except Exception as e:
            logger.error(f"Failed to compare image hashes: {e}")
            # On error, assume change to be safe
            return True
    
    async def _play_sound_on_camera(self, device_interface, sound_file_path: Path) -> bool:
        """Play a sound file through the camera's speaker using talkback."""
        try:
            # Check if device interface has talkback capability
            if not hasattr(device_interface, 'play_sound_file'):
                logger.warning(f"Device interface does not support sound playback")
                return False
            
            # Use the device interface to play the sound file
            result = device_interface.play_sound_file(sound_file_path)
            if hasattr(result, '__await__'):
                return await result
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to play sound on camera: {e}")
            return False
        
    async def start(self):
        """Start the detection worker in a separate thread."""
        if self.is_running:
            logger.warning("Detection worker is already running")
            return
            
        self.is_running = True
        self._thread = threading.Thread(target=self._run_in_thread)
        self._thread.daemon = True
        self._thread.start()
        logger.info(f"Detection worker started with {self.check_interval}s interval")
        
    async def stop(self):
        """Stop the detection worker."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Detection worker stopped")
        
    def _run_in_thread(self):
        """Run the worker in a separate thread with its own event loop."""
        # Create a new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._run())
        except Exception as e:
            logger.error(f"Error in detection worker thread: {e}")
        finally:
            self._loop.close()
        
    async def _run(self):
        """Main worker loop."""
        while self.is_running:
            try:
                await self._check_all_cameras()
            except Exception as e:
                logger.error(f"Error in detection worker: {e}")
                
            # Wait for the next check
            await asyncio.sleep(self.check_interval)
            
    async def _check_all_cameras(self):
        """Check all active cameras for foes."""
        with Session(engine) as session:
            # Get all camera devices from active integrations
            cameras = session.exec(
                select(Device)
                .join(IntegrationInstance)
                .where(Device.device_type == "camera")
                .where(Device.status == "online")
                .where(IntegrationInstance.enabled == True)
            ).all()
            
            if cameras:
                logger.info(f"Checking {len(cameras)} active cameras")
            
            for camera in cameras:
                try:
                    await self._check_camera(camera, session)
                except Exception as e:
                    logger.error(f"Error checking camera {camera.id}: {e}")
                    
    async def _check_camera(self, camera: Device, session: Session):
        """Check a single camera for foes."""
        # Get the integration instance
        integration = camera.integration
        if not integration:
            logger.warning(f"Camera {camera.id} has no integration")
            return
            
        # Get or create the integration handler
        if integration.id not in self._integrations:
            integration_class = get_integration_class(integration.integration_type)
            if integration_class:
                if integration.integration_type == "dummy-surveillance":
                    handler = DummySurveillanceIntegration(
                        integration.id,
                        integration.config
                    )
                    await handler.connect()
                else:
                    # For other integrations like UniFi Protect
                    handler = integration_class(integration)
                    
                self._integrations[integration.id] = handler
            else:
                logger.warning(f"Unknown integration type: {integration.integration_type}")
                return
                
        handler = self._integrations[integration.id]
        
        # Get device interface from handler
        device_interface = None
        
        if integration.integration_type == "dummy-surveillance":
            # For dummy integration, get all devices and use the first one
            devices_result = handler.get_devices()
            if hasattr(devices_result, '__await__'):
                devices = await devices_result
            else:
                devices = devices_result
            if devices:
                device_interface = devices[0]
        else:
            # For real integrations like UniFi, get specific device by camera ID
            camera_id_from_metadata = camera.device_metadata.get("camera_id")
            if camera_id_from_metadata and hasattr(handler, 'get_device'):
                device_result = handler.get_device(camera_id_from_metadata)
                if hasattr(device_result, '__await__'):
                    device_interface = await device_result
                else:
                    device_interface = device_result
                
        if not device_interface:
            logger.warning(f"Device interface not found for camera {camera.id}")
            return
            
        # Get snapshot (handle both sync and async methods)
        snapshot_result = device_interface.get_snapshot()
        
        if hasattr(snapshot_result, '__await__'):
            snapshot_data = await snapshot_result
        else:
            snapshot_data = snapshot_result
            
        if not snapshot_data:
            return
            
        # Calculate image hash for change detection
        current_hash = self._calculate_image_hash(snapshot_data)
        if not current_hash:
            logger.warning(f"Failed to calculate hash for camera {camera.id}")
            return
            
        # Check if image has changed significantly
        has_changed = self._has_significant_change(current_hash, camera.last_image_hash)
        
        if not has_changed:
            logger.debug(f"No significant change detected for camera {camera.name}, skipping AI analysis")
            return
            
        logger.info(f"Significant change detected for camera {camera.name}, running AI analysis")
        
        # Update the camera's last image hash
        camera.last_image_hash = current_hash
        session.add(camera)
        session.commit()
            
        # Save snapshot to file
        snapshots_dir = Path("data/snapshots")
        snapshots_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow()
        filename = f"{camera.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        snapshot_path = snapshots_dir / filename
        
        with open(snapshot_path, 'wb') as f:
            f.write(snapshot_data)
            
        # Create detection record
        detection = Detection(
            device_id=camera.id,
            timestamp=timestamp,
            image_path=str(snapshot_path),
            status=DetectionStatus.PENDING
        )
        session.add(detection)
        session.commit()
        session.refresh(detection)
        
        
        # Run AI detection
        try:
            result = self.ai_detector.detect_foes(snapshot_data)
            # Log estimated AI cost to the detection
            try:
                detection.ai_cost = getattr(result, 'cost', None)
            except Exception:
                pass
            
            # Update detection with results
            detection.ai_response = {
                "scene_description": result.scene_description,
                "foes_detected": result.foes_detected,
                "foes_count": len(result.foes)
            }
            detection.status = DetectionStatus.PROCESSED
            detection.processed_at = datetime.utcnow()
            
            # Create foe records
            for detected_foe in result.foes:
                foe = Foe(
                    detection_id=detection.id,
                    foe_type=detected_foe.foe_type,
                    confidence=detected_foe.confidence,
                    bounding_box=detected_foe.bounding_box or {}
                )
                session.add(foe)
                
            # Update camera last detection time if foes found
            if result.foes_detected:
                camera.last_detection = datetime.utcnow()
                session.add(camera)
                
            session.commit()
            # Handle deterrent sound playback and logging
            if result.foes_detected:
                logger.info(
                    f"Foes detected on {camera.name}: "
                    f"{', '.join([f'{foe.foe_type} ({foe.confidence:.0%})' for foe in result.foes])}"
                )
                played_sounds = []
                foe_types_detected = set(foe.foe_type for foe in result.foes)
                for foe_type in foe_types_detected:
                    if foe_type == "unknown":
                        continue
                    try:
                        available_sounds = sound_player.get_available_sounds(foe_type)
                        if not available_sounds:
                            logger.warning(f"No deterrent sounds available for {foe_type}")
                            continue
                        selected_sound = sound_player._select_random_sound(available_sounds)
                        played_sounds.append(selected_sound.name)
                        success = await self._play_sound_on_camera(device_interface, selected_sound)
                        if success:
                            logger.info(f"Played deterrent sound '{selected_sound.name}' on camera {camera.name} for {foe_type}")
                        else:
                            logger.warning(f"Failed to play deterrent sound on camera {camera.name} for {foe_type}")
                        # Record action in database
                        action = DeterrentAction(
                            detection_id=detection.id,
                            action_type="sound",
                            action_details={"foe_type": foe_type, "sound_file": selected_sound.name},
                            success=bool(success)
                        )
                        session.add(action)
                    except Exception as e:
                        logger.error(f"Error playing sound on camera {camera.name} for {foe_type}: {e}")
                # Persist played_sounds list if any
                if played_sounds:
                    try:
                        detection.played_sounds = played_sounds
                        session.add(detection)
                        session.commit()
                    except Exception as e:
                        logger.error(f"Failed to record played_sounds for detection {detection.id}: {e}")
            
        except Exception as e:
            logger.error(f"AI detection failed for detection {detection.id}: {e}")
            detection.status = DetectionStatus.FAILED
            detection.ai_response = {"error": str(e)}
            session.commit()


# Global worker instance
detection_worker = DetectionWorker()