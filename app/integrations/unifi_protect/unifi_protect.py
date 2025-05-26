import ssl
import httpx
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os
import subprocess

from app.integrations.base import IntegrationBase, DeviceInterface
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
import base64

logger = logging.getLogger(__name__)


class UniFiProtectDevice(DeviceInterface):
    """UniFi Protect camera device implementation."""
    
    def __init__(self, integration: "UniFiProtectIntegration", device_data: Dict[str, Any]):
        self.integration = integration
        self.device_data = device_data
        self.device_id = device_data["id"]
        self.name = device_data["name"]
    
    async def test_talkback(self) -> bool:
        """Test the talkback functionality by playing a short sound."""
        try:
            # Check if camera has speaker capability
            if not self.device_data.get("featureFlags", {}).get("hasSpeaker", False):
                logger.warning(f"Camera {self.name} does not have speaker capability")
                return False
            
            # Create talkback session
            url = f"{self.integration.host}/proxy/protect/integration/v1/cameras/{self.device_id}/talkback-session"
            response = await self.integration._client.post(url)
            
            if response.status_code == 200:
                talkback_info = response.json()
                logger.info(f"Talkback session created: {talkback_info}")
                
                # Get RTP URL and audio parameters
                rtp_url = talkback_info.get('url')
                codec = talkback_info.get('codec', 'opus')
                sample_rate = talkback_info.get('samplingRate', 24000)
                
                # Use a short test sound - dog barking to deter animals
                test_sound = "/Volumes/Sites/crow-be-gone.neuhaus.nrw/public/sounds/crows/short-lo-fi-dog-barking_F_minor.wav"
                
                # If test sound doesn't exist, use TTS
                if not os.path.exists(test_sound):
                    # Use ffmpeg with flite TTS to say "Test sound"
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-re',  # Read input at native frame rate
                        '-f', 'lavfi',
                        '-i', 'flite=text=\'Test sound\':voice=slt',
                        '-c:a', codec,
                        '-strict', '-2',
                        '-b:a', '24k',
                        '-f', 'rtp',
                        rtp_url
                    ]
                else:
                    # Use the test sound file
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-re',  # Read input at native frame rate
                        '-i', test_sound,
                        '-c:a', codec,
                        '-strict', '-2',
                        '-b:a', '24k',
                        '-f', 'rtp',
                        rtp_url
                    ]
                
                # Run ffmpeg command with timeout
                logger.info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
                
                # Run in background and limit duration to 2 seconds
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait for up to 3 seconds for the sound to play
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3.0)
                    if process.returncode != 0:
                        logger.error(f"ffmpeg error: {stderr.decode()}")
                        return False
                except asyncio.TimeoutError:
                    # This is expected - ffmpeg will keep streaming until we stop it
                    process.terminate()
                    await process.wait()
                
                logger.info("Talkback test completed successfully")
                return True
            else:
                logger.error(f"Failed to create talkback session: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error testing talkback: {str(e)}")
            return False
        
    async def get_snapshot(self) -> Optional[bytes]:
        """Get current snapshot from camera."""
        try:
            # Get snapshot URL from UniFi Protect API
            url = f"{self.integration.host}/proxy/protect/integration/v1/cameras/{self.device_id}/snapshot"
            response = await self.integration._client.get(url)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to get snapshot: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting snapshot: {str(e)}")
            return None
        
    async def get_status(self) -> Dict[str, Any]:
        """Get current device status."""
        return {
            "online": self.device_data.get("state") == "CONNECTED",
            "model": self.device_data.get("modelKey", "Unknown"),
            "features": self.device_data.get("featureFlags", {}),
            "smart_detect": self.device_data.get("smartDetectSettings", {})
        }


class UniFiProtectIntegration(IntegrationBase):
    """UniFi Protect integration for camera management."""
    
    TYPE = "unifi_protect"
    NAME = "UniFi Protect"
    DESCRIPTION = "Connect to UniFi Protect cameras for wildlife detection"
    
    def __init__(self, instance: IntegrationInstance):
        self.instance = instance
        self.host = None
        self.api_key = None
        self._client = None
        self._ssl_context = None
        
    def _init_client(self):
        """Initialize HTTP client with proper SSL handling."""
        config = self.instance.config_dict
        logger.info(f"UniFi config: {config}")
        self.host = config.get("host", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        
        # Create SSL context that accepts self-signed certificates
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create HTTP client with custom SSL context
        self._client = httpx.AsyncClient(
            verify=self._ssl_context,
            timeout=httpx.Timeout(30.0),
            headers={
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
                "User-Agent": "Foe-Be-Gone/1.0"
            }
        )
        
    async def test_connection(self) -> bool:
        """Test connection to UniFi Protect controller."""
        try:
            if not self._client:
                self._init_client()
                
            if not self.host or not self.api_key:
                logger.error("Missing host or API key configuration")
                return False
                
            # Test API endpoint and try to get system name
            url = f"{self.host}/proxy/protect/integration/v1/meta/info"
            response = await self._client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Connected to UniFi Protect version: {data.get('applicationVersion', 'Unknown')}")
                
                # Try to get NVR info for a better name
                await self._update_instance_name()
                
                return True
            elif response.status_code == 401:
                logger.error("Invalid API key")
                return False
            else:
                logger.error(f"Connection failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def _update_instance_name(self):
        """Try to update the instance name with NVR information."""
        try:
            # Use the correct API endpoint from the documentation
            nvr_url = f"{self.host}/proxy/protect/integration/v1/nvrs"
            response = await self._client.get(nvr_url)
            
            if response.status_code == 200:
                data = response.json()
                
                # According to the docs, this returns NVR details with a name field
                nvr_name = data.get("name")
                
                # Build a better name
                if nvr_name:
                    new_name = f"UniFi Protect - {nvr_name}"
                else:
                    # Keep the default name
                    return
                
                # Update the instance name in the database
                from sqlmodel import Session
                from app.core.database import engine
                
                with Session(engine) as session:
                    self.instance.name = new_name
                    session.add(self.instance)
                    session.commit()
                    
                logger.info(f"Updated instance name to: {new_name}")
                
        except Exception as e:
            # This is optional functionality, so we don't fail if it doesn't work
            logger.debug(f"Could not update instance name: {str(e)}")
            
    async def get_devices(self) -> List[Device]:
        """Discover all available cameras from UniFi Protect."""
        devices = []
        
        try:
            if not self._client:
                self._init_client()
                
            # Get all cameras from UniFi Protect
            url = f"{self.host}/proxy/protect/integration/v1/cameras"
            response = await self._client.get(url)
            
            if response.status_code != 200:
                logger.error(f"Failed to get cameras: {response.status_code}")
                return devices
                
            cameras = response.json()
            
            # Get enabled cameras from config
            enabled_cameras = self.instance.config_dict.get("enabled_cameras", [])
            
            # If no cameras are explicitly enabled, don't return any
            if not enabled_cameras:
                return devices
            
            for camera in cameras:
                # Only include cameras that are enabled in config
                if camera["id"] not in enabled_cameras:
                    continue
                    
                device = Device(
                    integration_id=self.instance.id,
                    device_type="camera",
                    name=camera["name"],
                    model=camera.get("modelKey", "Unknown"),
                    status="online" if camera.get("state") == "CONNECTED" else "offline",
                    device_metadata={
                        "camera_id": camera["id"],
                        "features": camera.get("featureFlags", {}),
                        "smart_detect": camera.get("smartDetectSettings", {})
                    },
                    capabilities=camera.get("featureFlags", {})
                )
                
                # For UniFi cameras, we'll use the snapshot endpoint directly
                # instead of storing base64 data which might be too large
                device.current_image_url = f"/api/integrations/{self.instance.id}/devices/{camera['id']}/snapshot"
                
                devices.append(device)
                
        except Exception as e:
            logger.error(f"Failed to get devices: {str(e)}")
            
        return devices
        
    async def get_device(self, device_id: str) -> Optional[DeviceInterface]:
        """Get a specific device interface."""
        try:
            if not self._client:
                self._init_client()
                
            # Get camera details
            url = f"{self.host}/proxy/protect/integration/v1/cameras"
            response = await self._client.get(url)
            
            if response.status_code != 200:
                return None
                
            cameras = response.json()
            
            for camera in cameras:
                if camera["id"] == device_id:
                    return UniFiProtectDevice(self, camera)
                    
        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {str(e)}")
            
        return None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup client."""
        if self._client:
            await self._client.aclose()
            self._client = None