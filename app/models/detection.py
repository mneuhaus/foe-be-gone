"""Detection-related models."""
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FoeType(str, Enum):
    """Types of foes we can detect."""
    RODENT = "rodent"
    CROW = "crow"
    CROW_LIKE = "crow_like"  # Magpie, jackdaw, etc.
    CAT = "cat"
    UNKNOWN = "unknown"


class DetectionStatus(str, Enum):
    """Status of a detection."""
    PENDING = "pending"
    PROCESSED = "processed"
    DETERRED = "deterred"
    FAILED = "failed"


class Foe(SQLModel, table=True):
    """Detected foe/animal."""
    __tablename__ = "foes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    foe_type: FoeType = Field(description="Type of foe detected")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence (0-1)")
    bounding_box: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    detection_id: int = Field(foreign_key="detections.id")
    
    # Relationship
    detection: Optional["Detection"] = Relationship(back_populates="foes")


class Detection(SQLModel, table=True):
    """Detection event from a camera."""
    __tablename__ = "detections"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(foreign_key="devices.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    image_path: Optional[str] = Field(default=None, description="Path to saved snapshot")
    image_url: Optional[str] = Field(default=None, description="URL to snapshot if stored externally")
    status: DetectionStatus = Field(default=DetectionStatus.PENDING)
    ai_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    processed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    device: Optional["Device"] = Relationship(back_populates="detections")
    foes: List["Foe"] = Relationship(back_populates="detection", cascade_delete=True)
    deterrent_actions: List["DeterrentAction"] = Relationship(back_populates="detection", cascade_delete=True)


class DeterrentAction(SQLModel, table=True):
    """Actions taken to deter detected foes."""
    __tablename__ = "deterrent_actions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    detection_id: int = Field(foreign_key="detections.id")
    action_type: str = Field(description="Type of deterrent action (sound, light, etc.)")
    action_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=False)
    
    # Relationship
    detection: Optional["Detection"] = Relationship(back_populates="deterrent_actions")


# Update forward references
from app.models.device import Device
Detection.model_rebuild()
Foe.model_rebuild()
DeterrentAction.model_rebuild()