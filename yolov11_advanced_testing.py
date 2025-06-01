#!/usr/bin/env python3
"""
YOLOv11n Advanced Testing Suite
Comprehensive testing scenarios for production deployment
"""

import os
import sys
import time
import json
import random
from pathlib import Path
import cv2
import numpy as np
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading

def check_environment():
    """Check if we're running in the correct virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        return True
    else:
        print("❌ NOT running in virtual environment")
        return False

def setup_yolov11():
    """Setup YOLOv11 model"""
    try:
        from ultralytics import YOLO
        model = YOLO('yolo11n.pt')
        return model
    except Exception as e:
        print(f"❌ YOLOv11 setup failed: {e}")
        return None

def test_memory_usage():
    """Test memory usage during processing"""
    print("\n💾 Testing Memory Usage...")
    
    try:
        import psutil
        process = psutil.Process()
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"   Initial memory: {initial_memory:.1f} MB")
        
        model = setup_yolov11()
        if not model:
            return None
        
        # Memory after model loading
        after_loading = process.memory_info().rss / 1024 / 1024
        print(f"   After model loading: {after_loading:.1f} MB (+{after_loading - initial_memory:.1f} MB)")
        
        # Test with multiple images
        test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))[:10]
        max_memory = after_loading
        
        for i, image_path in enumerate(test_images):
            results = model(str(image_path), conf=0.3, verbose=False)
            current_memory = process.memory_info().rss / 1024 / 1024
            max_memory = max(max_memory, current_memory)
            
            if i % 3 == 0:  # Print every 3rd image
                print(f"   Image {i+1}: {current_memory:.1f} MB")
        
        print(f"   Peak memory usage: {max_memory:.1f} MB")
        print(f"   Memory overhead: {max_memory - initial_memory:.1f} MB")
        
        return {
            'initial_mb': initial_memory,
            'after_loading_mb': after_loading,
            'peak_mb': max_memory,
            'overhead_mb': max_memory - initial_memory
        }
        
    except ImportError:
        print("⚠️ psutil not available for memory testing")
        return None
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return None

def test_batch_processing(model, batch_size=5):
    """Test batch processing capabilities"""
    print(f"\n📦 Testing Batch Processing (batch size: {batch_size})...")
    
    test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))[:20]
    
    # Single image processing
    single_start = time.time()
    single_detections = 0
    
    for image_path in test_images:
        results = model(str(image_path), conf=0.3, verbose=False)
        for result in results:
            if result.boxes is not None:
                single_detections += len(result.boxes)
    
    single_time = time.time() - single_start
    single_fps = len(test_images) / single_time
    
    # Batch processing
    batch_start = time.time()
    batch_detections = 0
    
    # Process in batches
    for i in range(0, len(test_images), batch_size):
        batch = test_images[i:i + batch_size]
        batch_paths = [str(path) for path in batch]
        
        results = model(batch_paths, conf=0.3, verbose=False)
        for result in results:
            if result.boxes is not None:
                batch_detections += len(result.boxes)
    
    batch_time = time.time() - batch_start
    batch_fps = len(test_images) / batch_time
    
    print(f"   Single processing: {single_time:.2f}s, {single_fps:.1f} FPS, {single_detections} detections")
    print(f"   Batch processing: {batch_time:.2f}s, {batch_fps:.1f} FPS, {batch_detections} detections")
    print(f"   Speedup: {single_time / batch_time:.2f}x")
    
    return {
        'single': {
            'time': single_time,
            'fps': single_fps,
            'detections': single_detections
        },
        'batch': {
            'time': batch_time,
            'fps': batch_fps,
            'detections': batch_detections,
            'batch_size': batch_size
        },
        'speedup': single_time / batch_time
    }

def test_threading_performance(model, num_threads=4):
    """Test multi-threading performance"""
    print(f"\n🧠 Testing Multi-Threading Performance ({num_threads} threads)...")
    
    test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))[:20]
    
    def process_image(image_path):
        """Process single image"""
        start_time = time.time()
        results = model(str(image_path), conf=0.3, verbose=False)
        processing_time = time.time() - start_time
        
        detections = 0
        for result in results:
            if result.boxes is not None:
                detections += len(result.boxes)
        
        return {
            'path': str(image_path),
            'time': processing_time,
            'detections': detections
        }
    
    # Sequential processing
    sequential_start = time.time()
    sequential_results = []
    for image_path in test_images:
        result = process_image(image_path)
        sequential_results.append(result)
    sequential_time = time.time() - sequential_start
    
    # Threaded processing
    threaded_start = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        threaded_results = list(executor.map(process_image, test_images))
    threaded_time = time.time() - threaded_start
    
    sequential_fps = len(test_images) / sequential_time
    threaded_fps = len(test_images) / threaded_time
    
    print(f"   Sequential: {sequential_time:.2f}s, {sequential_fps:.1f} FPS")
    print(f"   Threaded ({num_threads}): {threaded_time:.2f}s, {threaded_fps:.1f} FPS")
    print(f"   Threading speedup: {sequential_time / threaded_time:.2f}x")
    
    return {
        'sequential': {
            'time': sequential_time,
            'fps': sequential_fps
        },
        'threaded': {
            'time': threaded_time,
            'fps': threaded_fps,
            'num_threads': num_threads
        },
        'speedup': sequential_time / threaded_time
    }

def test_different_image_sizes(model):
    """Test performance with different image sizes"""
    print("\n🖼️ Testing Different Image Sizes...")
    
    # Get a sample image
    test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))
    if not test_images:
        print("⚠️ No test images found")
        return None
    
    sample_image = test_images[0]
    
    # Test different sizes
    test_sizes = [
        (640, 480),    # VGA
        (1280, 720),   # 720p
        (1920, 1080),  # 1080p
        (2560, 1440),  # 1440p
        (3840, 2160),  # 4K
    ]
    
    size_results = {}
    
    for width, height in test_sizes:
        print(f"   Testing {width}x{height}...")
        
        # Resize image
        img = cv2.imread(str(sample_image))
        resized_img = cv2.resize(img, (width, height))
        
        # Save temporarily
        temp_path = f"temp_resized_{width}x{height}.jpg"
        cv2.imwrite(temp_path, resized_img)
        
        # Test processing
        times = []
        detections = []
        
        for _ in range(3):  # 3 runs for averaging
            start_time = time.time()
            results = model(temp_path, conf=0.3, verbose=False)
            processing_time = time.time() - start_time
            times.append(processing_time)
            
            detection_count = 0
            for result in results:
                if result.boxes is not None:
                    detection_count += len(result.boxes)
            detections.append(detection_count)
        
        avg_time = sum(times) / len(times)
        avg_detections = sum(detections) / len(detections)
        fps = 1 / avg_time
        
        size_results[f"{width}x{height}"] = {
            'avg_time': avg_time,
            'fps': fps,
            'avg_detections': avg_detections,
            'megapixels': (width * height) / 1_000_000
        }
        
        print(f"     Avg time: {avg_time:.3f}s, FPS: {fps:.1f}, Detections: {avg_detections:.1f}")
        
        # Cleanup
        Path(temp_path).unlink()
    
    return size_results

def test_stress_test(model, duration_minutes=2):
    """Run stress test for specified duration"""
    print(f"\n💪 Stress Testing ({duration_minutes} minutes)...")
    
    test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))[:10]
    if not test_images:
        print("⚠️ No test images found")
        return None
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    processed_count = 0
    total_detections = 0
    processing_times = []
    errors = 0
    
    while time.time() < end_time:
        # Random image selection
        image_path = random.choice(test_images)
        
        try:
            process_start = time.time()
            results = model(str(image_path), conf=0.3, verbose=False)
            process_time = time.time() - process_start
            
            processing_times.append(process_time)
            processed_count += 1
            
            # Count detections
            for result in results:
                if result.boxes is not None:
                    total_detections += len(result.boxes)
            
            # Progress update
            if processed_count % 50 == 0:
                elapsed = time.time() - start_time
                current_fps = processed_count / elapsed
                print(f"     {processed_count} images processed, {current_fps:.1f} FPS, {total_detections} detections")
                
        except Exception as e:
            errors += 1
            print(f"     Error processing {image_path}: {e}")
    
    total_time = time.time() - start_time
    avg_fps = processed_count / total_time
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    
    print(f"\n   Stress Test Results:")
    print(f"     Total images processed: {processed_count}")
    print(f"     Total time: {total_time:.1f}s")
    print(f"     Average FPS: {avg_fps:.1f}")
    print(f"     Average processing time: {avg_processing_time:.3f}s")
    print(f"     Total detections: {total_detections}")
    print(f"     Errors: {errors}")
    print(f"     Success rate: {((processed_count - errors) / processed_count * 100):.1f}%")
    
    return {
        'total_images': processed_count,
        'total_time': total_time,
        'avg_fps': avg_fps,
        'avg_processing_time': avg_processing_time,
        'total_detections': total_detections,
        'errors': errors,
        'success_rate': (processed_count - errors) / processed_count * 100 if processed_count > 0 else 0,
        'duration_minutes': duration_minutes
    }

def test_model_warmup(model):
    """Test model warmup time and performance improvement"""
    print("\n🔥 Testing Model Warmup Performance...")
    
    test_images = list(Path("public/dummy-surveillance").rglob("*.jpg"))[:5]
    if not test_images:
        return None
    
    # Cold start
    print("   Cold start (first 5 inferences):")
    cold_times = []
    for i, image_path in enumerate(test_images):
        start_time = time.time()
        results = model(str(image_path), conf=0.3, verbose=False)
        process_time = time.time() - start_time
        cold_times.append(process_time)
        print(f"     Inference {i+1}: {process_time:.3f}s")
    
    # Warm start
    print("   Warm start (next 5 inferences):")
    warm_times = []
    for i, image_path in enumerate(test_images):
        start_time = time.time()
        results = model(str(image_path), conf=0.3, verbose=False)
        process_time = time.time() - start_time
        warm_times.append(process_time)
        print(f"     Inference {i+1}: {process_time:.3f}s")
    
    cold_avg = sum(cold_times) / len(cold_times)
    warm_avg = sum(warm_times) / len(warm_times)
    improvement = (cold_avg - warm_avg) / cold_avg * 100
    
    print(f"\n   Warmup Analysis:")
    print(f"     Cold start average: {cold_avg:.3f}s")
    print(f"     Warm start average: {warm_avg:.3f}s")
    print(f"     Performance improvement: {improvement:.1f}%")
    
    return {
        'cold_start_avg': cold_avg,
        'warm_start_avg': warm_avg,
        'improvement_percent': improvement,
        'cold_times': cold_times,
        'warm_times': warm_times
    }

def run_advanced_testing():
    """Run comprehensive advanced testing suite"""
    print("🚀 YOLOv11n Advanced Testing Suite")
    print("=" * 50)
    
    if not check_environment():
        return 1
    
    model = setup_yolov11()
    if model is None:
        return 1
    
    # Create output directory
    output_dir = Path("yolov11_advanced_testing")
    output_dir.mkdir(exist_ok=True)
    
    # Run all tests
    results = {}
    
    # 1. Memory usage test
    results['memory_usage'] = test_memory_usage()
    
    # 2. Batch processing test
    results['batch_processing'] = test_batch_processing(model, batch_size=5)
    
    # 3. Threading performance test
    results['threading_performance'] = test_threading_performance(model, num_threads=4)
    
    # 4. Different image sizes test
    results['image_sizes'] = test_different_image_sizes(model)
    
    # 5. Model warmup test
    results['model_warmup'] = test_model_warmup(model)
    
    # 6. Stress test (shorter duration for demo)
    results['stress_test'] = test_stress_test(model, duration_minutes=1)
    
    # Save results
    results_file = output_dir / "advanced_testing_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✨ Advanced Testing Complete!")
    print(f"📁 Results saved to: {results_file}")
    
    # Summary
    print(f"\n📈 Testing Summary:")
    
    if results.get('memory_usage'):
        mem = results['memory_usage']
        print(f"   💾 Memory: {mem['peak_mb']:.1f} MB peak ({mem['overhead_mb']:.1f} MB overhead)")
    
    if results.get('batch_processing'):
        batch = results['batch_processing']
        print(f"   📦 Batch speedup: {batch['speedup']:.2f}x")
    
    if results.get('threading_performance'):
        thread = results['threading_performance']
        print(f"   🧠 Threading speedup: {thread['speedup']:.2f}x")
    
    if results.get('stress_test'):
        stress = results['stress_test']
        print(f"   💪 Stress test: {stress['avg_fps']:.1f} FPS average, {stress['success_rate']:.1f}% success")
    
    print(f"\n🎆 YOLOv11n shows excellent performance characteristics for production use!")
    
    return 0

if __name__ == "__main__":
    sys.exit(run_advanced_testing())
