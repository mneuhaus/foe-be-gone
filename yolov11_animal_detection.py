#!/usr/bin/env python3
"""
YOLOv11n Animal Detection Script
Fast and accurate animal detection with bounding box visualization
Optimized for surveillance footage analysis
"""

import os
import sys
import time
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def check_environment():
    """Check if we're running in the correct virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        print(f"Python executable: {sys.executable}")
        print(f"Python version: {sys.version}")
    else:
        print("❌ NOT running in virtual environment")
        print("Please activate the virtual environment:")
        print("source megadetector_env/bin/activate")
        return False
    return True

def setup_yolov11():
    """Setup YOLOv11 model"""
    print("\n📥 Setting up YOLOv11...")
    
    try:
        # Install/update ultralytics to get YOLOv11 support
        import subprocess
        print("Ensuring latest ultralytics for YOLOv11 support...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "ultralytics"], 
                              capture_output=True, text=True)
        
        # Import YOLO
        from ultralytics import YOLO
        
        print("Loading YOLOv11n model...")
        start_time = time.time()
        
        # Load YOLOv11 nano model (fastest)
        model = YOLO('yolo11n.pt')  # This will auto-download YOLOv11n
        
        load_time = time.time() - start_time
        print(f"✅ YOLOv11n loaded successfully in {load_time:.2f} seconds")
        
        # Print model info
        print(f"   Model: YOLOv11n")
        print(f"   Classes: {len(model.names)} COCO classes")
        print(f"   Animal classes available: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe")
        
        return model
        
    except Exception as e:
        print(f"❌ YOLOv11 setup failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def draw_detections_on_image(image_path, detections, output_path, model):
    """Draw bounding boxes and labels on image using OpenCV for better performance"""
    try:
        # Load image with OpenCV
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"❌ Could not load image: {image_path}")
            return 0
        
        height, width = image.shape[:2]
        
        # Define colors for different animal types
        colors = {
            'bird': (0, 255, 0),      # Green
            'cat': (255, 0, 0),       # Blue  
            'dog': (0, 0, 255),       # Red
            'horse': (255, 255, 0),   # Cyan
            'sheep': (255, 0, 255),   # Magenta
            'cow': (0, 255, 255),     # Yellow
            'elephant': (128, 0, 128), # Purple
            'bear': (255, 165, 0),    # Orange
            'zebra': (0, 128, 255),   # Light Blue
            'giraffe': (128, 255, 0), # Light Green
            'default': (255, 255, 255) # White
        }
        
        detection_count = 0
        
        for detection in detections:
            class_name = detection['class_name']
            confidence = detection['confidence']
            bbox = detection['bbox']  # [x1, y1, x2, y2]
            
            # Get color for this class
            color = colors.get(class_name, colors['default'])
            
            # Convert bbox to integers
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw bounding box
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
            
            # Prepare label text
            label_text = f"{class_name}: {confidence:.2f}"
            
            # Get text size for background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)
            
            # Draw background rectangle for text
            cv2.rectangle(image, 
                         (x1, y1 - text_height - baseline - 10), 
                         (x1 + text_width + 10, y1), 
                         color, -1)
            
            # Draw text
            cv2.putText(image, label_text, 
                       (x1 + 5, y1 - baseline - 5), 
                       font, font_scale, (0, 0, 0), thickness)
            
            detection_count += 1
        
        # Save the image
        cv2.imwrite(str(output_path), image)
        
        return detection_count
        
    except Exception as e:
        print(f"❌ Error drawing detections: {e}")
        return 0

def process_image_with_yolov11(model, image_path, output_dir, confidence_threshold=0.3):
    """Process single image with YOLOv11"""
    try:
        image_name = Path(image_path).stem
        print(f"\n📸 Processing: {Path(image_path).name}")
        
        start_time = time.time()
        
        # Run YOLOv11 detection
        results = model(str(image_path), conf=confidence_threshold, verbose=False)
        
        inference_time = time.time() - start_time
        
        # Extract detections
        detections = []
        animal_classes = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().numpy().tolist()  # [x1, y1, x2, y2]
                    
                    # Only keep animal detections
                    if class_name in animal_classes:
                        detection = {
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': confidence,
                            'bbox': bbox
                        }
                        detections.append(detection)
        
        if not detections:
            print(f"   ⚪ No animals detected")
            return {
                'image_name': image_name,
                'animals_detected': 0,
                'inference_time': inference_time,
                'detections': []
            }
        
        # Draw detections on image
        output_path = output_dir / f"{image_name}_yolov11_detections.jpg"
        detection_count = draw_detections_on_image(image_path, detections, output_path, model)
        
        # Group by animal type
        animal_counts = {}
        for detection in detections:
            animal_type = detection['class_name']
            animal_counts[animal_type] = animal_counts.get(animal_type, 0) + 1
        
        print(f"   🐾 Found {len(detections)} animals:")
        for animal_type, count in animal_counts.items():
            avg_conf = np.mean([d['confidence'] for d in detections if d['class_name'] == animal_type])
            print(f"     - {animal_type}: {count} (avg conf: {avg_conf:.3f})")
        
        print(f"   💾 Saved: {output_path.name}")
        print(f"   ⏱️  Inference time: {inference_time:.3f}s")
        
        return {
            'image_name': image_name,
            'animals_detected': len(detections),
            'inference_time': inference_time,
            'detections': detections,
            'animal_counts': animal_counts,
            'output_image': str(output_path)
        }
        
    except Exception as e:
        print(f"❌ Error processing {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'image_name': Path(image_path).stem,
            'animals_detected': 0,
            'inference_time': 0,
            'detections': [],
            'error': str(e)
        }

def extract_frames_from_videos(num_frames_per_video=5):
    """Extract random frames from dummy videos"""
    print("\n🎬 Extracting frames from dummy videos...")
    
    video_base_path = Path("public/dummy-videos")
    if not video_base_path.exists():
        print("⚠️  No dummy-videos directory found")
        return []
    
    video_files = list(video_base_path.glob("*.mp4"))
    if not video_files:
        print("⚠️  No MP4 videos found")
        return []
    
    print(f"📹 Found {len(video_files)} videos")
    
    try:
        import cv2
        import random
        
        # Create temp directory for frames
        frames_dir = Path("temp_yolov11_frames")
        frames_dir.mkdir(exist_ok=True)
        
        extracted_frames = []
        
        for video_file in video_files:
            print(f"  📽️  Extracting from: {video_file.name}")
            
            # Open video
            cap = cv2.VideoCapture(str(video_file))
            if not cap.isOpened():
                print(f"    ❌ Could not open video: {video_file}")
                continue
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if total_frames < num_frames_per_video:
                frame_numbers = list(range(total_frames))
            else:
                frame_numbers = sorted(random.sample(range(total_frames), num_frames_per_video))
            
            # Extract frames
            for frame_num in frame_numbers:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    video_stem = video_file.stem
                    frame_filename = f"{video_stem}_frame_{frame_num:06d}.jpg"
                    frame_path = frames_dir / frame_filename
                    
                    cv2.imwrite(str(frame_path), frame)
                    extracted_frames.append(frame_path)
            
            cap.release()
            print(f"    ✅ Extracted {len(frame_numbers)} frames")
        
        print(f"🎬 Total frames extracted: {len(extracted_frames)}")
        return extracted_frames
        
    except ImportError:
        print("❌ OpenCV not available for video processing")
        return []
    except Exception as e:
        print(f"❌ Error extracting video frames: {e}")
        return []

def test_yolov11_on_images():
    """Test YOLOv11 on surveillance images and video frames"""
    print("🚀 YOLOv11n Comprehensive Animal Detection Test")
    print("=" * 55)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Setup YOLOv11
    model = setup_yolov11()
    if model is None:
        print("❌ Failed to setup YOLOv11")
        return 1
    
    all_images = []
    
    # Collect ALL images from dummy surveillance (no limit)
    dummy_surveillance = Path("public/dummy-surveillance")
    if dummy_surveillance.exists():
        print("\n📁 Collecting dummy surveillance images...")
        for category_dir in dummy_surveillance.iterdir():
            if category_dir.is_dir():
                images = list(category_dir.glob("*.jpg"))
                all_images.extend(images)
                print(f"  📸 {category_dir.name}/: {len(images)} images")
    
    # Extract frames from videos
    video_frames = extract_frames_from_videos(num_frames_per_video=5)
    all_images.extend(video_frames)
    
    if not all_images:
        print("❌ No test images found")
        return 1
    
    # Test on ALL available images for comprehensive analysis
    test_images = all_images
    print(f"\n📊 Testing YOLOv11n on {len(test_images)} images total:")
    print(f"   📸 Surveillance images: {len(all_images) - len(video_frames)}")
    print(f"   🎬 Video frames: {len(video_frames)}")
    
    # Create output directory
    output_dir = Path("yolov11_detections")
    output_dir.mkdir(exist_ok=True)
    
    # Process all images
    start_time = time.time()
    all_results = []
    total_animals = 0
    total_by_type = {}
    
    for i, image_path in enumerate(test_images, 1):
        print(f"\n[{i}/{len(test_images)}]", end="")
        result = process_image_with_yolov11(
            model, image_path, output_dir, confidence_threshold=0.3
        )
        all_results.append(result)
        total_animals += result['animals_detected']
        
        # Aggregate animal counts
        if 'animal_counts' in result:
            for animal_type, count in result['animal_counts'].items():
                total_by_type[animal_type] = total_by_type.get(animal_type, 0) + count
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_images)
    
    # Save results
    results_file = output_dir / "yolov11_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Create summary
    summary = {
        'total_images_processed': len(test_images),
        'total_animals_detected': total_animals,
        'animals_by_type': total_by_type,
        'total_processing_time': total_time,
        'avg_time_per_image': avg_time,
        'images_per_second': len(test_images) / total_time,
        'confidence_threshold': 0.3,
        'model_info': {
            'model': 'YOLOv11n',
            'version': 'ultralytics',
            'classes_detected': list(total_by_type.keys())
        }
    }
    
    summary_file = output_dir / "yolov11_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print results
    print(f"\n" + "="*50)
    print(f"✅ YOLOv11n detection completed!")
    print(f"   📊 Processed {len(test_images)} images in {total_time:.2f} seconds")
    print(f"   ⚡ Average: {avg_time:.3f}s per image ({len(test_images)/total_time:.1f} fps)")
    print(f"   🐾 Total animals detected: {total_animals}")
    if len(test_images) > 0:
        print(f"   📈 Detection rate: {total_animals/len(test_images):.1f} animals per image")
    
    # Show animal breakdown
    if total_by_type:
        print(f"\n🐾 Animals detected by type:")
        for animal_type, count in sorted(total_by_type.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_animals) * 100 if total_animals > 0 else 0
            print(f"   🐕 {animal_type}: {count} ({percentage:.1f}%)")
    
    # Show output structure
    detection_images = list(output_dir.glob("*_detections.jpg"))
    
    print(f"\n📁 Output structure:")
    print(f"  📂 {output_dir}/")
    print(f"    🖼️  {len(detection_images)} detection images with bounding boxes")
    print(f"    📄 yolov11_results.json - Detailed results")
    print(f"    📄 yolov11_summary.json - Summary statistics")
    
    if detection_images:
        print(f"\n🖼️  Sample detection images:")
        for img_file in detection_images[:5]:
            print(f"  - {img_file.name}")
        if len(detection_images) > 5:
            print(f"  ... and {len(detection_images) - 5} more")
    
    # Show detection highlights
    successful_detections = [r for r in all_results if r['animals_detected'] > 0]
    if successful_detections:
        print(f"\n🎯 Detection highlights:")
        for result in successful_detections[:5]:  # Show more examples
            print(f"  📸 {result['image_name']}:")
            if 'animal_counts' in result:
                for animal_type, count in result['animal_counts'].items():
                    avg_conf = np.mean([d['confidence'] for d in result['detections'] if d['class_name'] == animal_type])
                    print(f"    - {animal_type}: {count} (avg conf: {avg_conf:.3f})")
    
    # Performance comparison
    print(f"\n⚡ Performance Analysis:")
    images_with_detections = len(successful_detections)
    detection_rate = (images_with_detections / len(test_images)) * 100
    print(f"  📈 Detection rate: {detection_rate:.1f}% of images had animals")
    print(f"  🚀 Processing speed: {len(test_images)/total_time:.1f} images/second")
    print(f"  ⚡ Real-time capable: {'✅ Yes' if avg_time < 0.2 else '❌ No'} (needs <200ms per frame)")
    
    # Show video vs static image performance
    if video_frames:
        video_results = [r for r in all_results if any(frame.name.startswith(Path(r['image_name']).name) for frame in video_frames)]
        static_results = [r for r in all_results if r not in video_results]
        
        video_detections = sum(r['animals_detected'] for r in video_results)
        static_detections = sum(r['animals_detected'] for r in static_results)
        
        print(f"\n📊 Video vs Static Comparison:")
        print(f"  🎬 Video frames: {len(video_results)} images, {video_detections} animals")
        print(f"  📸 Static images: {len(static_results)} images, {static_detections} animals")
        if len(video_results) > 0:
            print(f"  📈 Video detection rate: {video_detections/len(video_results):.2f} animals per frame")
        if len(static_results) > 0:
            print(f"  📈 Static detection rate: {static_detections/len(static_results):.2f} animals per image")
    
    # Cleanup temp frames
    temp_frames_dir = Path("temp_yolov11_frames")
    if temp_frames_dir.exists():
        import shutil
        shutil.rmtree(temp_frames_dir)
        print(f"\n🧹 Cleaned up temporary video frames")
    
    print(f"\n🎉 YOLOv11n comprehensive animal detection completed!")
    print("✨ Key advantages of YOLOv11n:")
    print("  1. 🚀 Ultra-fast: Latest YOLO architecture for real-time detection")
    print("  2. 🎯 Accurate: State-of-the-art object detection performance")
    print("  3. 🐾 Multi-animal: Detects birds, cats, dogs, and more")
    print("  4. 🔍 COCO trained: Robust performance on real-world images")
    print("  5. 📦 Easy deployment: Single model file, no complex setup")
    print("  6. 🎬 Versatile: Works on both static images and video frames")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_yolov11_on_images())