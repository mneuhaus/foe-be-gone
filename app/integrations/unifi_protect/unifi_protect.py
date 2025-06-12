import ssl
import httpx
from typing import List, Dict, Any, Optional
import logging
import asyncio
import os
import subprocess
from pathlib import Path
import warnings

from app.integrations.base import IntegrationBase, DeviceInterface
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
import base64

# Suppress SSL warnings for self-signed certificates
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

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
                
                # Generate a pleasant beep tone (800Hz) for 2.5 seconds
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-f', 'lavfi',
                    '-i', 'sine=frequency=800:duration=2.5',  # 800Hz beep for 2.5 seconds
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
            if not self.device_data.get("featureFlags", {}).get("hasSpeaker", False):
                logger.warning(f"Camera {self.name} does not have speaker capability")
                return False
            
            # Validate sound file exists
            if not sound_file_path.exists():
                logger.error(f"Sound file does not exist: {sound_file_path}")
                return False
            
            # Create talkback session
            url = f"{self.integration.host}/proxy/protect/integration/v1/cameras/{self.device_id}/talkback-session"
            response = await self.integration._client.post(url)
            
            if response.status_code == 200:
                talkback_info = response.json()
                logger.info(f"Talkback session created for sound playback: {talkback_info}")
                
                # Get RTP URL and audio parameters
                rtp_url = talkback_info.get('url')
                codec = talkback_info.get('codec', 'opus')
                sample_rate = talkback_info.get('samplingRate', 24000)
                
                # Handle codec-specific sample rate requirements
                if codec == 'opus':
                    # Opus supports 8, 12, 16, 24, and 48 kHz
                    # Use 48kHz for best quality and compatibility
                    target_sample_rate = 48000
                    logger.info(f"Using 48kHz sample rate for Opus codec (camera requested {sample_rate}Hz)")
                else:
                    # Use the camera's preferred sample rate for other codecs
                    target_sample_rate = sample_rate
                
                # Stream the audio file to the camera with real-time pacing and duration limit
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-t', str(max_duration),        # Limit input duration to max_duration seconds
                    '-re',                          # Read input at its native frame rate (important for RTP streaming!)
                    '-i', str(sound_file_path),      # Input sound file
                    '-c:a', codec,                  # Audio codec
                    '-ar', str(target_sample_rate), # Sample rate (corrected for codec)
                    '-ac', '1',                     # Force mono channel
                    '-strict', '-2',
                    '-b:a', '24k',                  # Bitrate
                    '-f', 'rtp',                    # Output format
                    rtp_url                         # RTP destination
                ]
                
                # Run ffmpeg command with timeout
                logger.info(f"Playing sound file '{sound_file_path.name}' on camera {self.name} using codec '{codec}' at {target_sample_rate}Hz")
                logger.debug(f"ffmpeg command: {' '.join(ffmpeg_cmd)}")
                
                # Run in background with timeout based on file duration
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait for up to 10 seconds for the sound to play (most deterrent sounds should be shorter)
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
                    if process.returncode != 0:
                        error_msg = stderr.decode()
                        logger.error(f"ffmpeg failed to play {sound_file_path.name} on camera {self.name}: {error_msg}")
                        
                        # Check for common audio format issues
                        if "sample rate" in error_msg.lower():
                            logger.error(f"Audio sample rate issue - camera expects different rate")
                        elif "codec" in error_msg.lower():
                            logger.error(f"Audio codec issue - camera may not support {codec}")
                        
                        return False
                    else:
                        logger.debug(f"ffmpeg output: {stdout.decode()}")
                        
                except asyncio.TimeoutError:
                    # Terminate if taking too long
                    process.terminate()
                    await process.wait()
                    logger.warning(f"Sound playback timed out for {sound_file_path.name} on camera {self.name}")
                
                logger.info(f"Sound file '{sound_file_path.name}' played successfully on camera {self.name}")
                return True
            else:
                logger.error(f"Failed to create talkback session for sound playback: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error playing sound file {sound_file_path}: {str(e)}")
            return False
        
    async def get_snapshot(self) -> Optional[bytes]:
        """Get current snapshot from camera."""
        from app.utils.rate_limiter import camera_rate_limiter
        
        # Rate limit per integration instance
        from app.core.config import config
        await camera_rate_limiter.acquire(
            resource_id=self.integration.instance.id,
            calls_per_second=config.UNIFI_RATE_LIMIT_CALLS_PER_SECOND,
            burst=config.UNIFI_RATE_LIMIT_BURST
        )
        
        # Retry with exponential backoff for rate limits
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Get snapshot URL from UniFi Protect API
                url = f"{self.integration.host}/proxy/protect/integration/v1/cameras/{self.device_id}/snapshot"
                response = await self.integration._client.get(url)
            
                if response.status_code == 200:
                    return response.content
                elif response.status_code == 429:
                    # Rate limit - retry with backoff
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limit hit for {self.name}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for {self.name} after {max_retries} attempts")
                        return None
                else:
                    error_msg = f"Failed to get snapshot: HTTP {response.status_code}"
                    if response.status_code == 500:
                        error_msg += " - Camera may be offline or experiencing issues"
                    elif response.status_code == 404:
                        error_msg += " - Camera not found"
                    elif response.status_code == 403:
                        error_msg += " - Permission denied"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            except Exception as e:
                if attempt < max_retries - 1 and "429" not in str(e):
                    # Retry for other errors too
                    logger.warning(f"Error getting snapshot from {self.name}, retrying: {str(e)}")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Error getting snapshot from {self.name}: {str(e)}")
                    return None
        
        return None  # Should not reach here
        
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
        logger.debug(f"Initializing UniFi client with config: {config}")
        self.host = config.get("host", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        
        # Create HTTP client with SSL verification disabled
        # This is necessary for self-signed certificates
        self._client = httpx.AsyncClient(
            verify=False,  # Disable SSL verification completely
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
                "User-Agent": "Foe-Be-Gone/1.0"
            },
            follow_redirects=True,
            http2=False,  # Disable HTTP/2 which can cause issues with some UniFi setups
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.debug(f"Client initialized for host: {self.host}")
        
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
            logger.debug(f"Testing connection to: {url}")
            
            try:
                response = await self._client.get(url)
            except httpx.ConnectError as e:
                logger.error(f"Connection failed to {self.host}: {str(e)}")
                logger.error(f"ConnectError details: {type(e).__name__}, {e.args}")
                return False
            except httpx.TimeoutException as e:
                logger.error(f"Connection timeout to {self.host}: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error connecting to {self.host}: {type(e).__name__}: {str(e)}")
                return False
            
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
                    id=camera["id"],  # Use the UniFi camera ID as the device ID
                    integration_id=self.instance.id,
                    device_type="camera",
                    name=camera["name"],
                    model=camera.get("modelKey", "Unknown"),
                    status="online" if camera.get("state") == "CONNECTED" else "offline"
                )
                
                # Set metadata separately to ensure it's properly serialized
                device.device_metadata = {
                    "camera_id": camera["id"],
                    "features": camera.get("featureFlags", {}),
                    "smart_detect": camera.get("smartDetectSettings", {})
                }
                
                # Set capabilities separately as well
                device.capabilities = camera.get("featureFlags", {})
                
                # For UniFi cameras, we'll use the snapshot endpoint directly
                # instead of storing base64 data which might be too large
                device.current_image_url = f"api/integrations/{self.instance.id}/devices/{camera['id']}/snapshot"
                
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
            logger.debug(f"Fetching cameras from: {url}")
            
            try:
                response = await self._client.get(url)
            except httpx.ConnectError as e:
                logger.error(f"Connection failed to {self.host}: {str(e)}")
                logger.error(f"ConnectError details: {type(e).__name__}, {e.args}")
                raise Exception(f"All connection attempts failed")
            except httpx.TimeoutException as e:
                logger.error(f"Connection timeout to {self.host}: {str(e)}")
                raise Exception(f"Connection timeout")
            except Exception as e:
                logger.error(f"Unexpected error connecting to {self.host}: {type(e).__name__}: {str(e)}")
                raise
            
            if response.status_code == 401:
                logger.error("Authentication failed - invalid API key")
                raise Exception("Authentication failed")
            elif response.status_code != 200:
                logger.error(f"API returned status {response.status_code}")
                raise Exception(f"API error: {response.status_code}")
                
            cameras = response.json()
            logger.debug(f"Found {len(cameras)} cameras")
            
            for camera in cameras:
                if camera["id"] == device_id:
                    logger.debug(f"Found camera {device_id}: {camera.get('name')}")
                    return UniFiProtectDevice(self, camera)
            
            logger.error(f"Camera {device_id} not found in {len(cameras)} available cameras")
            available_ids = [c['id'] for c in cameras]
            logger.debug(f"Available camera IDs: {available_ids}")
                    
        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {str(e)}")
            raise
            
        return None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup client."""
        if self._client:
            await self._client.aclose()
            self._client = None