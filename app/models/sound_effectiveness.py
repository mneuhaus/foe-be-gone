"""Models for tracking deterrent sound effectiveness."""

from sqlmodel import Field, SQLModel, Relationship, Column
from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlalchemy import Float, Integer, ForeignKey


class DeterrentResult(str, Enum):
    """Result of deterrent action."""
    SUCCESS = "success"         # Foe was successfully deterred (left the scene)
    PARTIAL = "partial"        # Foe count reduced but not eliminated
    FAILURE = "failure"        # Foe remained or increased
    UNKNOWN = "unknown"        # Could not determine (e.g., camera error)


class SoundEffectiveness(SQLModel, table=True):
    """Track effectiveness of specific sounds against specific foes."""
    __tablename__ = "sound_effectiveness"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    detection_id: int = Field(foreign_key="detections.id", description="Related detection event")
    foe_type: str = Field(description="Type of foe (rats, crows, cats)")
    sound_file: str = Field(description="Name of the sound file played")
    playback_method: str = Field(description="How sound was played (camera, local)")
    
    # Before and after detection data
    foes_before: int = Field(description="Number of foes detected before deterrent")
    foes_after: int = Field(description="Number of foes detected after deterrent")
    confidence_before: float = Field(description="Average confidence before deterrent")
    confidence_after: float = Field(description="Average confidence after deterrent")
    
    # Timing information
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    wait_duration: int = Field(default=10, description="Seconds waited before re-check")
    
    # Result
    result: DeterrentResult = Field(description="Effectiveness result")
    effectiveness_score: float = Field(
        default=0.0,
        description="Calculated effectiveness score (0-1)",
        ge=0.0, 
        le=1.0
    )
    
    # Optional follow-up data
    follow_up_image_path: Optional[str] = Field(default=None, description="Path to follow-up snapshot")
    notes: Optional[str] = Field(default=None, description="Additional observations")
    
    # Relationships
    detection: Optional["Detection"] = Relationship(back_populates="effectiveness_tests")
    
    def calculate_effectiveness_score(self) -> float:
        """Calculate effectiveness score based on before/after comparison."""
        if self.foes_before == 0:
            return 0.0
            
        if self.foes_after == 0:
            # Complete success
            return 1.0
        elif self.foes_after < self.foes_before:
            # Partial success - reduced foe count
            reduction_ratio = (self.foes_before - self.foes_after) / self.foes_before
            # Also factor in confidence changes
            confidence_factor = 1.0
            if self.confidence_before > 0:
                confidence_factor = 1 - (self.confidence_after / self.confidence_before)
            return min(1.0, (reduction_ratio + confidence_factor) / 2)
        else:
            # Failure - same or more foes
            return 0.0


class SoundStatistics(SQLModel, table=True):
    """Aggregated statistics for sound effectiveness."""
    __tablename__ = "sound_statistics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    foe_type: str = Field(description="Type of foe")
    sound_file: str = Field(description="Sound file name")
    
    # Statistics
    total_uses: int = Field(default=0, description="Total times this sound was used")
    successful_uses: int = Field(default=0, description="Times it successfully deterred foes")
    partial_uses: int = Field(default=0, description="Times it partially deterred foes")
    failed_uses: int = Field(default=0, description="Times it failed to deter foes")
    
    # Effectiveness metrics
    success_rate: float = Field(default=0.0, description="Success rate (0-1)")
    average_effectiveness: float = Field(default=0.0, description="Average effectiveness score")
    
    # Timestamps
    first_used: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Create unique constraint on foe_type + sound_file
    class Config:
        """SQLModel config."""
        table = True
        
    def update_statistics(self, effectiveness: SoundEffectiveness):
        """Update statistics with a new effectiveness record."""
        self.total_uses += 1
        self.last_used = effectiveness.timestamp
        self.last_updated = datetime.utcnow()
        
        # Update success counts
        if effectiveness.result == DeterrentResult.SUCCESS:
            self.successful_uses += 1
        elif effectiveness.result == DeterrentResult.PARTIAL:
            self.partial_uses += 1
        elif effectiveness.result == DeterrentResult.FAILURE:
            self.failed_uses += 1
            
        # Recalculate rates
        if self.total_uses > 0:
            self.success_rate = self.successful_uses / self.total_uses
            # Average effectiveness would need to be calculated from all records
            
            
class TimeBasedEffectiveness(SQLModel, table=True):
    """Track effectiveness patterns by time of day."""
    __tablename__ = "time_based_effectiveness"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    foe_type: str = Field(description="Type of foe")
    hour_of_day: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    
    # Statistics for this hour
    total_detections: int = Field(default=0)
    successful_deterrents: int = Field(default=0)
    average_effectiveness: float = Field(default=0.0)
    
    # Most effective sound for this time
    best_sound: Optional[str] = Field(default=None)
    best_sound_success_rate: float = Field(default=0.0)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)