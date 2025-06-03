"""Models for test image management and ground truth labeling."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from app.models.detection import FoeType


class TestImage(SQLModel, table=True):
    """Test image for model evaluation with ground truth labels."""
    
    __tablename__ = "test_images"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Display name for the test image")
    description: Optional[str] = Field(default=None, description="Description of what's in the image")
    
    # Image data
    image_path: str = Field(description="Path to the full image")
    thumbnail_path: Optional[str] = Field(default=None, description="Path to thumbnail image")
    
    # Source information
    source_detection_id: Optional[int] = Field(default=None, foreign_key="detections.id")
    source_type: str = Field(default="detection", description="Source type: detection, upload, etc.")
    
    # Metadata
    image_width: int = Field(description="Original image width")
    image_height: int = Field(description="Original image height")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    ground_truth_labels: List["GroundTruthLabel"] = Relationship(back_populates="test_image")
    test_results: List["TestResult"] = Relationship(back_populates="test_image")


class GroundTruthLabel(SQLModel, table=True):
    """Ground truth label for a specific animal in a test image."""
    
    __tablename__ = "ground_truth_labels"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    test_image_id: int = Field(foreign_key="test_images.id")
    
    # Bounding box (x1, y1, x2, y2)
    bbox_x1: int = Field(description="Left coordinate")
    bbox_y1: int = Field(description="Top coordinate")
    bbox_x2: int = Field(description="Right coordinate")
    bbox_y2: int = Field(description="Bottom coordinate")
    
    # Label information
    foe_type: Optional[FoeType] = Field(default=None, description="Type of foe if applicable")
    species: str = Field(description="Specific species name")
    notes: Optional[str] = Field(default=None, description="Additional notes about this animal")
    
    # Confidence in the label (for cases where labeler is unsure)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Labeler confidence 0-1")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, description="Who created this label")
    
    # Relationships
    test_image: TestImage = Relationship(back_populates="ground_truth_labels")


class TestResult(SQLModel, table=True):
    """Result from testing a model on a test image."""
    
    __tablename__ = "test_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    test_image_id: int = Field(foreign_key="test_images.id")
    test_run_id: int = Field(foreign_key="test_runs.id")
    
    # Model information
    model_name: str = Field(description="Model name used for testing")
    provider_name: str = Field(description="Provider name (ollama, openai, etc.)")
    
    # Performance metrics
    inference_time_ms: float = Field(description="Inference time in milliseconds")
    total_time_ms: float = Field(description="Total time including warmup")
    cost: float = Field(default=0.0, description="Cost in USD for cloud models")
    
    # Detection results
    detections: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    raw_response: Optional[str] = Field(default=None, description="Raw API response")
    
    # Evaluation metrics (calculated after comparing with ground truth)
    true_positives: int = Field(default=0)
    false_positives: int = Field(default=0)
    false_negatives: int = Field(default=0)
    precision: Optional[float] = Field(default=None)
    recall: Optional[float] = Field(default=None)
    f1_score: Optional[float] = Field(default=None)
    
    # Error tracking
    error: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    test_image: TestImage = Relationship(back_populates="test_results")
    test_run: "TestRun" = Relationship(back_populates="results")


class TestRun(SQLModel, table=True):
    """A batch test run across multiple images and models."""
    
    __tablename__ = "test_runs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="Name of the test run")
    description: Optional[str] = Field(default=None)
    
    # Test configuration
    test_image_ids: List[int] = Field(default=[], sa_column=Column(JSON))
    model_names: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Aggregate metrics
    total_images: int = Field(default=0)
    total_models: int = Field(default=0)
    total_tests: int = Field(default=0)
    completed_tests: int = Field(default=0)
    failed_tests: int = Field(default=0)
    
    # Performance summary
    total_cost: float = Field(default=0.0)
    total_time_seconds: float = Field(default=0.0)
    
    # Status
    status: str = Field(default="pending", description="pending, running, completed, failed")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None)
    
    # Relationships
    results: List[TestResult] = Relationship(back_populates="test_run")