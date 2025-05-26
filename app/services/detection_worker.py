"""Background worker for periodic detection checks."""
import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import uuid

from sqlmodel import Session, select
from app.core.database import engine
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.models.detection import Detection, Foe, DetectionStatus
from app.services.ai_detector import AIDetector
from app.integrations.dummy_surveillance.dummy_surveillance import DummySurveillanceIntegration
from app.integrations import get_integration_class

logger = logging.getLogger(__name__)


class DetectionWorker:
    """Background worker that periodically checks cameras for foes."""
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize the detection worker.
        
        Args:
            check_interval: Seconds between detection checks (default: 30)
        """
        self.check_interval = check_interval
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.ai_detector = AIDetector()
        self._integrations: Dict[str, Any] = {}
        
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
        devices = handler.get_devices()
        device_interface = None
        
        # For dummy integration, we'll use the first available device
        # In a real integration, we'd match by device ID
        if integration.integration_type == "dummy-surveillance" and devices:
            device_interface = devices[0]
        else:
            # Match by device ID for real integrations
            for device in devices:
                if device.device_id == camera.id:
                    device_interface = device
                    break
                
        if not device_interface:
            logger.warning(f"Device interface not found for camera {camera.id}")
            return
            
        # Get snapshot
        snapshot_data = device_interface.get_snapshot()
        if not snapshot_data:
            return
            
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
            
            if result.foes_detected:
                logger.info(
                    f"Foes detected on {camera.name}: "
                    f"{', '.join([f'{foe.foe_type} ({foe.confidence:.0%})' for foe in result.foes])}"
                )
            
        except Exception as e:
            logger.error(f"AI detection failed for detection {detection.id}: {e}")
            detection.status = DetectionStatus.FAILED
            detection.ai_response = {"error": str(e)}
            session.commit()


# Global worker instance
detection_worker = DetectionWorker()