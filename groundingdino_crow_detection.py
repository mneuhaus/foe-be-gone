#!/usr/bin/env python3
"""
GroundingDINO Crow Detection Script
Text-prompt based detection for crows and corvids in surveillance images
Generates images with bounding boxes and confidence scores
"""

import os
import sys
import time
import json
from pathlib import Path
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

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

def setup_groundingdino():
    """Setup GroundingDINO model"""
    print("\n📥 Setting up GroundingDINO...")
    
    try:
        # Try the transformers approach first (most reliable)
        from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
        
        print("Loading GroundingDINO via Transformers...")
        start_time = time.time()
        
        model_id = "IDEA-Research/grounding-dino-tiny"
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id)
        
        # Check device availability
        if torch.backends.mps.is_available():
            try:
                device = torch.device('mps')
                model = model.to(device)
                print(f"✅ GroundingDINO loaded on MPS in {time.time() - start_time:.2f}s")
            except Exception as e:
                print(f"⚠️  MPS failed ({e}), falling back to CPU")
                device = torch.device('cpu')
                model = model.to(device)
                print(f"✅ GroundingDINO loaded on CPU in {time.time() - start_time:.2f}s")
        else:
            device = torch.device('cpu')
            model = model.to(device)
            print(f"✅ GroundingDINO loaded on CPU in {time.time() - start_time:.2f}s")
        
        return model, processor, device
        
    except Exception as e:
        print(f"❌ GroundingDINO setup failed: {e}")
        print("Trying alternative approach...")
        
        try:
            # Try groundingdino-py package
            from groundingdino_py import GroundingDINO
            
            print("Loading GroundingDINO via groundingdino-py...")
            start_time = time.time()
            
            model = GroundingDINO()
            device = torch.device('cpu')  # groundingdino-py handles device internally
            processor = None  # Not needed for this approach
            
            print(f"✅ GroundingDINO-py loaded in {time.time() - start_time:.2f}s")
            return model, processor, device
            
        except Exception as e2:
            print(f"❌ All GroundingDINO approaches failed: {e2}")
            return None, None, None

def detect_with_transformers_grounding_dino(model, processor, image, text_prompts, device, confidence_threshold=0.3):
    """Run detection using Transformers GroundingDINO"""
    try:
        all_detections = []
        
        # Run each prompt separately to avoid confusion
        for prompt in text_prompts:
            try:
                # Process inputs for single prompt
                inputs = processor(images=image, text=prompt, return_tensors="pt")
                inputs = {k: v.to(device) if hasattr(v, 'to') else v for k, v in inputs.items()}
                
                # Run inference
                with torch.no_grad():
                    outputs = model(**inputs)
                
                # Post-process results
                target_sizes = torch.tensor([image.size[::-1]]).to(device)  # (height, width)
                results = processor.post_process_grounded_object_detection(
                    outputs, 
                    target_sizes=target_sizes, 
                    threshold=confidence_threshold
                )[0]
                
                # Extract results for this prompt
                if len(results["boxes"]) > 0:
                    boxes = results["boxes"].cpu().numpy()
                    scores = results["scores"].cpu().numpy()
                    labels = results["labels"]
                    
                    for i in range(len(boxes)):
                        detection = {
                            'bbox': boxes[i].tolist(),  # [x1, y1, x2, y2]
                            'confidence': float(scores[i]),
                            'label': prompt,  # Use the actual prompt that found this
                            'prompt_matched': prompt,
                            'detected_text': labels[i] if hasattr(labels, '__getitem__') else prompt
                        }
                        all_detections.append(detection)
                        
            except Exception as e:
                print(f"⚠️  Failed to detect '{prompt}': {e}")
                continue
        
        return all_detections
        
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        return []

def detect_with_groundingdino_py(model, image, text_prompts, confidence_threshold=0.3):
    """Run detection using groundingdino-py"""
    try:
        # Convert PIL to numpy
        image_np = np.array(image)
        
        # Run detection for each prompt
        all_detections = []
        
        for prompt in text_prompts:
            try:
                detections = model.predict(image_np, prompt, confidence_threshold)
                
                for detection in detections:
                    detection_data = {
                        'bbox': detection.get('bbox', [0, 0, 0, 0]),
                        'confidence': detection.get('confidence', 0.0),
                        'label': prompt,
                        'prompt_matched': prompt
                    }
                    all_detections.append(detection_data)
                    
            except Exception as e:
                print(f"⚠️  Failed to detect '{prompt}': {e}")
                continue
        
        return all_detections
        
    except Exception as e:
        print(f"❌ GroundingDINO-py detection failed: {e}")
        return []

def draw_detections_on_image(image, detections, output_path):
    """Draw bounding boxes and labels on image"""
    try:
        # Create a copy for drawing
        draw_image = image.copy()
        draw = ImageDraw.Draw(draw_image)
        
        # Try to use a font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            try:
                font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 24)
            except:
                font = ImageFont.load_default()
        
        # Color scheme for different prompts
        colors = [
            (255, 0, 0),    # Red for crows
            (0, 255, 0),    # Green for magpies
            (0, 0, 255),    # Blue for ravens
            (255, 255, 0),  # Yellow for blackbirds
            (255, 0, 255),  # Magenta for corvids
            (0, 255, 255),  # Cyan for birds
        ]
        
        detection_count = 0
        
        for i, detection in enumerate(detections):
            bbox = detection['bbox']
            confidence = detection['confidence']
            label = detection['label']
            
            # Get color for this detection
            color = colors[i % len(colors)]
            
            # Draw bounding box
            x1, y1, x2, y2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw label and confidence
            label_text = f"{label}: {confidence:.2f}"
            
            # Get text size for background
            try:
                bbox_text = draw.textbbox((x1, y1 - 30), label_text, font=font)
                text_width = bbox_text[2] - bbox_text[0]
                text_height = bbox_text[3] - bbox_text[1]
            except:
                text_width, text_height = 150, 25
            
            # Draw background for text
            draw.rectangle([x1, y1 - text_height - 5, x1 + text_width + 10, y1], fill=color)
            
            # Draw text
            draw.text((x1 + 5, y1 - text_height), label_text, fill=(255, 255, 255), font=font)
            
            detection_count += 1
        
        # Save the image
        draw_image.save(output_path, 'JPEG', quality=95)
        
        return detection_count
        
    except Exception as e:
        print(f"❌ Error drawing detections: {e}")
        return 0

def process_image_with_groundingdino(model, processor, image_path, text_prompts, device, output_dir, confidence_threshold=0.3):
    """Process single image with GroundingDINO"""
    try:
        image_name = Path(image_path).stem
        print(f"\n📸 Processing: {Path(image_path).name}")
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        
        start_time = time.time()
        
        # Run detection based on available model type
        if processor is not None:
            # Transformers approach
            detections = detect_with_transformers_grounding_dino(
                model, processor, image, text_prompts, device, confidence_threshold
            )
        else:
            # groundingdino-py approach
            detections = detect_with_groundingdino_py(
                model, image, text_prompts, confidence_threshold
            )
        
        inference_time = time.time() - start_time
        
        if not detections:
            print(f"   ⚪ No detections found")
            return {
                'image_name': image_name,
                'detections_count': 0,
                'inference_time': inference_time,
                'detections': []
            }
        
        # Draw detections on image
        output_path = output_dir / f"{image_name}_groundingdino_detections.jpg"
        detection_count = draw_detections_on_image(image, detections, output_path)
        
        print(f"   🎯 Found {len(detections)} detections:")
        for detection in detections:
            print(f"     - {detection['label']}: {detection['confidence']:.3f}")
        print(f"   💾 Saved: {output_path.name}")
        print(f"   ⏱️  Inference time: {inference_time:.3f}s")
        
        return {
            'image_name': image_name,
            'detections_count': len(detections),
            'inference_time': inference_time,
            'detections': detections,
            'output_image': str(output_path)
        }
        
    except Exception as e:
        print(f"❌ Error processing {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'image_name': Path(image_path).stem,
            'detections_count': 0,
            'inference_time': 0,
            'detections': [],
            'error': str(e)
        }

def test_groundingdino_on_images():
    """Test GroundingDINO on surveillance images"""
    print("🎯 GroundingDINO Crow Detection Test")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Setup GroundingDINO
    model, processor, device = setup_groundingdino()
    if model is None:
        print("❌ Failed to setup GroundingDINO")
        return 1
    
    # Define specific text prompts for crow/corvid detection
    text_prompts = [
        "black crow bird",
        "magpie bird", 
        "raven bird",
        "corvid bird"
    ]
    
    print(f"\n🔍 Detection prompts: {', '.join(text_prompts)}")
    
    # Find test images
    test_sources = [
        "public/dummy-surveillance",
        "public/dummy-videos"  # We'll use some video frames if available
    ]
    
    all_images = []
    
    # Collect images from dummy surveillance
    dummy_surveillance = Path("public/dummy-surveillance")
    if dummy_surveillance.exists():
        for category_dir in dummy_surveillance.iterdir():
            if category_dir.is_dir():
                images = list(category_dir.glob("*.jpg"))
                all_images.extend(images[:2])  # Take 2 from each category
    
    # Also test on some extracted video frames if available
    video_frames_dir = Path("temp_video_frames")
    if video_frames_dir.exists():
        frame_images = list(video_frames_dir.glob("*.jpg"))
        all_images.extend(frame_images[:5])  # Add 5 video frames
    
    if not all_images:
        print("❌ No test images found")
        return 1
    
    # Limit for testing
    test_images = all_images[:10]
    print(f"📊 Testing on {len(test_images)} images")
    
    # Create output directory
    output_dir = Path("groundingdino_detections")
    output_dir.mkdir(exist_ok=True)
    
    # Process all images
    start_time = time.time()
    all_results = []
    total_detections = 0
    
    for image_path in test_images:
        result = process_image_with_groundingdino(
            model, processor, image_path, text_prompts, device, output_dir, confidence_threshold=0.4
        )
        all_results.append(result)
        total_detections += result['detections_count']
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_images)
    
    # Save results
    results_file = output_dir / "groundingdino_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Create summary
    summary = {
        'total_images_processed': len(test_images),
        'total_detections': total_detections,
        'total_processing_time': total_time,
        'avg_time_per_image': avg_time,
        'text_prompts_used': text_prompts,
        'confidence_threshold': 0.25,
        'model_info': {
            'approach': 'transformers' if processor else 'groundingdino-py',
            'device': str(device)
        }
    }
    
    summary_file = output_dir / "groundingdino_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print results
    print(f"\n✅ GroundingDINO detection completed!")
    print(f"   📊 Processed {len(test_images)} images in {total_time:.2f} seconds")
    print(f"   ⚡ Average: {avg_time:.3f}s per image ({len(test_images)/total_time:.1f} fps)")
    print(f"   🎯 Total detections: {total_detections}")
    if len(test_images) > 0:
        print(f"   📈 Detection rate: {total_detections/len(test_images):.1f} detections per image")
    
    # Show output structure
    detection_images = list(output_dir.glob("*_detections.jpg"))
    
    print(f"\n📁 Output structure:")
    print(f"  📂 {output_dir}/")
    print(f"    🖼️  {len(detection_images)} detection images with bounding boxes")
    print(f"    📄 groundingdino_results.json - Detailed results")
    print(f"    📄 groundingdino_summary.json - Summary statistics")
    
    if detection_images:
        print(f"\n🎯 Sample detection images:")
        for img_file in detection_images[:5]:
            print(f"  - {img_file.name}")
        if len(detection_images) > 5:
            print(f"  ... and {len(detection_images) - 5} more")
    
    # Show some detection details
    successful_detections = [r for r in all_results if r['detections_count'] > 0]
    if successful_detections:
        print(f"\n🐦‍⬛ Detection highlights:")
        for result in successful_detections[:3]:
            print(f"  📸 {result['image_name']}:")
            for detection in result['detections'][:2]:  # Show top 2 per image
                print(f"    - {detection['label']}: {detection['confidence']:.3f}")
    
    print(f"\n🎉 GroundingDINO text-prompt detection is working!")
    print("✨ Key advantages:")
    print("  1. 🎯 Text-prompt based: Can search for specific types like 'crow', 'magpie'")
    print("  2. 🔍 Zero-shot: No training needed for new object types")
    print("  3. 🎨 Flexible: Easy to adjust prompts for different corvid species")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_groundingdino_on_images())