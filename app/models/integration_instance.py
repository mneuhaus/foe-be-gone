"""SQLModel for integration instances."""

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
import uuid
import json

if TYPE_CHECKING:
    from .device import Device


class IntegrationInstance(SQLModel, table=True):
    """Represents an instance of an integration (e.g., a specific UniFi setup)."""
    
    __tablename__ = "integration_instances"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    integration_type: str = Field(index=True)  # e.g., "dummy-surveillance", "unifi-protect"
    name: str  # User-friendly name for this instance
    enabled: bool = Field(default=True)
    config_json: str = Field(default="{}")  # JSON string of configuration
    status: str = Field(default="disconnected")  # connected, disconnected, error
    status_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    devices: List["Device"] = Relationship(back_populates="integration")
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return json.loads(self.config_json) if self.config_json else {}
    
    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set configuration from dictionary."""
        self.config_json = json.dumps(value) if value else "{}"
    
    @property
    def config_dict(self) -> Dict[str, Any]:
        """Alias for config property for compatibility."""
        return self.config
        
    def update_status(self, status: str, message: Optional[str] = None):
        """Update integration status."""
        self.status = status
        self.status_message = message
        self.updated_at = datetime.utcnow()