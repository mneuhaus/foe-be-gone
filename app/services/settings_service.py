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
    
    def initialize_defaults(self) -> None:
        """Initialize default settings if they don't exist."""
        defaults = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "detection_interval": "10",
            "confidence_threshold": "0.5",
            "max_image_size_mb": "10",
            "snapshot_retention_days": "7"
        }
        
        for key, default_value in defaults.items():
            existing = self.get_setting(key)
            if existing is None:
                self.set_setting(key, default_value)
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        settings = self.session.exec(select(Setting)).all()
        return {setting.key: setting.value for setting in settings}