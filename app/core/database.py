"""Database configuration and session management."""

from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from app.core.config import config

# Get database URL from config or use default
if config.DATABASE_URL:
    DATABASE_URL = config.DATABASE_URL
else:
    # Create database directory if it doesn't exist
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_dir}/foe_be_gone.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables() -> None:
    """Create all database tables."""
    # Import all models to register them with SQLModel
    from app.models.integration_instance import IntegrationInstance
    from app.models.device import Device
    from app.models.detection import Detection, Foe, DeterrentAction
    from app.models.setting import Setting
    from app.models.sound_effectiveness import (
        SoundEffectiveness, 
        SoundStatistics, 
        TimeBasedEffectiveness
    )
    
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session