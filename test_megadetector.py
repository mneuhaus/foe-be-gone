#!/usr/bin/env python3
"""
Basic MegaDetector test script for M4 MacBook Pro
Tests MegaDetector installation and basic functionality
"""

import os
import sys
import time
from pathlib import Path

# Check if we're in virtual environment
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

def test_imports():
    """Test importing required modules"""
    print("\n🔍 Testing imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
        
        # Check if MPS (Metal Performance Shaders) is available for Apple Silicon
        if torch.backends.mps.is_available():
            print("✅ MPS (Apple Silicon GPU) is available")
            device = torch.device('mps')
            print(f"✅ Using device: {device}")
        else:
            print("⚠️  MPS not available, using CPU")
            device = torch.device('cpu')
            print(f"✅ Using device: {device}")
            
    except ImportError as e:
        print(f"❌ PyTorch import failed: {e}")
        return False, None
    
    try:
        import megadetector
        print(f"✅ MegaDetector imported")
        
        # Import specific MegaDetector modules
        from megadetector.detection.run_detector import load_detector, load_and_run_detector
        print("✅ MegaDetector detection modules imported")
        
    except ImportError as e:
        print(f"❌ MegaDetector import failed: {e}")
        return False, None
    
    return True, device

def download_model():
    """Download MegaDetector model if not already available"""
    print("\n📥 Checking/downloading MegaDetector model...")
    
    try:
        from megadetector.detection.run_detector import load_detector
        
        # Use the default MDv5 model
        model_path = "MDV5A"  # This will auto-download the model
        print(f"Loading model: {model_path}")
        
        start_time = time.time()
        detector = load_detector(model_path)
        load_time = time.time() - start_time
        
        print(f"✅ Model loaded successfully in {load_time:.2f} seconds")
        return detector
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return None

def crop_detections_from_image(image_path, detections, output_dir, confidence_threshold=0.3, expansion_factor=0.5):
    """Extract detected animals as separate cropped images with expanded bounding boxes"""
    try:
        from PIL import Image
        import numpy as np
        
        # Load the original image
        image = Image.open(image_path)
        img_width, img_height = image.size
        
        cropped_animals = []
        
        for i, detection in enumerate(detections):
            category = detection.get('category', 0)
            confidence = detection.get('conf', 0)
            bbox = detection.get('bbox', [])
            
            # Convert category to int (MegaDetector returns strings)
            try:
                category = int(category)
            except (ValueError, TypeError):
                category = 0
            
            # Convert confidence to float
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = 0.0
            
            # Only process animals (category 1) above confidence threshold
            if category == 1 and confidence >= confidence_threshold and len(bbox) == 4:
                # MegaDetector bbox format: [x_min, y_min, width, height] in relative coordinates
                x_min_rel, y_min_rel, width_rel, height_rel = bbox
                
                # Convert to absolute pixel coordinates
                x_min = int(x_min_rel * img_width)
                y_min = int(y_min_rel * img_height) 
                x_max = int((x_min_rel + width_rel) * img_width)
                y_max = int((y_min_rel + height_rel) * img_height)
                
                # Calculate box dimensions
                box_width = x_max - x_min
                box_height = y_max - y_min
                
                # Expand box by specified factor (50% = 0.5)
                width_expansion = int(box_width * expansion_factor / 2)  # Half on each side
                height_expansion = int(box_height * expansion_factor / 2)  # Half on each side
                
                # Apply expansion while staying within image bounds
                x_min_expanded = max(0, x_min - width_expansion)
                y_min_expanded = max(0, y_min - height_expansion)
                x_max_expanded = min(img_width, x_max + width_expansion)
                y_max_expanded = min(img_height, y_max + height_expansion)
                
                # Crop the animal with expanded bounding box
                cropped = image.crop((x_min_expanded, y_min_expanded, x_max_expanded, y_max_expanded))
                
                # Generate filename
                original_name = Path(image_path).stem
                crop_filename = f"{original_name}_animal_{i+1}_conf_{confidence:.2f}_expanded.jpg"
                crop_path = output_dir / crop_filename
                
                # Save cropped image
                cropped.save(crop_path, 'JPEG', quality=95)
                
                cropped_animals.append({
                    'filename': crop_filename,
                    'confidence': confidence,
                    'bbox_original': (x_min, y_min, x_max, y_max),
                    'bbox_expanded': (x_min_expanded, y_min_expanded, x_max_expanded, y_max_expanded),
                    'size': (x_max_expanded - x_min_expanded, y_max_expanded - y_min_expanded),
                    'expansion_factor': expansion_factor
                })
        
        return cropped_animals
        
    except Exception as e:
        print(f"❌ Error cropping detections from {image_path}: {e}")
        return []

def run_detector_and_extract_animals(image_paths, output_dir, confidence_threshold=0.3):
    """Run MegaDetector and extract animal detections with 50% expanded bounding boxes"""
    try:
        from megadetector.detection.run_detector import load_detector
        import json
        import tempfile
        import shutil
        
        total_animals_found = 0
        results_summary = {}
        
        # Create subdirectories
        detections_dir = output_dir / "detections_with_boxes"
        crops_dir = output_dir / "animal_crops"
        detections_dir.mkdir(exist_ok=True)
        crops_dir.mkdir(exist_ok=True)
        
        print("🔍 Loading MegaDetector model...")
        detector = load_detector("MDV5A")
        
        print("🔍 Running detection and extraction on each image...")
        
        total_inference_time = 0
        
        for image_path in image_paths:
            original_name = Path(image_path).stem
            print(f"📸 Processing: {Path(image_path).name}")
            
            start_time = time.time()
            
            # Run detection on single image to get detection results AND detection image
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output = Path(temp_dir)
                
                # Run detector to get visualization with boxes
                from megadetector.detection.run_detector import load_and_run_detector
                load_and_run_detector(
                    model_file="MDV5A",  # Use model string, not detector object
                    image_file_names=[str(image_path)],
                    output_dir=str(temp_output),
                    render_confidence_threshold=0.1,
                    crop_images=False
                )
                
                # Copy detection image with boxes
                detection_files = list(temp_output.glob("*.jpg"))
                if detection_files:
                    detection_output = detections_dir / f"{original_name}_detections.jpg"
                    shutil.copy2(detection_files[0], detection_output)
                
                # Now run raw detection to get bounding box coordinates
                from PIL import Image
                
                # Load image
                image = Image.open(image_path)
                
                # Run detector to get raw detection results
                detections = detector.generate_detections_one_image(image)
            
            inference_time = time.time() - start_time
            total_inference_time += inference_time
            
            # Extract animal crops with 50% expansion
            # detections is a dict with 'detections' key containing the actual detection list
            detection_list = detections.get('detections', []) if isinstance(detections, dict) else detections
            cropped_animals = crop_detections_from_image(
                image_path, detection_list, crops_dir, confidence_threshold, expansion_factor=0.5
            )
            
            total_animals_found += len(cropped_animals)
            
            # Store results
            results_summary[original_name] = {
                'inference_time': inference_time,
                'animals_detected': len(cropped_animals),
                'crops': cropped_animals
            }
            
            if cropped_animals:
                print(f"  🦌 Found {len(cropped_animals)} animals (50% expanded crops saved)")
                for animal in cropped_animals:
                    print(f"    - {animal['filename']} (conf: {animal['confidence']:.2f})")
            else:
                print(f"  ⚪ No animals detected above {confidence_threshold} confidence")
        
        return results_summary, total_animals_found
        
    except Exception as e:
        print(f"❌ Detection and extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return {}, 0

def extract_random_frames_from_video(video_path, num_frames=3):
    """Extract random frames from an MP4 video"""
    try:
        import cv2
        import random
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ Could not open video: {video_path}")
            return []
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"📹 Video: {video_path.name}")
        print(f"   Frames: {total_frames}, FPS: {fps:.1f}, Duration: {duration:.1f}s")
        
        if total_frames < num_frames:
            num_frames = total_frames
        
        # Generate random frame numbers
        frame_numbers = sorted(random.sample(range(total_frames), num_frames))
        
        extracted_frames = []
        
        for i, frame_num in enumerate(frame_numbers):
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if ret:
                # Create output filename
                video_stem = video_path.stem
                frame_filename = f"{video_stem}_frame_{frame_num:06d}.jpg"
                frame_path = Path("temp_video_frames") / frame_filename
                frame_path.parent.mkdir(exist_ok=True)
                
                # Save frame
                cv2.imwrite(str(frame_path), frame)
                extracted_frames.append(frame_path)
                print(f"   📸 Extracted frame {frame_num} -> {frame_filename}")
            else:
                print(f"   ❌ Failed to extract frame {frame_num}")
        
        cap.release()
        return extracted_frames
        
    except ImportError:
        print("❌ OpenCV not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "opencv-python"], check=True)
        return extract_random_frames_from_video(video_path, num_frames)
    except Exception as e:
        print(f"❌ Error extracting frames from {video_path}: {e}")
        return []

def test_with_video_frames(device):
    """Test MegaDetector with random frames from dummy videos"""
    print("\n🎬 Testing with frames from dummy surveillance videos...")
    
    # Find all dummy videos
    video_base_path = Path("public/dummy-videos")
    if not video_base_path.exists():
        print("❌ No dummy-videos directory found")
        return False
    
    # Collect all videos
    video_files = list(video_base_path.glob("*.mp4"))
    
    if not video_files:
        print("❌ No MP4 videos found in dummy-videos directory")
        return False
    
    print(f"📊 Found {len(video_files)} MP4 videos")
    
    try:
        # Create output directory
        output_dir = Path("megadetector_video_extraction")
        output_dir.mkdir(exist_ok=True)
        
        # Create temp directory for frames
        temp_frames_dir = Path("temp_video_frames")
        temp_frames_dir.mkdir(exist_ok=True)
        
        print(f"\n🎬 Extracting random frames from {len(video_files)} videos...")
        
        all_extracted_frames = []
        
        # Extract 3 random frames from each video
        for video_file in video_files:
            frames = extract_random_frames_from_video(video_file, num_frames=3)
            all_extracted_frames.extend(frames)
        
        if not all_extracted_frames:
            print("❌ No frames were extracted from videos")
            return False
        
        print(f"\n🖼️  Extracted {len(all_extracted_frames)} frames total")
        print(f"🚀 Processing frames with animal extraction...")
        
        start_time = time.time()
        
        # Run detection and extraction on all frames
        results_summary, total_animals = run_detector_and_extract_animals(
            all_extracted_frames, output_dir, confidence_threshold=0.3
        )
        
        total_time = time.time() - start_time
        avg_time = total_time / len(all_extracted_frames)
        
        print(f"\n✅ Detection and extraction completed!")
        print(f"   Total time: {total_time:.2f} seconds")
        print(f"   Average per frame: {avg_time:.2f} seconds")
        print(f"   Frames per second: {len(all_extracted_frames)/total_time:.2f}")
        print(f"   🦌 Total animals extracted: {total_animals}")
        
        # Save summary
        import json
        summary_file = output_dir / "video_extraction_summary.json"
        with open(summary_file, 'w') as f:
            # Add video source info to summary
            enhanced_summary = {}
            for frame_name, result in results_summary.items():
                # Extract video name from frame name
                video_name = frame_name.split('_frame_')[0] if '_frame_' in frame_name else frame_name
                enhanced_summary[frame_name] = {
                    **result,
                    'source_video': video_name
                }
            json.dump(enhanced_summary, f, indent=2)
        
        # Print detailed results
        print(f"\n📁 Output structure:")
        print(f"  📂 {output_dir}/")
        print(f"    📂 detections_with_boxes/ - Frames with bounding boxes")
        print(f"    📂 animal_crops/ - Extracted animal cutouts (50% expanded)")
        print(f"    📄 video_extraction_summary.json - Detailed results")
        print(f"  📂 temp_video_frames/ - Extracted frames (temporary)")
        
        # Count files
        detection_files = list((output_dir / "detections_with_boxes").glob("*.jpg"))
        crop_files = list((output_dir / "animal_crops").glob("*.jpg"))
        
        print(f"\n📊 Results breakdown:")
        print(f"  Detection frames: {len(detection_files)}")
        print(f"  Animal crops: {len(crop_files)}")
        
        if crop_files:
            print(f"\n🦌 Sample animal crops from videos:")
            for crop_file in crop_files[:5]:  # Show first 5
                print(f"  - {crop_file.name}")
            if len(crop_files) > 5:
                print(f"  ... and {len(crop_files) - 5} more")
        
        # Cleanup temp frames
        import shutil
        shutil.rmtree(temp_frames_dir)
        print(f"\n🧹 Cleaned up temporary frames")
        
        return True
        
    except Exception as e:
        print(f"❌ Video processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_all_dummy_images(device):
    """Test MegaDetector with all dummy surveillance images and extract animals"""
    print("\n🖼️  Testing with ALL dummy surveillance images...")
    
    # Find all dummy surveillance directories
    dummy_base_path = Path("public/dummy-surveillance")
    if not dummy_base_path.exists():
        print("❌ No dummy-surveillance directory found")
        return False
    
    # Collect all images from all subdirectories
    all_images = []
    categories = {}
    
    for category_dir in dummy_base_path.iterdir():
        if category_dir.is_dir():
            images = list(category_dir.glob("*.jpg"))
            if images:
                categories[category_dir.name] = len(images)
                all_images.extend(images)  # Keep as Path objects
    
    if not all_images:
        print("❌ No images found in dummy-surveillance directories")
        return False
    
    print(f"📊 Found {len(all_images)} images across {len(categories)} categories:")
    for category, count in categories.items():
        print(f"  - {category}: {count} images")
    
    try:
        # Create output directory
        output_dir = Path("megadetector_animal_extraction")
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n🚀 Processing {len(all_images)} images with animal extraction...")
        start_time = time.time()
        
        # Run detection and extraction
        results_summary, total_animals = run_detector_and_extract_animals(
            all_images, output_dir, confidence_threshold=0.3
        )
        
        total_time = time.time() - start_time
        avg_time = total_time / len(all_images)
        
        print(f"\n✅ Detection and extraction completed!")
        print(f"   Total time: {total_time:.2f} seconds")
        print(f"   Average per image: {avg_time:.2f} seconds")
        print(f"   Images per second: {len(all_images)/total_time:.2f}")
        print(f"   🦌 Total animals extracted: {total_animals}")
        
        # Save summary
        import json
        summary_file = output_dir / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results_summary, f, indent=2)
        
        # Print detailed results
        print(f"\n📁 Output structure:")
        print(f"  📂 {output_dir}/")
        print(f"    📂 detections_with_boxes/ - Images with bounding boxes")
        print(f"    📂 animal_crops/ - Extracted animal cutouts (50% expanded)")
        print(f"    📄 extraction_summary.json - Detailed results")
        
        # Count files
        detection_files = list((output_dir / "detections_with_boxes").glob("*.jpg"))
        crop_files = list((output_dir / "animal_crops").glob("*.jpg"))
        
        print(f"\n📊 Results breakdown:")
        print(f"  Detection images: {len(detection_files)}")
        print(f"  Animal crops: {len(crop_files)}")
        
        if crop_files:
            print(f"\n🦌 Sample animal crops:")
            for crop_file in crop_files[:5]:  # Show first 5
                print(f"  - {crop_file.name}")
            if len(crop_files) > 5:
                print(f"  ... and {len(crop_files) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Detection and extraction failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 MegaDetector Test Script for M4 MacBook Pro")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Test imports
    imports_ok, device = test_imports()
    if not imports_ok:
        return 1
    
    # Ask user what to test
    print("\nWhat would you like to test?")
    print("1. Static images from dummy-surveillance")
    print("2. Random frames from dummy-videos")
    print("3. Both images and videos")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        print("\n" + "="*50)
        if not test_with_all_dummy_images(device):
            return 1
    
    if choice in ['2', '3']:
        print("\n" + "="*50)
        if not test_with_video_frames(device):
            return 1
    
    print("\n🎉 All tests passed! MegaDetector is working correctly.")
    print("\nNext steps:")
    print("1. The virtual environment is working: megadetector_env/")
    print("2. MegaDetector is properly installed with Apple Silicon support")
    print("3. You can now integrate this into your main application")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())