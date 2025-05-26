"""Database configuration and session management."""

from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path
import os

# Get database URL from environment or use default
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # Create database directory if it doesn't exist
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_dir}/foe_be_gone.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """Create all database tables."""
    from app.models.integration_instance import IntegrationInstance  # Import models
    from app.models.device import Device
    from app.models.detection import Detection, Foe, DeterrentAction
    from app.models.setting import Setting
    
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session