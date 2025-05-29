"""
Dummy Surveillance Integration

Simulates a surveillance system with a single camera for testing purposes.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import random
import asyncio
from enum import Enum
from pathlib import Path
import os
from app.integrations.base import IntegrationBase, DeviceInterface


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class DummyCameraDevice(DeviceInterface):
    """Dummy camera device implementation."""
    
    def __init__(self, device_id: str, name: str, integration):
        super().__init__(device_id, name, "camera")
        self.integration = integration
        self.status = "online"
        
    async def get_snapshot(self) -> Optional[bytes]:
        """Get a snapshot from the camera."""
        if self.integration.current_image_path:
            # Read the actual image file
            image_path = Path("public") / self.integration.current_image_path
            if image_path.exists():
                with open(image_path, 'rb') as f:
                    return f.read()
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the device."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.device_type,
            "status": self.status,
            "last_seen": self.last_seen.isoformat(),
            "current_image": f"public/{self.integration.current_image_path}" if self.integration.current_image_path else None
        }


class DummySurveillanceIntegration(IntegrationBase):
    """Dummy surveillance system integration for testing."""
    
    def __init__(self, integration_instance):
        """Initialize with an IntegrationInstance from the database."""
        from app.models.integration_instance import IntegrationInstance
        
        if isinstance(integration_instance, IntegrationInstance):
            self.integration_id = integration_instance.id
            self.config = integration_instance.config
            self.integration_instance = integration_instance
        else:
            # Legacy support
            self.integration_id = integration_instance
            self.config = {}
            self.integration_instance = None
            
        self.status = IntegrationStatus.DISCONNECTED
        self._is_running = False
        self.current_scenario = "nothing"
        self.current_image_path = None
        self._device = None
        self._scenario_index = 0
        self._scenarios = []
        
    async def connect(self) -> bool:
        """Simulate connection to surveillance system."""
        await asyncio.sleep(0.5)  # Simulate connection delay
        self.status = IntegrationStatus.CONNECTED
        self._is_running = True
        # Create dummy camera device
        self._device = DummyCameraDevice("dummy-cam-001", "Dummy Camera 1", self)
        # Initialize test scenarios
        self._init_test_scenarios()
        return True
        
    async def disconnect(self) -> bool:
        """Disconnect from surveillance system."""
        self._is_running = False
        self.status = IntegrationStatus.DISCONNECTED
        return True
        
    def get_cameras(self) -> List[Dict[str, Any]]:
        """Get list of available cameras."""
        if self.status != IntegrationStatus.CONNECTED:
            return []
            
        return [{
            "id": "dummy-cam-001",
            "name": "Dummy Camera 1",
            "model": None,
            "status": "online",
            "stream_url": f"rtsp://dummy.local/stream/1",
            "snapshot_url": f"http://dummy.local/snapshot/1",
            "capabilities": {
                "pan_tilt_zoom": False,
                "infrared": True,
                "motion_detection": True,
                "audio": True
            },
            "location": "Test Location",
            "firmware_version": "1.0.0-dummy",
            "last_seen": datetime.utcnow().isoformat()
        }]
        
    async def get_device(self, device_id: str) -> Optional[DeviceInterface]:
        """Get a specific device by ID."""
        if self.status != IntegrationStatus.CONNECTED:
            await self.connect()
            
        if self._device and self._device.device_id == device_id:
            return self._device
        return None
    
    async def get_camera_snapshot(self, camera_id: str) -> Optional[bytes]:
        """Get a snapshot from the camera (returns dummy data)."""
        if self.status != IntegrationStatus.CONNECTED:
            return None
            
        # In a real implementation, this would fetch actual image data
        # For now, return None to indicate no image available
        return None
        
    async def trigger_detection_test(self, camera_id: str) -> Dict[str, Any]:
        """Trigger a test detection event."""
        if self.status != IntegrationStatus.CONNECTED:
            return {"error": "Not connected"}
            
        # Simulate detection with random confidence
        detection_types = ["crow", "magpie", "raven", "cat", "unknown"]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "camera_id": camera_id,
            "detection": {
                "type": random.choice(detection_types),
                "confidence": round(random.uniform(0.6, 0.95), 2),
                "bounding_box": {
                    "x": random.randint(100, 500),
                    "y": random.randint(100, 300),
                    "width": random.randint(50, 150),
                    "height": random.randint(50, 150)
                }
            },
            "test_mode": True
        }
        
    async def get_devices(self) -> List:
        """Get all devices from this integration as database models."""
        from app.models.device import Device
        
        # Always connect first
        if self.status != IntegrationStatus.CONNECTED:
            await self.connect()
            
        if not self._device:
            return []
            
        # Create a Device model instance
        device = Device(
            device_id="dummy-cam-001",
            integration_id=self.integration_id,
            name="Dummy Camera",
            device_type="camera",
            status="online",
            current_image_url="public/dummy-surveillance/nothing/Terrassentür  - 5-26-2025, 09.07.18 GMT+2.jpg",
            device_metadata={
                "camera_id": "dummy-cam-001",
                "model": "Dummy Model",
                "firmware": "1.0.0",
                "capabilities": ["snapshot", "motion_detection"]
            }
        )
        return [device]
    
    async def test_connection(self) -> bool:
        """Test the connection to the integration."""
        try:
            await self.connect()
            return self.status == IntegrationStatus.CONNECTED
        except:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            "integration_id": self.integration_id,
            "type": "dummy-surveillance",
            "status": self.status.value,
            "connected": self.status == IntegrationStatus.CONNECTED,
            "camera_count": len(self.get_cameras()),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _init_test_scenarios(self):
        """Initialize test scenarios by scanning available test images."""
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        base_path = Path("public/dummy-surveillance")
        
        if not base_path.exists():
            logger.warning(f"Test images directory not found: {base_path}")
            return
            
        # Scan all subdirectories for images
        for scenario_dir in base_path.iterdir():
            if scenario_dir.is_dir():
                images = list(scenario_dir.glob("*.jpg")) + list(scenario_dir.glob("*.png"))
                for image in images:
                    relative_path = str(image.relative_to(Path("public")))
                    self._scenarios.append({
                        "scenario": scenario_dir.name,
                        "path": relative_path,
                        "full_path": str(image)
                    })
                    
        
    def _get_next_scenario(self):
        """Get the next test scenario in rotation."""
        if not self._scenarios:
            return None
            
        scenario = self._scenarios[self._scenario_index]
        self._scenario_index = (self._scenario_index + 1) % len(self._scenarios)
        
        
        self.current_scenario = scenario['scenario']
        self.current_image_path = scenario['path']
        return scenario
    
    @staticmethod
    def get_test_scenarios() -> List[str]:
        """Get available test scenarios."""
        scenarios_path = Path("public/dummy-surveillance")
        if not scenarios_path.exists():
            return []
        
        scenarios = []
        for item in scenarios_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                scenarios.append(item.name)
        
        return sorted(scenarios)
    
    def set_test_scenario(self, scenario: str) -> Dict[str, Any]:
        """Set the current test scenario and pick a random image."""
        scenarios_path = Path("public/dummy-surveillance")
        scenario_path = scenarios_path / scenario
        
        if not scenario_path.exists():
            return {"error": f"Scenario '{scenario}' not found"}
        
        # Find all image files in the scenario folder
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        images = [f for f in scenario_path.iterdir() 
                 if f.is_file() and f.suffix.lower() in image_extensions]
        
        if not images:
            return {"error": f"No images found in scenario '{scenario}'"}
        
        # Pick a random image
        selected_image = random.choice(images)
        self.current_scenario = scenario
        # Store relative path from public directory
        relative_path = selected_image.relative_to(Path("public"))
        self.current_image_path = str(relative_path)
        
        return {
            "success": True,
            "scenario": scenario,
            "image_path": f"public/{self.current_image_path}",
            "image_count": len(images)
        }
    


# Integration metadata
INTEGRATION_INFO = {
    "id": "dummy-surveillance",
    "name": "Dummy Surveillance",
    "description": "Test integration that simulates a surveillance system",
    "version": "1.0.0",
    "author": "Foe Be Gone",
    "configuration_schema": {},  # No configuration needed for dummy
    "supported_features": [
        "cameras",
        "snapshots",
        "motion_detection",
        "test_detections"
    ]
}