"""Application configuration and environment variable validation."""

import os
import sys
from typing import Optional
from pathlib import Path


class Config:
    """Application configuration with environment variable validation."""
    
    # Required environment variables for AI integration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Optional environment variables with defaults
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Application constants
    MIN_DETECTION_INTERVAL: int = 1
    MAX_DETECTION_INTERVAL: int = 30
    DEFAULT_DETECTION_INTERVAL: int = 10
    
    # File size limits
    MAX_IMAGE_SIZE_MB: int = 10
    
    # Detection thresholds
    MIN_CONFIDENCE_THRESHOLD: float = 0.5
    
    # Sound player settings
    SOUNDS_DIR: Path = Path("public/sounds")
    SUPPORTED_AUDIO_FORMATS: list[str] = [".mp3", ".wav"]
    
    # Snapshot settings
    SNAPSHOTS_DIR: Path = Path("data/snapshots")
    SNAPSHOT_RETENTION_DAYS: int = 7
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables at startup.
        
        Raises:
            SystemExit: If required environment variables are missing
        """
        errors = []
        
        # Check required variables
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY environment variable is required for AI detection")
        
        # Check if sounds directory exists
        if not cls.SOUNDS_DIR.exists():
            errors.append(f"Sounds directory not found: {cls.SOUNDS_DIR}")
        
        # Create snapshots directory if it doesn't exist
        cls.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # If there are errors, print them and exit
        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            print("\nPlease set the required environment variables and try again.", file=sys.stderr)
            sys.exit(1)
        
        # Log successful validation
        print(f"Configuration validated successfully")
        print(f"  - OpenAI API key: {'*' * 8}{cls.OPENAI_API_KEY[-4:]}")
        print(f"  - Database URL: {cls.DATABASE_URL or 'Using default SQLite'}")
        print(f"  - Log level: {cls.LOG_LEVEL}")


# Create global config instance
config = Config()