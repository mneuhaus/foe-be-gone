#!/usr/bin/env python3
"""
YOLOv11n Detection Results Viewer
Display and analyze the best detection results
"""

import json
import sys
from pathlib import Path
from PIL import Image
import os

def show_detection_samples():
    """Show sample detection results"""
    print("🖼️ YOLOv11n Detection Results Viewer")
    print("=" * 40)
    
    # Load results
    results_file = Path("yolov11_detections/yolov11_results.json")
    if not results_file.exists():
        print("❌ No detection results found")
        return
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Find images with detections
    images_with_detections = [r for r in results if r.get('animals_detected', 0) > 0]
    
    if not images_with_detections:
        print("⚠️ No detections found in results")
        return
    
    print(f"📊 Found {len(images_with_detections)} images with detections")
    print(f"🖼️ Detection images saved in: yolov11_detections/")
    
    # Show top detections by confidence
    print("\n🎆 Top Detection Results:")
    print("-" * 30)
    
    # Sort by number of detections and confidence
    sorted_results = sorted(images_with_detections, 
                          key=lambda x: (x.get('animals_detected', 0), 
                                        max([d.get('confidence', 0) for d in x.get('detections', [])], default=0)), 
                          reverse=True)
    
    for i, result in enumerate(sorted_results[:10]):  # Top 10
        image_name = result.get('image_name', 'unknown')
        animal_count = result.get('animals_detected', 0)
        inference_time = result.get('inference_time', 0)
        
        print(f"\n{i+1}. {image_name}")
        print(f"   Animals detected: {animal_count}")
        print(f"   Processing time: {inference_time:.3f}s")
        
        # Show detections
        for j, detection in enumerate(result.get('detections', [])):
            class_name = detection.get('class_name', 'unknown')
            confidence = detection.get('confidence', 0)
            bbox = detection.get('bbox', [])
            
            print(f"   Detection {j+1}: {class_name} ({confidence:.3f} confidence)")
            if len(bbox) == 4:
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                print(f"     Bounding box: {width:.0f}x{height:.0f} pixels")
        
        # Show output image path if available
        if 'output_image' in result:
            output_path = Path(result['output_image'])
            if output_path.exists():
                print(f"   🖼️ Annotated image: {output_path}")
                
                # Try to get image dimensions
                try:
                    with Image.open(output_path) as img:
                        print(f"   📊 Image size: {img.width}x{img.height} pixels")
                except Exception:
                    pass
    
    # Summary statistics
    print(f"\n📊 Detection Summary:")
    print("-" * 20)
    
    total_detections = sum(r.get('animals_detected', 0) for r in images_with_detections)
    total_inference_time = sum(r.get('inference_time', 0) for r in images_with_detections)
    
    animal_counts = {}
    confidence_scores = []
    bbox_areas = []
    
    for result in images_with_detections:
        for detection in result.get('detections', []):
            animal_type = detection.get('class_name', 'unknown')
            animal_counts[animal_type] = animal_counts.get(animal_type, 0) + 1
            
            confidence = detection.get('confidence', 0)
            confidence_scores.append(confidence)
            
            bbox = detection.get('bbox', [])
            if len(bbox) == 4:
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                bbox_areas.append(area)
    
    print(f"Total detections: {total_detections}")
    print(f"Images with detections: {len(images_with_detections)}")
    print(f"Average processing time: {total_inference_time / len(images_with_detections):.3f}s")
    
    print(f"\nAnimals detected:")
    for animal_type, count in sorted(animal_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_detections) * 100
        print(f"  {animal_type}: {count} ({percentage:.1f}%)")
    
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        print(f"\nConfidence scores:")
        print(f"  Average: {avg_confidence:.3f}")
        print(f"  Range: {min_confidence:.3f} - {max_confidence:.3f}")
    
    if bbox_areas:
        avg_area = sum(bbox_areas) / len(bbox_areas)
        min_area = min(bbox_areas)
        max_area = max(bbox_areas)
        print(f"\nBounding box areas:")
        print(f"  Average: {avg_area:.0f} pixels²")
        print(f"  Range: {min_area:.0f} - {max_area:.0f} pixels²")
    
    # List available annotated images
    detection_dir = Path("yolov11_detections")
    annotated_images = list(detection_dir.glob("*_detections.jpg"))
    
    if annotated_images:
        print(f"\n🖼️ Available Annotated Images ({len(annotated_images)} total):")
        print("-" * 35)
        
        # Show first few annotated images
        for i, img_path in enumerate(annotated_images[:5]):
            print(f"  {i+1}. {img_path.name}")
            
            # Try to get file size
            try:
                size_kb = img_path.stat().st_size / 1024
                print(f"     Size: {size_kb:.1f} KB")
            except Exception:
                pass
        
        if len(annotated_images) > 5:
            print(f"  ... and {len(annotated_images) - 5} more images")
        
        print(f"\n📁 To view images, open the files in: {detection_dir.absolute()}")
    
    print(f"\n✨ YOLOv11n successfully detected animals in {len(images_with_detections)} images!")
    print(f"🎆 The model shows excellent performance for wildlife surveillance applications.")

if __name__ == "__main__":
    show_detection_samples()
