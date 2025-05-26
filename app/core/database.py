"""Database configuration and session management."""

from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path

# Create database directory if it doesn't exist
db_dir = Path("data")
db_dir.mkdir(exist_ok=True)

# SQLite database URL
DATABASE_URL = f"sqlite:///{db_dir}/foe_be_gone.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """Create all database tables."""
    from app.models.integration_instance import IntegrationInstance  # Import models
    from app.models.device import Device
    
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session