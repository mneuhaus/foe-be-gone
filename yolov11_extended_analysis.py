#!/usr/bin/env python3
"""
YOLOv11n Extended Analysis & Performance Testing
Advanced evaluation suite for animal detection capabilities
"""

import os
import sys
import time
import json
import statistics
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter

def check_environment():
    """Check if we're running in the correct virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        print(f"Python executable: {sys.executable}")
        return True
    else:
        print("❌ NOT running in virtual environment")
        print("Please activate the virtual environment:")
        print("source megadetector_env/bin/activate")
        return False

def setup_yolov11():
    """Setup YOLOv11 model"""
    print("\n📥 Setting up YOLOv11...")
    
    try:
        from ultralytics import YOLO
        model = YOLO('yolo11n.pt')
        print(f"✅ YOLOv11n loaded successfully")
        return model
    except Exception as e:
        print(f"❌ YOLOv11 setup failed: {e}")
        return None

def analyze_confidence_distribution(results_file):
    """Analyze confidence score distribution across detections"""
    print("\n📊 Analyzing Confidence Score Distribution...")
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    confidences = []
    confidences_by_class = defaultdict(list)
    
    for result in results:
        for detection in result.get('detections', []):
            conf = detection['confidence']
            class_name = detection['class_name']
            confidences.append(conf)
            confidences_by_class[class_name].append(conf)
    
    if not confidences:
        print("⚠️ No detections found for confidence analysis")
        return
    
    # Overall statistics
    print(f"📈 Overall Confidence Statistics:")
    print(f"   Mean: {statistics.mean(confidences):.3f}")
    print(f"   Median: {statistics.median(confidences):.3f}")
    print(f"   Min: {min(confidences):.3f}")
    print(f"   Max: {max(confidences):.3f}")
    print(f"   Std Dev: {statistics.stdev(confidences):.3f}")
    
    # Per-class statistics
    print(f"\n📊 Per-Class Confidence Statistics:")
    for class_name, class_confidences in confidences_by_class.items():
        print(f"   {class_name}:")
        print(f"     Count: {len(class_confidences)}")
        print(f"     Mean: {statistics.mean(class_confidences):.3f}")
        print(f"     Min: {min(class_confidences):.3f}")
        print(f"     Max: {max(class_confidences):.3f}")
    
    return {
        'overall': {
            'mean': statistics.mean(confidences),
            'median': statistics.median(confidences),
            'min': min(confidences),
            'max': max(confidences),
            'std': statistics.stdev(confidences),
            'count': len(confidences)
        },
        'by_class': {cls: {
            'mean': statistics.mean(confs),
            'median': statistics.median(confs),
            'min': min(confs),
            'max': max(confs),
            'std': statistics.stdev(confs) if len(confs) > 1 else 0,
            'count': len(confs)
        } for cls, confs in confidences_by_class.items()}
    }

def analyze_bbox_sizes(results_file):
    """Analyze bounding box size distribution"""
    print("\n📏 Analyzing Bounding Box Sizes...")
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    bbox_areas = []
    bbox_areas_by_class = defaultdict(list)
    bbox_ratios = []  # width/height ratios
    bbox_ratios_by_class = defaultdict(list)
    
    for result in results:
        for detection in result.get('detections', []):
            bbox = detection['bbox']  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox
            
            width = x2 - x1
            height = y2 - y1
            area = width * height
            ratio = width / height if height > 0 else 0
            
            class_name = detection['class_name']
            
            bbox_areas.append(area)
            bbox_areas_by_class[class_name].append(area)
            bbox_ratios.append(ratio)
            bbox_ratios_by_class[class_name].append(ratio)
    
    if not bbox_areas:
        print("⚠️ No bounding boxes found for size analysis")
        return
    
    print(f"📦 Bounding Box Area Statistics:")
    print(f"   Mean Area: {statistics.mean(bbox_areas):.0f} pixels²")
    print(f"   Median Area: {statistics.median(bbox_areas):.0f} pixels²")
    print(f"   Min Area: {min(bbox_areas):.0f} pixels²")
    print(f"   Max Area: {max(bbox_areas):.0f} pixels²")
    
    print(f"\n📐 Aspect Ratio Statistics:")
    print(f"   Mean Ratio: {statistics.mean(bbox_ratios):.2f}")
    print(f"   Median Ratio: {statistics.median(bbox_ratios):.2f}")
    
    # Per-class bbox statistics
    print(f"\n📊 Per-Class Bounding Box Statistics:")
    for class_name in bbox_areas_by_class.keys():
        areas = bbox_areas_by_class[class_name]
        ratios = bbox_ratios_by_class[class_name]
        print(f"   {class_name}:")
        print(f"     Mean Area: {statistics.mean(areas):.0f} pixels²")
        print(f"     Mean Ratio: {statistics.mean(ratios):.2f}")
    
    return {
        'areas': {
            'mean': statistics.mean(bbox_areas),
            'median': statistics.median(bbox_areas),
            'min': min(bbox_areas),
            'max': max(bbox_areas)
        },
        'ratios': {
            'mean': statistics.mean(bbox_ratios),
            'median': statistics.median(bbox_ratios)
        }
    }

def test_confidence_thresholds(model, test_images, output_dir):
    """Test different confidence thresholds to find optimal settings"""
    print("\n🎯 Testing Multiple Confidence Thresholds...")
    
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    threshold_results = {}
    
    animal_classes = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']
    
    for threshold in thresholds:
        print(f"\n  Testing threshold: {threshold}")
        total_detections = 0
        detections_by_class = Counter()
        processing_times = []
        
        for i, image_path in enumerate(test_images[:20]):  # Test on subset for speed
            start_time = time.time()
            results = model(str(image_path), conf=threshold, verbose=False)
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id]
                        if class_name in animal_classes:
                            total_detections += 1
                            detections_by_class[class_name] += 1
        
        threshold_results[threshold] = {
            'total_detections': total_detections,
            'detections_by_class': dict(detections_by_class),
            'avg_processing_time': statistics.mean(processing_times),
            'images_processed': len(test_images[:20])
        }
        
        print(f"    Total detections: {total_detections}")
        print(f"    Avg processing time: {statistics.mean(processing_times):.3f}s")
    
    # Save threshold analysis
    threshold_file = output_dir / "threshold_analysis.json"
    with open(threshold_file, 'w') as f:
        json.dump(threshold_results, f, indent=2)
    
    # Find optimal threshold
    detection_counts = [data['total_detections'] for data in threshold_results.values()]
    if detection_counts:
        optimal_threshold = None
        best_balance = 0
        
        for thresh, data in threshold_results.items():
            # Balance between detection count and precision (higher threshold = higher precision)
            balance_score = data['total_detections'] * thresh
            if balance_score > best_balance:
                best_balance = balance_score
                optimal_threshold = thresh
        
        print(f"\n🎯 Recommended optimal threshold: {optimal_threshold}")
        print(f"   (Best balance of detection count vs precision)")
    
    return threshold_results

def benchmark_processing_speed(model, test_images, iterations=3):
    """Benchmark processing speed with multiple runs"""
    print(f"\n⚡ Benchmarking Processing Speed ({iterations} iterations)...")
    
    sample_images = test_images[:10]  # Use subset for benchmarking
    all_times = []
    
    for iteration in range(iterations):
        print(f"  Iteration {iteration + 1}/{iterations}")
        iteration_times = []
        
        for image_path in sample_images:
            start_time = time.time()
            results = model(str(image_path), conf=0.3, verbose=False)
            processing_time = time.time() - start_time
            iteration_times.append(processing_time)
        
        all_times.extend(iteration_times)
        avg_time = statistics.mean(iteration_times)
        fps = len(sample_images) / sum(iteration_times)
        print(f"    Avg time: {avg_time:.3f}s, FPS: {fps:.1f}")
    
    # Overall statistics
    overall_avg = statistics.mean(all_times)
    overall_median = statistics.median(all_times)
    overall_std = statistics.stdev(all_times)
    min_time = min(all_times)
    max_time = max(all_times)
    
    print(f"\n📊 Overall Speed Statistics:")
    print(f"   Average: {overall_avg:.3f}s per image")
    print(f"   Median: {overall_median:.3f}s per image")
    print(f"   Min: {min_time:.3f}s")
    print(f"   Max: {max_time:.3f}s")
    print(f"   Std Dev: {overall_std:.3f}s")
    print(f"   Theoretical Max FPS: {1/overall_avg:.1f}")
    print(f"   Real-time capable: {'✅ Yes' if overall_avg < 0.033 else '⚠️ Marginal' if overall_avg < 0.1 else '❌ No'}")
    
    return {
        'average': overall_avg,
        'median': overall_median,
        'min': min_time,
        'max': max_time,
        'std': overall_std,
        'max_fps': 1/overall_avg,
        'iterations': iterations,
        'images_per_iteration': len(sample_images)
    }

def create_detection_heatmap(results_file, output_dir):
    """Create heatmap showing where animals are typically detected in images"""
    print("\n🔥 Creating Detection Position Heatmap...")
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Assume standard image dimensions (will normalize)
    heatmap_size = (100, 100)  # 100x100 grid
    heatmap = np.zeros(heatmap_size)
    
    total_detections = 0
    
    for result in results:
        for detection in result.get('detections', []):
            bbox = detection['bbox']  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox
            
            # Calculate center point
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Normalize to image dimensions (assuming typical surveillance camera resolution)
            # This is a rough estimate - in real implementation we'd get actual image dimensions
            norm_x = center_x / 3000  # Assume ~3000px width
            norm_y = center_y / 2000  # Assume ~2000px height
            
            # Convert to heatmap coordinates
            heatmap_x = int(norm_x * (heatmap_size[1] - 1))
            heatmap_y = int(norm_y * (heatmap_size[0] - 1))
            
            # Clamp to valid range
            heatmap_x = max(0, min(heatmap_size[1] - 1, heatmap_x))
            heatmap_y = max(0, min(heatmap_size[0] - 1, heatmap_y))
            
            # Add to heatmap with gaussian blur effect
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    hy = heatmap_y + dy
                    hx = heatmap_x + dx
                    if 0 <= hy < heatmap_size[0] and 0 <= hx < heatmap_size[1]:
                        distance = np.sqrt(dx*dx + dy*dy)
                        weight = np.exp(-distance / 2)  # Gaussian-like weight
                        heatmap[hy, hx] += weight
            
            total_detections += 1
    
    if total_detections == 0:
        print("⚠️ No detections found for heatmap generation")
        return
    
    # Save heatmap data
    heatmap_file = output_dir / "detection_heatmap.npy"
    np.save(heatmap_file, heatmap)
    
    print(f"🔥 Generated heatmap from {total_detections} detections")
    print(f"💾 Saved heatmap data: {heatmap_file}")
    
    return heatmap

def compare_with_previous_results():
    """Compare YOLOv11n results with previous detection methods"""
    print("\n🔄 Comparing with Previous Detection Methods...")
    
    comparison_data = {}
    
    # Load YOLOv11n results
    yolo_file = Path("yolov11_detections/yolov11_summary.json")
    if yolo_file.exists():
        with open(yolo_file, 'r') as f:
            comparison_data['YOLOv11n'] = json.load(f)
    
    # Load GroundingDINO results if available
    grounding_file = Path("groundingdino_detections/groundingdino_summary.json")
    if grounding_file.exists():
        with open(grounding_file, 'r') as f:
            comparison_data['GroundingDINO'] = json.load(f)
    
    # Load EfficientNet results if available (would need to be created)
    # efficient_file = Path("efficientnet_results/efficientnet_summary.json")
    # if efficient_file.exists():
    #     with open(efficient_file, 'r') as f:
    #         comparison_data['EfficientNet'] = json.load(f)
    
    if len(comparison_data) < 2:
        print("⚠️ Need at least 2 methods to compare")
        return
    
    print(f"📊 Comparison Results:")
    print(f"{'Method':<15} {'Images':<8} {'Detections':<12} {'Avg Time':<10} {'FPS':<8}")
    print("-" * 60)
    
    for method, data in comparison_data.items():
        images = data.get('total_images_processed', 0)
        detections = data.get('total_detections', 0)
        avg_time = data.get('avg_time_per_image', 0)
        fps = 1/avg_time if avg_time > 0 else 0
        
        print(f"{method:<15} {images:<8} {detections:<12} {avg_time:<10.3f} {fps:<8.1f}")
    
    return comparison_data

def run_extended_analysis():
    """Run comprehensive extended analysis of YOLOv11n performance"""
    print("🚀 YOLOv11n Extended Analysis Suite")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Setup model
    model = setup_yolov11()
    if model is None:
        return 1
    
    # Check if previous results exist
    results_file = Path("yolov11_detections/yolov11_results.json")
    summary_file = Path("yolov11_detections/yolov11_summary.json")
    
    if not results_file.exists():
        print("❌ Previous YOLOv11n results not found. Please run the basic test first.")
        return 1
    
    # Create extended analysis output directory
    extended_dir = Path("yolov11_extended_analysis")
    extended_dir.mkdir(exist_ok=True)
    
    # Run analyses
    print("\n🔍 Running Extended Analyses...")
    
    # 1. Confidence distribution analysis
    confidence_stats = analyze_confidence_distribution(results_file)
    
    # 2. Bounding box size analysis
    bbox_stats = analyze_bbox_sizes(results_file)
    
    # 3. Collect test images for additional tests
    test_images = []
    dummy_surveillance = Path("public/dummy-surveillance")
    if dummy_surveillance.exists():
        for category_dir in dummy_surveillance.iterdir():
            if category_dir.is_dir():
                test_images.extend(list(category_dir.glob("*.jpg")))
    
    if test_images:
        # 4. Confidence threshold testing
        threshold_results = test_confidence_thresholds(model, test_images, extended_dir)
        
        # 5. Processing speed benchmark
        speed_stats = benchmark_processing_speed(model, test_images)
        
        # 6. Detection heatmap
        heatmap = create_detection_heatmap(results_file, extended_dir)
    
    # 7. Comparison with other methods
    comparison_results = compare_with_previous_results()
    
    # Compile extended summary
    extended_summary = {
        'analysis_timestamp': time.time(),
        'confidence_analysis': confidence_stats,
        'bbox_analysis': bbox_stats,
        'speed_benchmark': speed_stats if test_images else None,
        'threshold_testing': threshold_results if test_images else None,
        'method_comparison': comparison_results
    }
    
    # Save extended summary
    extended_summary_file = extended_dir / "extended_analysis_summary.json"
    with open(extended_summary_file, 'w') as f:
        json.dump(extended_summary, f, indent=2)
    
    print(f"\n✨ Extended Analysis Complete!")
    print(f"📁 Results saved to: {extended_dir}/")
    print(f"📄 Extended summary: {extended_summary_file}")
    
    # Show key insights
    print(f"\n🔍 Key Insights:")
    if confidence_stats:
        overall_conf = confidence_stats['overall']
        print(f"   📊 Detection Confidence: {overall_conf['mean']:.3f} ± {overall_conf['std']:.3f}")
    
    if 'speed_benchmark' in extended_summary and extended_summary['speed_benchmark']:
        speed = extended_summary['speed_benchmark']
        print(f"   ⚡ Processing Speed: {speed['average']:.3f}s per image ({speed['max_fps']:.1f} FPS max)")
    
    if comparison_results:
        print(f"   🔄 Compared with {len(comparison_results)} detection methods")
    
    print(f"\n🎉 Extended analysis provides deeper insights into YOLOv11n performance!")
    
    return 0

if __name__ == "__main__":
    sys.exit(run_extended_analysis())
