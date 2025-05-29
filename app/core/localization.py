"""Localization support for the application."""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
from fastapi import Request

class Translator:
    """Simple translator for the application."""
    
    def __init__(self, translations_dir: str = "app/translations"):
        self.translations_dir = Path(translations_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations()
        
    def _load_translations(self):
        """Load all translation files."""
        if not self.translations_dir.exists():
            self.translations_dir.mkdir(parents=True, exist_ok=True)
            
        for file_path in self.translations_dir.glob("*.json"):
            lang_code = file_path.stem
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading translation file {file_path}: {e}")
    
    def get_language(self, request: Request) -> str:
        """Get the current language from request or session."""
        # Check for language in query params
        lang = request.query_params.get('lang')
        if lang and lang in self.translations:
            return lang
            
        # Check for language in cookies
        lang = request.cookies.get('language')
        if lang and lang in self.translations:
            return lang
            
        # Check Accept-Language header
        accept_language = request.headers.get('accept-language', '')
        for lang_code in ['de', 'en']:  # Check German first, then English
            if lang_code in accept_language and lang_code in self.translations:
                return lang_code
                
        # Default to English
        return 'en'
    
    def translate(self, key: str, lang: str, **kwargs) -> str:
        """Translate a key to the specified language."""
        if lang not in self.translations:
            lang = 'en'  # Fallback to English
            
        # Navigate through nested keys (e.g., "common.save")
        keys = key.split('.')
        value = self.translations.get(lang, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                break
                
        if value is None:
            # Try English as fallback
            value = self.translations.get('en', {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    break
        
        if value is None:
            return key  # Return the key if translation not found
            
        # Format with provided kwargs
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except:
                return value
                
        return str(value)
    
    def get_all_translations(self, lang: str) -> Dict[str, Any]:
        """Get all translations for a language."""
        return self.translations.get(lang, self.translations.get('en', {}))


# Global translator instance
translator = Translator()


def t(key: str, request: Request, **kwargs) -> str:
    """Convenience function for translations in templates."""
    lang = translator.get_language(request)
    return translator.translate(key, lang, **kwargs)