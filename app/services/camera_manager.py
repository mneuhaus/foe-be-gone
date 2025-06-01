"""Camera management service for handling device interactions."""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from sqlmodel import Session, select

from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.integrations import get_integration_class
from app.core.session import get_db_session
from app.services.camera_diagnostics import camera_diagnostics

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages camera devices and their integrations."""
    
    def __init__(self):
        """Initialize the camera manager."""
        self._integrations: Dict[str, Any] = {}
        
    def get_active_cameras(self) -> List[Device]:
        """Get all active camera devices from connected integrations."""
        with get_db_session() as session:
            cameras = session.exec(
                select(Device)
                .join(IntegrationInstance)
                .where(Device.device_type == "camera")
                .where(IntegrationInstance.status == "connected")
                .where(IntegrationInstance.enabled == True)
            ).all()
            
            # Detach from session to use outside context
            return [camera.model_copy() for camera in cameras]
    
    async def get_integration_handler(self, integration_instance: IntegrationInstance) -> Optional[Any]:
        """Get or create an integration handler."""
        integration_id = str(integration_instance.id)
        
        if integration_id not in self._integrations:
            try:
                integration_class = get_integration_class(integration_instance.integration_type)
                if integration_class:
                    self._integrations[integration_id] = integration_class(integration_instance)
                    logger.info(f"Created integration handler for {integration_instance.name}")
                else:
                    logger.error(f"Unknown integration type: {integration_instance.integration_type}")
                    return None
            except Exception as e:
                logger.error(f"Failed to create integration handler: {e}")
                return None
                
        return self._integrations.get(integration_id)
    
    async def capture_snapshot(self, camera: Device) -> Optional[bytes]:
        """Capture a snapshot from a camera device."""
        with get_db_session() as session:
            # Get fresh camera instance with integration
            camera_db = session.get(Device, camera.id)
            if not camera_db or not camera_db.integration:
                logger.error(f"Camera {camera.device_id} not found or has no integration")
                return None
                
            integration = camera_db.integration
            handler = await self.get_integration_handler(integration)
            
            if not handler:
                return None
                
            try:
                camera_id = camera_db.device_metadata.get("camera_id")
                if not camera_id:
                    logger.error(f"Camera {camera_db.name} has no camera_id in metadata")
                    return None
                    
                device_interface = await handler.get_device(camera_id)
                if not device_interface:
                    logger.error(f"Could not get device interface for camera {camera_id}")
                    return None
                    
                # Capture snapshot
                snapshot_data = await device_interface.get_snapshot()
                return snapshot_data
                
            except Exception as e:
                logger.error(f"Error capturing snapshot from {camera_db.name}: {e}")
                # Record error for diagnostics
                error_type = "HTTP 500" if "500" in str(e) else type(e).__name__
                camera_diagnostics.record_camera_error(
                    camera_id=camera_db.id,
                    camera_name=camera_db.name,
                    error_type=error_type,
                    error_details=str(e)
                )
                return None
    
    async def play_sound_on_camera(self, camera: Device, sound_file: Path, max_duration: int = 10) -> bool:
        """Play a sound file on a camera device.
        
        Args:
            camera: Camera device
            sound_file: Path to sound file
            max_duration: Maximum duration in seconds (default: 10)
            
        Returns:
            True if sound played successfully
        """
        with get_db_session() as session:
            # Get fresh camera instance with integration
            camera_db = session.get(Device, camera.id)
            if not camera_db or not camera_db.integration:
                logger.error(f"Camera {camera.device_id} not found or has no integration")
                return False
                
            integration = camera_db.integration
            handler = await self.get_integration_handler(integration)
            
            if not handler:
                return False
                
            try:
                camera_id = camera_db.device_metadata.get("camera_id")
                if not camera_id:
                    logger.error(f"Camera {camera_db.name} has no camera_id in metadata")
                    return False
                    
                logger.debug(f"Getting device interface for camera {camera_id}")
                device_interface = await handler.get_device(camera_id)
                if not device_interface:
                    logger.error(f"Could not get device interface for camera {camera_id}")
                    return False
                    
                # Play sound if supported
                if hasattr(device_interface, 'play_sound_file'):
                    logger.info(f"Playing sound {sound_file.name} on camera {camera_db.name} (max {max_duration}s)")
                    logger.debug(f"Sound file path: {sound_file}, exists: {sound_file.exists()}")
                    success = await device_interface.play_sound_file(sound_file, max_duration)
                    if success:
                        logger.info(f"Successfully played sound on camera {camera_db.name}")
                    else:
                        logger.warning(f"Failed to play sound on camera {camera_db.name}")
                    return success
                else:
                    logger.warning(f"Camera {camera_db.name} does not support sound playback method")
                    return False
                    
            except Exception as e:
                logger.error(f"Error playing sound on {camera_db.name}: {e}")
                return False
    
    async def cleanup(self):
        """Clean up all integration handlers."""
        for integration_id, handler in self._integrations.items():
            try:
                if hasattr(handler, 'cleanup'):
                    await handler.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up integration {integration_id}: {e}")
        
        self._integrations.clear()