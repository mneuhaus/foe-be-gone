"""Settings service for managing application configuration."""

import os
from typing import Optional, Dict, Any
from sqlmodel import Session, select

from app.models.setting import Setting
from app.core.config import config


class SettingsService:
    """Service for managing application settings stored in database."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value from the database."""
        setting = self.session.exec(select(Setting).where(Setting.key == key)).first()
        if setting:
            return setting.value
        return default
    
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value in the database."""
        setting = self.session.exec(select(Setting).where(Setting.key == key)).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        self.session.commit()
    
    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from settings or environment."""
        # First try database
        api_key = self.get_setting("openai_api_key")
        if api_key:
            return api_key
        # Fallback to environment variable
        return os.getenv("OPENAI_API_KEY")
    
    def get_log_level(self) -> str:
        """Get log level from settings or environment."""
        level = self.get_setting("log_level")
        if level:
            return level
        return os.getenv("LOG_LEVEL", "INFO")
    
    def get_detection_interval(self) -> int:
        """Get detection interval in seconds."""
        interval = self.get_setting("detection_interval", "10")
        try:
            value = int(interval)
            return max(config.MIN_DETECTION_INTERVAL, min(config.MAX_DETECTION_INTERVAL, value))
        except ValueError:
            return 10
    
    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold for detections."""
        threshold = self.get_setting("confidence_threshold", "0.5")
        try:
            value = float(threshold)
            return max(0.1, min(1.0, value))  # Clamp between 0.1-1.0
        except ValueError:
            return 0.5
    
    def get_max_image_size_mb(self) -> int:
        """Get maximum image size in MB."""
        size = self.get_setting("max_image_size_mb", "10")
        try:
            value = int(size)
            return max(1, min(50, value))  # Clamp between 1-50 MB
        except ValueError:
            return 10
    
    def get_snapshot_retention_days(self) -> int:
        """Get snapshot retention period in days."""
        days = self.get_setting("snapshot_retention_days", "7")
        try:
            value = int(days)
            return max(1, min(365, value))  # Clamp between 1-365 days
        except ValueError:
            return 7
    
    def get_yolo_enabled(self) -> bool:
        """Get whether YOLO detection is enabled."""
        enabled = self.get_setting("yolo_enabled", "true")
        return enabled.lower() in ["true", "1", "yes", "on"]
    
    def get_yolo_confidence_threshold(self) -> float:
        """Get YOLO confidence threshold."""
        threshold = self.get_setting("yolo_confidence_threshold", "0.25")
        try:
            value = float(threshold)
            return max(0.1, min(0.9, value))  # Clamp between 0.1-0.9
        except ValueError:
            return 0.25
    
    def get_timezone(self) -> str:
        """Get configured timezone."""
        # Default to UTC if not set
        return self.get_setting("timezone", "UTC")
    
    def get_species_identification_enabled(self) -> bool:
        """Get whether species identification is enabled."""
        enabled = self.get_setting("species_identification_enabled", "true")
        return enabled.lower() in ["true", "1", "yes", "on"]
    
    def get_species_model(self) -> str:
        """Get species identification model."""
        return self.get_setting("species_model", config.SPECIES_MODEL)
    
    def get_species_crop_padding(self) -> float:
        """Get species identification crop padding."""
        padding = self.get_setting("species_crop_padding", str(config.SPECIES_CROP_PADDING))
        try:
            value = float(padding)
            return max(0.0, min(1.0, value))  # Clamp between 0.0-1.0
        except ValueError:
            return config.SPECIES_CROP_PADDING
    
    def get_species_identification_provider(self) -> str:
        """Get species identification provider (qwen or ollama)."""
        return self.get_setting("species_identification_provider", config.SPECIES_IDENTIFICATION_PROVIDER)
    
    def get_deterrents_enabled(self) -> bool:
        """Get whether deterrents (sound playback) are enabled."""
        enabled = self.get_setting("deterrents_enabled", "true")
        return enabled.lower() in ["true", "1", "yes", "on"]
    
    def initialize_defaults(self) -> None:
        """Initialize default settings if they don't exist."""
        defaults = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "detection_interval": "10",
            "confidence_threshold": "0.5",
            "max_image_size_mb": "10",
            "snapshot_retention_days": "7",
            "yolo_enabled": os.getenv("YOLO_ENABLED", "true"),
            "yolo_confidence_threshold": os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.25"),
            "species_identification_enabled": os.getenv("SPECIES_IDENTIFICATION_ENABLED", "true"),
            "species_identification_provider": os.getenv("SPECIES_IDENTIFICATION_PROVIDER", config.SPECIES_IDENTIFICATION_PROVIDER),
            "species_model": os.getenv("SPECIES_MODEL", config.SPECIES_MODEL),
            "species_crop_padding": os.getenv("SPECIES_CROP_PADDING", str(config.SPECIES_CROP_PADDING)),
            "timezone": os.getenv("TZ", "UTC"),  # Default to UTC or TZ env var
            "deterrents_enabled": os.getenv("DETERRENTS_ENABLED", "true")  # Default to enabled
        }
        
        for key, default_value in defaults.items():
            existing = self.get_setting(key)
            if existing is None:
                self.set_setting(key, default_value)
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        settings = self.session.exec(select(Setting)).all()
        return {setting.key: setting.value for setting in settings}