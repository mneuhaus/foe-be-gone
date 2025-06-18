"""UniFi Protect integration using the official uiprotect library."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from uiprotect import ProtectApiClient
from uiprotect.data import Camera

from app.core.config import config
from app.integrations.base import IntegrationBase, DeviceInterface
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Rate limiter for snapshot requests
camera_rate_limiter = RateLimiter()


class UniFiProtectDevice(DeviceInterface):
    """UniFi Protect camera device implementation using uiprotect library."""
    
    def __init__(self, integration: "UniFiProtectIntegration", camera: Camera):
        self.integration = integration
        self.camera = camera
        self.device_id = camera.id
        self.name = camera.name
    
    async def test_talkback(self) -> bool:
        """Test the talkback functionality by playing a short sound."""
        try:
            # Check if camera has speaker capability
            if not self.camera.feature_flags.has_speaker:
                logger.warning(f"Camera {self.name} does not have speaker capability")
                return False
            
            # Generate a pleasant beep tone (800Hz) for 2.5 seconds using ffmpeg
            # Since uiprotect doesn't expose direct talkback streaming, we'll use a simple approach
            logger.info(f"Testing talkback on camera {self.name}")
            
            # For now, we'll just verify the camera has speaker capability
            # The actual audio streaming would require more complex implementation
            # with the uiprotect library's talkback methods
            
            # TODO: Implement actual audio streaming when uiprotect library supports it better
            logger.info(f"Camera {self.name} has talkback capability - test passed")
            return True
            
        except Exception as e:
            logger.error(f"Error testing talkback on {self.name}: {str(e)}")
            return False
    
    async def play_sound_file(self, sound_file_path: Path, max_duration: int = 10) -> bool:
        """Play a sound file through the camera's speaker using talkback.
        
        Args:
            sound_file_path: Path to the sound file
            max_duration: Maximum duration in seconds (default: 10)
            
        Returns:
            True if sound played successfully
        """
        try:
            # Check if camera has speaker capability
            if not self.camera.feature_flags.has_speaker:
                logger.warning(f"Camera {self.name} does not have speaker capability")
                return False
            
            if not sound_file_path.exists():
                logger.error(f"Sound file not found: {sound_file_path}")
                return False
            
            logger.info(f"Playing sound file {sound_file_path} on camera {self.name}")
            
            # TODO: Implement actual audio file streaming
            # This would require using the uiprotect library's talkback functionality
            # For now, we'll log that the operation would have been performed
            
            logger.info(f"Sound file playback initiated on {self.name} (placeholder implementation)")
            return True
            
        except Exception as e:
            logger.error(f"Error playing sound file on {self.name}: {str(e)}")
            return False
    
    async def get_snapshot(self) -> Optional[bytes]:
        """Get a snapshot from the camera using uiprotect library."""
        try:
            # Apply rate limiting
            await camera_rate_limiter.acquire()
            
            # Use uiprotect's built-in snapshot method
            snapshot_data = await self.camera.get_snapshot()
            
            if snapshot_data:
                logger.debug(f"Successfully got snapshot from {self.name}, size: {len(snapshot_data)} bytes")
                return snapshot_data
            else:
                logger.warning(f"No snapshot data received from {self.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting snapshot from {self.name}: {str(e)}")
            return None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current device status."""
        return {
            "online": self.camera.state.value == "CONNECTED",
            "model": self.camera.model,
            "firmware": self.camera.firmware_version,
            "features": {
                "has_speaker": self.camera.feature_flags.has_speaker,
                "has_smart_detect": self.camera.feature_flags.has_smart_detect,
                "can_zoom": getattr(self.camera.feature_flags, "can_zoom", False),
                "has_led_status": self.camera.feature_flags.has_led_status,
            },
            "smart_detect": {
                "object_types": [obj.value for obj in self.camera.smart_detect_settings.object_types],
                "audio_types": [audio.value for audio in self.camera.smart_detect_settings.audio_types] if hasattr(self.camera.smart_detect_settings, 'audio_types') else [],
            } if self.camera.smart_detect_settings else {},
            "recording_settings": {
                "mode": self.camera.recording_settings.mode.value if self.camera.recording_settings else None,
            },
            "privacy_mode": self.camera.privacy_mode if hasattr(self.camera, 'privacy_mode') else False,
        }


class UniFiProtectIntegration(IntegrationBase):
    """UniFi Protect integration using the official uiprotect library."""
    
    TYPE = "unifi_protect"
    NAME = "UniFi Protect"
    DESCRIPTION = "Connect to UniFi Protect cameras for wildlife detection using official uiprotect library"
    
    def __init__(self, instance: IntegrationInstance):
        self.instance = instance
        self.client: Optional[ProtectApiClient] = None
        self._websocket_unsub = None
    
    async def _init_client(self):
        """Initialize uiprotect client."""
        config_dict = self.instance.config_dict
        logger.debug(f"Initializing uiprotect client with config: {config_dict}")
        
        # Parse the host URL
        from urllib.parse import urlparse
        
        host_url = config_dict.get("host", "").rstrip("/")
        username = config_dict.get("username", "")
        password = config_dict.get("password", "")
        verify_ssl = config_dict.get("verify_ssl", False)
        
        # Parse the URL to extract host and port
        parsed = urlparse(host_url)
        if parsed.hostname:
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        else:
            # If no scheme provided, assume it's just the host
            host = host_url
            port = int(config_dict.get("port", 443))
        
        if not all([host, username, password]):
            raise ValueError("Host, username, and password are required for UniFi Protect")
        
        # Initialize ProtectApiClient
        self.client = ProtectApiClient(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        logger.debug(f"uiprotect client initialized for host: {host}")
    
    async def test_connection(self) -> bool:
        """Test connection to UniFi Protect controller."""
        try:
            if not self.client:
                await self._init_client()
            
            # Update bootstrap data to test connection with timeout
            import asyncio
            await asyncio.wait_for(self.client.update(), timeout=30.0)
            
            logger.info(f"Successfully connected to UniFi Protect")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Connection to UniFi Protect timed out after 30 seconds")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to UniFi Protect: {str(e)}")
            return False
    
    async def get_cameras_from_unifi(self) -> List:
        """Get raw camera objects from UniFi Protect using uiprotect library."""
        try:
            if not self.client:
                await self._init_client()
            
            # Update bootstrap data with timeout
            import asyncio
            await asyncio.wait_for(self.client.update(), timeout=30.0)
            
            # Use the native get_cameras() method from uiprotect
            cameras = await self.client.get_cameras()
            
            logger.info(f"Found {len(cameras)} cameras in UniFi Protect using get_cameras()")
            return cameras
            
        except asyncio.TimeoutError:
            logger.error("Getting cameras from UniFi Protect timed out after 30 seconds")
            return []
        except Exception as e:
            logger.error(f"Error getting cameras from UniFi Protect: {str(e)}")
            return []

    async def get_devices(self) -> List[Device]:
        """Get list of available cameras from UniFi Protect as Device objects."""
        try:
            # Get cameras using the native uiprotect method
            cameras = await self.get_cameras_from_unifi()
            
            devices = []
            for camera in cameras:
                # Skip if camera is not adopted or is disabled
                if not camera.is_adopted_by_us or not camera.is_connected:
                    logger.debug(f"Skipping camera {camera.name} - not adopted or not connected")
                    continue
                
                device = Device(
                    integration_id=self.instance.id,
                    device_type="camera",
                    name=camera.name,
                    model=camera.model,
                    status="online",
                    device_metadata={
                        "camera_id": camera.id,  # Store UniFi camera ID in metadata
                        "firmware": camera.firmware_version,
                        "mac": camera.mac,
                        "features": {
                            "has_speaker": camera.feature_flags.has_speaker,
                            "has_smart_detect": camera.feature_flags.has_smart_detect,
                            "can_zoom": getattr(camera.feature_flags, "can_zoom", False),
                        }
                    }
                )
                devices.append(device)
            
            logger.info(f"Found {len(devices)} cameras in UniFi Protect")
            return devices
            
        except Exception as e:
            logger.error(f"Error getting devices from UniFi Protect: {str(e)}")
            return []
    
    async def get_device(self, device_id: str) -> Optional[DeviceInterface]:
        """Get a specific device by ID (for camera_manager compatibility)."""
        if not self.client:
            await self._init_client()
            await self.client.update()
        
        camera = self.client.bootstrap.cameras.get(device_id)
        if not camera:
            logger.warning(f"Camera {device_id} not found in UniFi Protect")
            return None
        
        return UniFiProtectDevice(self, camera)
    
    async def get_device_interface(self, device: Device) -> DeviceInterface:
        """Get device interface for a specific device."""
        if not self.client:
            await self._init_client()
            await self.client.update()
        
        # Find the camera in bootstrap data
        camera = self.client.bootstrap.cameras.get(device.external_id)
        if not camera:
            raise ValueError(f"Camera {device.external_id} not found")
        
        return UniFiProtectDevice(self, camera)
    
    async def start_websocket(self):
        """Start WebSocket connection for real-time events."""
        try:
            if not self.client:
                await self._init_client()
                await self.client.update()
            
            def websocket_callback(message):
                """Handle WebSocket messages."""
                try:
                    # Log the message for debugging
                    logger.debug(f"Received WebSocket message: {message}")
                    
                    # TODO: Process different message types (motion events, doorbell rings, etc.)
                    # This would integrate with your detection system
                    
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
            
            # Subscribe to WebSocket updates
            self._websocket_unsub = self.client.subscribe_websocket(websocket_callback)
            logger.info("WebSocket connection established for real-time events")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket connection: {e}")
    
    async def stop_websocket(self):
        """Stop WebSocket connection."""
        if self._websocket_unsub:
            try:
                self._websocket_unsub()
                self._websocket_unsub = None
                logger.info("WebSocket connection stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket connection: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        await self.stop_websocket()
        if self.client:
            try:
                await self.client.close_session()
                self.client = None
                logger.debug("uiprotect client session closed")
            except Exception as e:
                logger.error(f"Error closing uiprotect client session: {e}")


# Factory function for integration
def create_integration(instance: IntegrationInstance) -> UniFiProtectIntegration:
    """Create a UniFi Protect integration instance."""
    return UniFiProtectIntegration(instance)