#!/bin/bash

echo "🦙 Setting up Ollama for Foe Be Gone species detection..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first:"
    echo "   Visit: https://ollama.ai"
    echo "   Or run: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

echo "✅ Ollama is installed"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running. Starting Ollama..."
    ollama serve &
    sleep 5
fi

echo "✅ Ollama is running"

# Pull the vision model
MODEL="llava:13b"
echo "📥 Pulling $MODEL (this may take a while)..."
ollama pull $MODEL

# Verify model is available
if ollama list | grep -q "$MODEL"; then
    echo "✅ Model $MODEL is ready!"
else
    echo "❌ Failed to pull model $MODEL"
    exit 1
fi

echo ""
echo "🎉 Ollama setup complete!"
echo ""
echo "To use Ollama for species detection, set:"
echo "  export SPECIES_IDENTIFICATION_PROVIDER=ollama"
echo ""
echo "Available models for better accuracy:"
echo "  - llava:13b (default, good balance)"
echo "  - llava:34b (better accuracy, more resources)"
echo "  - bakllava (alternative vision model)"
echo ""
echo "To change the model:"
echo "  export OLLAMA_MODEL=llava:34b"