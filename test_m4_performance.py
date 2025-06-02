#!/usr/bin/env python3
"""Quick M4 Mac performance test for Ollama models."""

import asyncio
import time
import httpx
import sys

async def quick_model_test(model_name: str):
    """Test model loading and simple prompt speed."""
    print(f"\n🔍 Testing {model_name}...")
    
    # Simple text prompt (no image) for quick test
    prompt = "What is 2+2? Answer briefly."
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 10  # Very short response
                    }
                }
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {model_name}: {duration:.1f}s")
                
                # Check performance metrics
                if 'load_duration' in result:
                    load_time = result['load_duration'] / 1e9
                    print(f"   Load time: {load_time:.2f}s")
                
                if 'eval_count' in result and 'eval_duration' in result:
                    tokens_per_sec = result['eval_count'] / (result['eval_duration'] / 1e9)
                    print(f"   Speed: {tokens_per_sec:.1f} tokens/sec")
                
                return duration
            else:
                print(f"❌ {model_name}: HTTP {response.status_code}")
                
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {model_name}: Failed ({e})")
    
    return None

async def main():
    print("🚀 M4 Mac Ollama Performance Test")
    print("=" * 40)
    
    # Test currently available models
    models_to_test = [
        "llava:13b"  # Your current model
    ]
    
    # Check what other models are available
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                available = [m['name'] for m in response.json().get('models', [])]
                print(f"Available models: {', '.join(available)}")
                models_to_test = available
    except:
        print("Could not list models")
    
    results = {}
    for model in models_to_test:
        duration = await quick_model_test(model)
        if duration:
            results[model] = duration
    
    if results:
        print(f"\n📊 Performance Summary:")
        for model, duration in sorted(results.items(), key=lambda x: x[1]):
            print(f"  {model}: {duration:.1f}s")
    
    print(f"\n💡 Recommendations for M4 Mac:")
    print(f"  1. Install smaller quantized models:")
    print(f"     ollama pull llava-phi3:3.8b-mini-q4_0")
    print(f"  2. Use 4-bit quantization for better speed")
    print(f"  3. Consider 7B models over 13B for real-time use")

if __name__ == "__main__":
    asyncio.run(main())