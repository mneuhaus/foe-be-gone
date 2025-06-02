"""Provider management routes for cloud AI services."""

import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.templates import templates
from app.models.provider import Provider, ProviderModel

router = APIRouter(prefix="/settings/providers", tags=["providers"])
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def providers_page(request: Request, db: Session = Depends(get_session)):
    """Display providers settings page."""
    # Get all providers
    providers = db.exec(select(Provider)).all()
    
    # Get default provider configurations
    default_providers = get_default_provider_configs()
    
    return templates.TemplateResponse(
        request,
        "settings/providers.html",
        {
            "providers": providers,
            "default_providers": default_providers
        }
    )


@router.post("/add")
async def add_provider(
    request: Request,
    provider_name: str = Form(...),
    api_key: str = Form(...),
    api_base: str = Form(""),
    enabled: bool = Form(False),
    db: Session = Depends(get_session)
):
    """Add a new provider."""
    try:
        # Check if provider already exists
        existing = db.exec(select(Provider).where(Provider.name == provider_name)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Provider already exists")
        
        # Get default config for this provider
        default_config = get_default_provider_configs().get(provider_name, {})
        
        # Create new provider
        provider = Provider(
            name=provider_name,
            display_name=default_config.get("display_name", provider_name.title()),
            provider_type=default_config.get("provider_type", provider_name),
            api_key=api_key if api_key else None,
            api_base=api_base if api_base else default_config.get("api_base"),
            enabled=enabled,
            config=default_config.get("config", {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        # Add default models for this provider
        await _add_default_models(provider, db)
        
        logger.info(f"Added provider: {provider_name}")
        return RedirectResponse(url="/settings/providers", status_code=303)
        
    except Exception as e:
        logger.error(f"Error adding provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider_id}/update")
async def update_provider(
    provider_id: int,
    api_key: str = Form(...),
    api_base: str = Form(""),
    enabled: bool = Form(False),
    db: Session = Depends(get_session)
):
    """Update provider settings."""
    try:
        provider = db.get(Provider, provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider.api_key = api_key if api_key else None
        provider.api_base = api_base if api_base else None
        provider.enabled = enabled
        provider.updated_at = datetime.utcnow()
        
        db.add(provider)
        db.commit()
        
        logger.info(f"Updated provider: {provider.name}")
        return RedirectResponse(url="/settings/providers", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider_id}/delete")
async def delete_provider(
    provider_id: int,
    db: Session = Depends(get_session)
):
    """Delete a provider and its models."""
    try:
        provider = db.get(Provider, provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Delete associated models first
        models = db.exec(select(ProviderModel).where(ProviderModel.provider_id == provider_id)).all()
        for model in models:
            db.delete(model)
        
        # Delete provider
        db.delete(provider)
        db.commit()
        
        logger.info(f"Deleted provider: {provider.name}")
        return RedirectResponse(url="/settings/providers", status_code=303)
        
    except Exception as e:
        logger.error(f"Error deleting provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{provider_id}/models")
async def get_provider_models(
    provider_id: int,
    db: Session = Depends(get_session)
):
    """Get models for a specific provider."""
    models = db.exec(
        select(ProviderModel).where(ProviderModel.provider_id == provider_id)
    ).all()
    
    return {
        "models": [
            {
                "id": model.id,
                "model_id": model.model_id,
                "display_name": model.display_name,
                "supports_vision": model.supports_vision,
                "enabled": model.enabled,
                "cost_per_1k_tokens": model.cost_per_1k_tokens
            }
            for model in models
        ]
    }


@router.post("/{provider_id}/refresh-models")
async def refresh_provider_models(
    provider_id: int,
    db: Session = Depends(get_session)
):
    """Refresh available models for a provider."""
    try:
        provider = db.get(Provider, provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Clear existing models
        existing_models = db.exec(
            select(ProviderModel).where(ProviderModel.provider_id == provider_id)
        ).all()
        for model in existing_models:
            db.delete(model)
        
        # Add fresh models
        await _add_default_models(provider, db)
        
        logger.info(f"Refreshed models for provider: {provider.name}")
        return {"message": "Models refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_default_provider_configs() -> Dict[str, Dict[str, Any]]:
    """Get default configurations for supported providers."""
    return {
        "openai": {
            "display_name": "OpenAI",
            "provider_type": "openai",
            "api_base": "https://api.openai.com/v1",
            "config": {
                "max_tokens": 4096,
                "temperature": 0.1
            }
        },
        "openrouter": {
            "display_name": "OpenRouter",
            "provider_type": "openrouter",
            "api_base": "https://openrouter.ai/api/v1",
            "config": {
                "max_tokens": 4096,
                "temperature": 0.1
            }
        },
        "anthropic": {
            "display_name": "Anthropic",
            "provider_type": "anthropic",
            "api_base": "https://api.anthropic.com",
            "config": {
                "max_tokens": 4096,
                "temperature": 0.1
            }
        },
        "google": {
            "display_name": "Google Gemini",
            "provider_type": "gemini",
            "api_base": "https://generativelanguage.googleapis.com/v1",
            "config": {
                "max_tokens": 4096,
                "temperature": 0.1
            }
        }
    }


async def _add_default_models(provider: Provider, db: Session):
    """Add default models for a provider."""
    models_by_provider = {
        "openai": [
            {
                "model_id": "gpt-4o",
                "display_name": "GPT-4o (Vision)",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.005
            },
            {
                "model_id": "gpt-4o-mini",
                "display_name": "GPT-4o Mini (Vision)",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00015
            },
            {
                "model_id": "gpt-4.1",
                "display_name": "GPT-4.1 (Vision)",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.01  # Estimated
            },
            {
                "model_id": "gpt-4.1-mini",
                "display_name": "GPT-4.1 Mini (Vision)",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.0003  # Estimated
            },
            {
                "model_id": "gpt-4.1-nano",
                "display_name": "GPT-4.1 Nano (Vision)",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00015  # Estimated
            }
        ],
        "openrouter": [
            {
                "model_id": "anthropic/claude-3.5-sonnet",
                "display_name": "Claude 3.5 Sonnet via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.003
            },
            {
                "model_id": "google/gemini-pro-vision",
                "display_name": "Gemini Pro Vision via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00025
            },
            {
                "model_id": "mistralai/mistral-medium-3",
                "display_name": "Mistral Medium 3 via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.001  # Estimated
            },
            {
                "model_id": "arcee-ai/spotlight",
                "display_name": "Arcee Spotlight via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.0005  # Estimated
            },
            {
                "model_id": "opengvlab/internvl3-14b:free",
                "display_name": "InternVL3 14B (Free) via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.0  # Free
            },
            {
                "model_id": "opengvlab/internvl3-2b:free",
                "display_name": "InternVL3 2B (Free) via OpenRouter",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.0  # Free
            }
        ],
        "anthropic": [
            {
                "model_id": "claude-3-opus-20240229",
                "display_name": "Claude 3 Opus",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.015
            },
            {
                "model_id": "claude-3-5-sonnet-20241022",
                "display_name": "Claude 3.5 Sonnet",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.003
            },
            {
                "model_id": "claude-3-haiku-20240307",
                "display_name": "Claude 3 Haiku",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00025
            }
        ],
        "google": [
            {
                "model_id": "gemini-2.5-pro-preview-05-06",
                "display_name": "Gemini 2.5 Pro Preview",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00125  # Estimated similar to 1.5 Pro
            },
            {
                "model_id": "gemini-2.5-flash-preview-05-20",
                "display_name": "Gemini 2.5 Flash Preview",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.000075  # Estimated similar to 1.5 Flash
            },
            {
                "model_id": "gemini-2.0-flash",
                "display_name": "Gemini 2.0 Flash",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.000075
            },
            {
                "model_id": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.00125
            },
            {
                "model_id": "gemini-1.5-flash",
                "display_name": "Gemini 1.5 Flash",
                "supports_vision": True,
                "cost_per_1k_tokens": 0.000075
            }
        ]
    }
    
    default_models = models_by_provider.get(provider.name, [])
    
    for model_config in default_models:
        model = ProviderModel(
            provider_id=provider.id,
            model_id=model_config["model_id"],
            display_name=model_config["display_name"],
            model_type="vision",
            supports_vision=model_config["supports_vision"],
            cost_per_1k_tokens=model_config["cost_per_1k_tokens"],
            enabled=True,
            config={}
        )
        db.add(model)
    
    db.commit()