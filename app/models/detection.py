"""Detection-related models."""
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import Float
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.sound_effectiveness import SoundEffectiveness


class FoeType(str, Enum):
    """Types of foes we can detect (matches sound directory names)."""
    RATS = "RATS"      # All rodents (rats, mice)
    CROWS = "CROWS"    # All corvids (crows, ravens, magpies, jackdaws)
    CATS = "CATS"      # Domestic cats
    HERONS = "HERONS"  # Herons and similar wading birds
    PIGEONS = "PIGEONS" # Pigeons and doves
    UNKNOWN = "UNKNOWN"


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
    foe_type: str = Field(description="Type of foe detected")  # Changed from FoeType to str
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence (0-1)")
    bounding_box: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    detection_id: int = Field(foreign_key="detections.id")
    
    # Relationship
    detection: Optional["Detection"] = Relationship(back_populates="foes")
    
    @property
    def foe_type_enum(self) -> FoeType:
        """Get foe_type as enum, with fallback to UNKNOWN."""
        try:
            return FoeType(self.foe_type.upper())
        except (ValueError, AttributeError):
            return FoeType.UNKNOWN
    
    def __repr__(self) -> str:
        return f"Foe(id={self.id}, foe_type={self.foe_type}, confidence={self.confidence:.2f})"


class Detection(SQLModel, table=True):
    """Detection event from a camera."""
    __tablename__ = "detections"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(foreign_key="devices.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    image_path: Optional[str] = Field(default=None, description="Path to saved snapshot")
    image_url: Optional[str] = Field(default=None, description="URL to snapshot if stored externally")
    video_path: Optional[str] = Field(default=None, description="Path to captured video")
    status: DetectionStatus = Field(default=DetectionStatus.PENDING)
    ai_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    processed_at: Optional[datetime] = Field(default=None)
    # Estimated cost of the AI detection call in USD
    ai_cost: Optional[float] = Field(default=None, description="Estimated AI call cost in USD", sa_column=Column(Float, nullable=True))
    # List of deterrent sound filenames played for this detection
    played_sounds: Optional[List[str]] = Field(default=None, description="List of deterrent sounds played", sa_column=Column(JSON, nullable=True))
    
    # Friend tracking fields
    is_friend: Optional[bool] = Field(default=None, description="Whether this detection is a friendly creature")
    friend_type: Optional[str] = Field(default=None, description="Type of friendly creature (squirrel, small_bird, etc)")
    friend_confidence: Optional[float] = Field(default=None, description="Confidence that this is a friend (0-1)")
    
    # Additional fields for statistics
    detected_foe: Optional[str] = Field(default=None, description="Type of foe detected (for quick queries)")
    deterrent_effective: Optional[bool] = Field(default=None, description="Whether the deterrent was effective")
    ai_analysis: Optional[str] = Field(default=None, description="AI analysis text")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the detection was created")
    
    # Visual similarity grouping
    visual_hash: Optional[str] = Field(default=None, description="Perceptual hash for visual similarity grouping")
    
    # Relationships
    device: Optional["Device"] = Relationship(back_populates="detections")
    foes: List["Foe"] = Relationship(back_populates="detection", cascade_delete=True)
    deterrent_actions: List["DeterrentAction"] = Relationship(back_populates="detection", cascade_delete=True)
    effectiveness_tests: List["SoundEffectiveness"] = Relationship(back_populates="detection", cascade_delete=True)
    
    def __repr__(self) -> str:
        return f"Detection(id={self.id}, device_id={self.device_id}, timestamp={self.timestamp}, status={self.status})"


class DeterrentAction(SQLModel, table=True):
    """Actions taken to deter detected foes."""
    __tablename__ = "deterrent_actions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    detection_id: int = Field(foreign_key="detections.id")
    action_type: str = Field(description="Type of deterrent action (sound, light, etc.)")
    action_details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = Field(default=False)
    
    # Relationship
    detection: Optional["Detection"] = Relationship(back_populates="deterrent_actions")
    
    def __repr__(self) -> str:
        return f"DeterrentAction(id={self.id}, detection_id={self.detection_id}, action_type={self.action_type}, success={self.success})"


