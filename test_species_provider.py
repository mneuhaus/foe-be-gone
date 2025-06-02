#!/usr/bin/env python3
"""Test which species identification provider is being used."""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import config

print(f"Species Identification Enabled: {config.SPECIES_IDENTIFICATION_ENABLED}")
print(f"Species Identification Provider: {config.SPECIES_IDENTIFICATION_PROVIDER}")
print(f"Ollama Host: {config.OLLAMA_HOST}")
print(f"Ollama Model: {config.OLLAMA_MODEL}")
print()

if config.SPECIES_IDENTIFICATION_PROVIDER == "ollama":
    print("✅ Using Ollama for species identification (no model loading)")
    print("   Make sure Ollama is running with: ollama serve")
    print(f"   And the model is pulled: ollama pull {config.OLLAMA_MODEL}")
else:
    print("⚠️  Using Qwen for species identification (will load model on first use)")
    print(f"   Model: {config.SPECIES_MODEL}")