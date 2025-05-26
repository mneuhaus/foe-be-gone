"""Base classes for integrations."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class DeviceInterface(ABC):
    """Abstract base class for all devices."""
    
    def __init__(self, device_id: str, name: str, device_type: str):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.last_seen = datetime.utcnow()
    
    @abstractmethod
    def get_snapshot(self) -> Optional[bytes]:
        """Get a snapshot from the device (image data as bytes)."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the device."""
        pass
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.utcnow()


class IntegrationBase(ABC):
    """Abstract base class for all integrations."""
    
    @abstractmethod
    def get_devices(self) -> List[DeviceInterface]:
        """Get all devices from this integration."""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the integration."""
        pass