"""Provider models for cloud AI service configuration."""

from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime


class Provider(SQLModel, table=True):
    """Cloud AI provider configuration."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # e.g., "openai", "openrouter", "anthropic", "google"
    display_name: str  # e.g., "OpenAI", "OpenRouter", "Anthropic", "Google Gemini"
    provider_type: str  # LiteLLM provider type
    api_key: Optional[str] = Field(default=None)
    api_base: Optional[str] = Field(default=None)  # Custom API base URL
    enabled: bool = Field(default=False)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # Additional provider-specific config
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProviderModel(SQLModel, table=True):
    """Available models for each provider."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: int = Field(foreign_key="provider.id")
    model_id: str  # LiteLLM model identifier (e.g., "gpt-4-vision-preview")
    display_name: str  # Human readable name (e.g., "GPT-4 Vision")
    model_type: str = Field(default="vision")  # vision, text, etc.
    supports_vision: bool = Field(default=True)
    max_tokens: Optional[int] = Field(default=None)
    cost_per_1k_tokens: Optional[float] = Field(default=None)
    enabled: bool = Field(default=True)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # Model-specific config
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }