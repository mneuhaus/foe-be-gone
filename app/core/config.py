"""Application configuration and environment variable validation."""

import os
import sys
from typing import Optional
from pathlib import Path


class Config:
    """Application configuration with environment variable validation."""
    
    # OpenAI API key is managed through frontend settings, not environment variables
    # OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
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
    
    # YOLO detection settings
    YOLO_CONFIDENCE_THRESHOLD: float = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.25"))
    YOLO_ENABLED: bool = os.getenv("YOLO_ENABLED", "true").lower() == "true"
    
    # Species identification settings
    SPECIES_IDENTIFICATION_ENABLED: bool = os.getenv("SPECIES_IDENTIFICATION_ENABLED", "true").lower() == "true"
    SPECIES_IDENTIFICATION_PROVIDER: str = os.getenv("SPECIES_IDENTIFICATION_PROVIDER", "ollama")  # "qwen" or "ollama"
    
    # Qwen settings (when using provider="qwen")
    SPECIES_MODEL: str = os.getenv("SPECIES_MODEL", "qwen/qwen2-vl-3b-instruct")  # LiteLLM format
    SPECIES_CROP_PADDING: float = float(os.getenv("SPECIES_CROP_PADDING", "0.5"))  # 50% padding around bbox
    SPECIES_MIN_CROP_SIZE: int = int(os.getenv("SPECIES_MIN_CROP_SIZE", "224"))  # Minimum crop size in pixels
    
    # Ollama settings (when using provider="ollama")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llava:13b")  # Vision model for Ollama
    
    # Sound player settings
    SOUNDS_DIR: Path = Path("public/sounds")
    SUPPORTED_AUDIO_FORMATS: list[str] = [".mp3", ".wav"]
    
    # Snapshot settings
    SNAPSHOTS_DIR: Path = Path("data/snapshots")
    SNAPSHOT_RETENTION_DAYS: int = 7
    
    # YOLO model settings
    MODELS_DIR: Path = Path("data/models")
    YOLO_MODEL_NAME: str = "yolo11n.pt"
    
    # AI Model configuration  
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o")  # LiteLLM model name
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.1"))
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "2000"))
    
    # Network settings
    RTSP_PORT: int = int(os.getenv("RTSP_PORT", "7447"))  # UniFi Protect RTSP port
    
    # Rate limiting settings
    UNIFI_RATE_LIMIT_CALLS_PER_SECOND: float = float(os.getenv("UNIFI_RATE_LIMIT_CPS", "0.5"))  # 2 seconds between calls
    UNIFI_RATE_LIMIT_BURST: int = int(os.getenv("UNIFI_RATE_LIMIT_BURST", "2"))  # Allow 2 immediate calls
    
    # Video capture settings
    VIDEO_CAPTURE_DURATION: int = int(os.getenv("VIDEO_CAPTURE_DURATION", "15"))  # seconds
    
    # Statistics timeframes
    STATS_DEFAULT_DAYS: int = int(os.getenv("STATS_DEFAULT_DAYS", "30"))
    STATS_RECENT_ACTIVITY_MINUTES: int = int(os.getenv("STATS_RECENT_ACTIVITY_MINUTES", "15"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables at startup.
        
        Raises:
            SystemExit: If required environment variables are missing
        """
        errors = []
        
        # OpenAI API key is now optional - can be set from frontend
        # if not cls.OPENAI_API_KEY:
        #     errors.append("OPENAI_API_KEY environment variable is required for AI detection")
        
        # Check if sounds directory exists
        if not cls.SOUNDS_DIR.exists():
            errors.append(f"Sounds directory not found: {cls.SOUNDS_DIR}")
        
        # Create data directories if they don't exist
        cls.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # If there are errors, print them and exit
        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            print("\nPlease set the required environment variables and try again.", file=sys.stderr)
            sys.exit(1)
        
        # Log successful validation
        print(f"Configuration validated successfully")
        print(f"  - Database URL: {cls.DATABASE_URL or 'Using default SQLite'}")
        print(f"  - Log level: {cls.LOG_LEVEL}")


# Create global config instance
config = Config()