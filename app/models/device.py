"""SQLModel for devices (cameras, sensors, etc.)."""

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
import uuid
import json

if TYPE_CHECKING:
    from app.models.detection import Detection


class Device(SQLModel, table=True):
    """Represents a device (camera, sensor, etc.) provided by an integration."""
    
    __tablename__ = "devices"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    integration_id: str = Field(foreign_key="integration_instances.id", index=True)
    device_type: str = Field(index=True)  # camera, sensor, etc.
    name: str
    model: Optional[str] = None
    status: str = Field(default="offline")  # online, offline, error
    
    # Device-specific data
    device_metadata_json: str = Field(default="{}")  # JSON string of device metadata
    capabilities_json: str = Field(default="{}")  # JSON string of capabilities
    
    # Current state
    current_image_url: Optional[str] = None  # For cameras
    last_detection: Optional[datetime] = None
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    integration: Optional["IntegrationInstance"] = Relationship(back_populates="devices")
    detections: List["Detection"] = Relationship(back_populates="device")
    
    @property
    def device_metadata(self) -> Dict[str, Any]:
        """Get device metadata as dictionary."""
        return json.loads(self.device_metadata_json)
    
    @device_metadata.setter
    def device_metadata(self, value: Dict[str, Any]):
        """Set device metadata from dictionary."""
        self.device_metadata_json = json.dumps(value)
        
    @property
    def capabilities(self) -> Dict[str, Any]:
        """Get capabilities as dictionary."""
        return json.loads(self.capabilities_json)
    
    @capabilities.setter
    def capabilities(self, value: Dict[str, Any]):
        """Set capabilities from dictionary."""
        self.capabilities_json = json.dumps(value)
        
    def update_status(self, status: str):
        """Update device status."""
        self.status = status
        self.last_seen = datetime.utcnow()
        self.updated_at = datetime.utcnow()