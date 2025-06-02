#!/usr/bin/env python3
"""Test Ollama performance with different models."""

import asyncio
import time
import httpx
from PIL import Image
import base64
import io

async def test_ollama_model(model_name: str, image_path: str = "public/dummy-surveillance/cat/Terrassentür  - 5-25-2025, 05.10.55 GMT+2.jpg"):
    """Test a specific Ollama model's performance."""
    print(f"\n🔍 Testing model: {model_name}")
    
    # Load and prepare image
    image = Image.open(image_path)
    # Resize to standard size for consistent testing
    image = image.resize((512, 512))
    
    # Convert to base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Prepare request
    prompt = """Identify the animal species in this image. 
    Respond with: species name, common name, and confidence (0-1).
    Be concise."""
    
    # Time the request
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "images": [img_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 100  # Limit response length
                    }
                }
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success in {duration:.1f}s")
                print(f"Response: {result.get('response', '')[:200]}...")
                
                # Check if model info includes GPU usage
                if 'model_info' in result:
                    print(f"Model info: {result['model_info']}")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Failed after {duration:.1f}s: {e}")
    
    return duration

async def main():
    """Test different Ollama models."""
    print("🚀 Ollama Performance Test on M4 Mac")
    print("=" * 50)
    
    # Check available models
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"\n📦 Available models:")
                for model in models:
                    size_gb = model.get('size', 0) / (1024**3)
                    print(f"  - {model['name']} ({size_gb:.1f}GB)")
        except:
            print("⚠️  Could not list models. Is Ollama running?")
            return
    
    # Models to test (from fastest to most accurate)
    test_models = [
        "llava-phi3:3.8b-mini-q4_0",     # Smallest, fastest
        "bakllava:7b-v1-q4_0",           # Fast alternative
        "llava:7b-v1.6-mistral-q4_0",   # Good balance
        "llava:13b",                      # Current default (slowest)
    ]
    
    print(f"\n🧪 Testing models for species identification...")
    
    results = {}
    for model in test_models:
        # Skip if model not available
        if not any(m['name'].startswith(model.split(':')[0]) for m in models):
            print(f"\n⏭️  Skipping {model} (not installed)")
            continue
            
        duration = await test_ollama_model(model)
        results[model] = duration
    
    # Summary
    print(f"\n📊 Performance Summary:")
    print("-" * 50)
    for model, duration in sorted(results.items(), key=lambda x: x[1]):
        print(f"{model:<30} {duration:>6.1f}s")
    
    # Recommendation
    if results:
        fastest = min(results.items(), key=lambda x: x[1])
        print(f"\n✨ Recommendation: Use {fastest[0]} for {fastest[1]:.1f}s processing time")
        print(f"   Current model (llava:13b) takes {results.get('llava:13b', 'N/A')}s")

if __name__ == "__main__":
    asyncio.run(main())