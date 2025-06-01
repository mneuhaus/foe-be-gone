#!/usr/bin/env python3
"""
GroundingDINO test script for M4 MacBook Pro
Tests GroundingDINO installation and crow detection functionality
"""

import os
import sys
import time
from pathlib import Path

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

def install_groundingdino():
    """Install GroundingDINO and its dependencies"""
    print("\n📦 Installing GroundingDINO and dependencies...")
    
    try:
        import subprocess
        
        # Install required packages
        packages = [
            "transformers",
            "accelerate",
            "torch",
            "torchvision",
            "Pillow",
            "numpy",
            "opencv-python",
            "supervision",
            "groundingdino-py"
        ]
        
        for package in packages:
            print(f"Installing {package}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to install {package}: {result.stderr}")
                return False
            else:
                print(f"✅ {package} installed successfully")
        
        print("✅ All packages installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

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
        import groundingdino
        print(f"✅ GroundingDINO imported")
        
        from groundingdino.models import build_model
        from groundingdino.util.slconfig import SLConfig
        from groundingdino.util.utils import clean_state_dict, get_phrases_from_posmap
        print("✅ GroundingDINO modules imported")
        
    except ImportError as e:
        print(f"❌ GroundingDINO import failed: {e}")
        print("Attempting to install GroundingDINO...")
        if install_groundingdino():
            try:
                import groundingdino
                from groundingdino.models import build_model
                from groundingdino.util.slconfig import SLConfig
                from groundingdino.util.utils import clean_state_dict, get_phrases_from_posmap
                print("✅ GroundingDINO imported after installation")
            except ImportError as e2:
                print(f"❌ GroundingDINO still not available: {e2}")
                return False, None
        else:
            return False, None
    
    try:
        import supervision as sv
        print(f"✅ Supervision imported")
    except ImportError:
        print("⚠️  Supervision not available, installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "supervision"], check=True)
        import supervision as sv
        print(f"✅ Supervision imported after installation")
    
    return True, device

def load_groundingdino_model(device):
    """Load GroundingDINO model"""
    print("\n📥 Loading GroundingDINO model...")
    
    try:
        from groundingdino.models import build_model
        from groundingdino.util.slconfig import SLConfig
        from groundingdino.util.utils import clean_state_dict
        import torch
        
        # GroundingDINO model configuration
        config_file = "groundingdino/config/GroundingDINO_SwinT_OGC.py"
        checkpoint_path = "groundingdino_swint_ogc.pth"
        
        # Check if we need to download the model
        if not Path(checkpoint_path).exists():
            print("📥 Downloading GroundingDINO model...")
            import urllib.request
            model_url = "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth"
            urllib.request.urlretrieve(model_url, checkpoint_path)
            print("✅ Model downloaded")
        
        # Load configuration
        print("Loading model configuration...")
        
        # Create a simple config since the file might not exist
        class SimpleConfig:
            def __init__(self):
                self.model = {
                    'type': 'GroundingDINO',
                    'backbone': {
                        'type': 'SwinTransformer',
                        'pretrain_img_size': 224,
                        'patch_size': 4,
                        'embed_dim': 96,
                        'depths': [2, 2, 6, 2],
                        'num_heads': [3, 6, 12, 24],
                        'window_size': 7,
                        'mlp_ratio': 4.0,
                        'qkv_bias': True,
                        'qk_scale': None,
                        'drop_rate': 0.0,
                        'attn_drop_rate': 0.0,
                        'drop_path_rate': 0.2,
                        'norm_layer': 'nn.LayerNorm',
                        'ape': False,
                        'patch_norm': True,
                        'out_indices': [1, 2, 3],
                        'frozen_stages': -1,
                        'use_checkpoint': False
                    }
                }
        
        start_time = time.time()
        
        # Try using groundingdino-py package instead
        try:
            from groundingdino_py import GroundingDINO
            model = GroundingDINO()
            load_time = time.time() - start_time
            print(f"✅ GroundingDINO model loaded successfully in {load_time:.2f} seconds")
            return model
        except ImportError:
            print("❌ groundingdino-py not available, trying alternative approach...")
            return None
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_transformers_approach(device):
    """Test using Transformers library approach for object detection"""
    print("\n🤖 Testing Transformers-based object detection...")
    
    try:
        from transformers import AutoProcessor, AutoModelForObjectDetection
        from PIL import Image
        import torch
        
        # Use DETR model which is similar to GroundingDINO
        print("Loading DETR model from Transformers...")
        
        start_time = time.time()
        processor = AutoProcessor.from_pretrained("facebook/detr-resnet-50")
        model = AutoModelForObjectDetection.from_pretrained("facebook/detr-resnet-50")
        
        # Move model to device
        if device.type == 'mps':
            # DETR might not support MPS, fall back to CPU
            device = torch.device('cpu')
            print("⚠️  Using CPU for DETR model (MPS compatibility)")
        
        model = model.to(device)
        model.eval()
        
        load_time = time.time() - start_time
        print(f"✅ DETR model loaded successfully in {load_time:.2f} seconds")
        
        # Test with a sample image
        test_images = []
        dummy_base_path = Path("public/dummy-surveillance")
        
        # Find a test image
        for category_dir in dummy_base_path.iterdir():
            if category_dir.is_dir():
                images = list(category_dir.glob("*.jpg"))
                if images:
                    test_images.append(images[0])
                    break
        
        if not test_images:
            print("❌ No test images found")
            return False
        
        test_image = test_images[0]
        print(f"📸 Testing with: {test_image}")
        
        # Load and process image
        image = Image.open(test_image)
        
        start_time = time.time()
        inputs = processor(images=image, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        inference_time = time.time() - start_time
        
        # Post-process outputs
        target_sizes = torch.tensor([image.size[::-1]]).to(device)
        results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.5)
        
        print(f"✅ Inference completed in {inference_time:.3f} seconds")
        
        # Print results
        result = results[0]
        boxes = result["boxes"]
        labels = result["labels"]
        scores = result["scores"]
        
        print(f"🔍 Detected {len(boxes)} objects:")
        
        # COCO class names (DETR is trained on COCO)
        coco_classes = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
            "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
            "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
            "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
            "toothbrush"
        ]
        
        bird_detections = 0
        for i in range(len(boxes)):
            label_id = labels[i].item()
            label_name = coco_classes[label_id] if label_id < len(coco_classes) else f"class_{label_id}"
            score = scores[i].item()
            box = boxes[i].tolist()
            
            print(f"  - {label_name}: {score:.3f} at {box}")
            
            if label_name == "bird":
                bird_detections += 1
        
        print(f"🐦 Found {bird_detections} bird detections")
        
        return True
        
    except Exception as e:
        print(f"❌ Transformers approach failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_yolo_approach(device):
    """Test using YOLOv8 for object detection"""
    print("\n🎯 Testing YOLOv8 object detection...")
    
    try:
        # Install ultralytics if not available
        try:
            from ultralytics import YOLO
        except ImportError:
            print("Installing ultralytics...")
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "ultralytics"], check=True)
            from ultralytics import YOLO
        
        print("Loading YOLOv8 model...")
        start_time = time.time()
        
        # Use YOLOv8 nano for faster inference
        model = YOLO('yolov8n.pt')  # This will auto-download the model
        
        load_time = time.time() - start_time
        print(f"✅ YOLOv8 model loaded successfully in {load_time:.2f} seconds")
        
        # Test with sample images
        test_images = []
        dummy_base_path = Path("public/dummy-surveillance")
        
        # Collect a few test images
        for category_dir in dummy_base_path.iterdir():
            if category_dir.is_dir():
                images = list(category_dir.glob("*.jpg"))
                if images:
                    test_images.extend(images[:2])  # Take 2 from each category
        
        if not test_images:
            print("❌ No test images found")
            return False
        
        test_images = test_images[:5]  # Limit to 5 images for testing
        print(f"📸 Testing with {len(test_images)} images")
        
        bird_detections = 0
        total_detections = 0
        total_inference_time = 0
        
        for i, test_image in enumerate(test_images, 1):
            print(f"\n🔍 Processing {i}/{len(test_images)}: {test_image.name}")
            
            start_time = time.time()
            results = model(str(test_image), conf=0.3, verbose=False)
            inference_time = time.time() - start_time
            total_inference_time += inference_time
            
            print(f"   Inference time: {inference_time:.3f}s")
            
            # Process results
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for j, box in enumerate(boxes):
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = model.names[class_id]
                        
                        total_detections += 1
                        print(f"   - {class_name}: {confidence:.3f}")
                        
                        if class_name == "bird":
                            bird_detections += 1
        
        avg_time = total_inference_time / len(test_images)
        print(f"\n✅ YOLOv8 testing completed!")
        print(f"   Total detections: {total_detections}")
        print(f"   Bird detections: {bird_detections}")
        print(f"   Average inference time: {avg_time:.3f}s per image")
        print(f"   Total time: {total_inference_time:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLOv8 approach failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_crow_detection_with_prompts():
    """Test text-prompt based detection for crows specifically"""
    print("\n🐦‍⬛ Testing crow-specific detection with text prompts...")
    
    try:
        # Try using CLIP + custom detection
        from transformers import CLIPProcessor, CLIPModel
        from PIL import Image
        import torch
        
        print("Loading CLIP model for text-guided detection...")
        
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        
        # Test prompts for crow detection
        crow_prompts = [
            "a black crow",
            "a black bird", 
            "a corvid",
            "a magpie",
            "a raven",
            "a blackbird"
        ]
        
        # Find test images
        test_images = []
        dummy_base_path = Path("public/dummy-surveillance")
        
        for category_dir in dummy_base_path.iterdir():
            if category_dir.is_dir():
                images = list(category_dir.glob("*.jpg"))
                if images:
                    test_images.extend(images[:1])  # One from each category
        
        if not test_images:
            print("❌ No test images found")
            return False
        
        test_images = test_images[:3]  # Limit for testing
        
        print(f"📸 Testing {len(test_images)} images with crow prompts...")
        
        for i, image_path in enumerate(test_images, 1):
            print(f"\n🔍 Image {i}: {image_path.name}")
            
            image = Image.open(image_path)
            
            # Process image and text
            inputs = processor(text=crow_prompts, images=image, return_tensors="pt", padding=True)
            
            with torch.no_grad():
                outputs = model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Show results
            for j, prompt in enumerate(crow_prompts):
                prob = probs[0][j].item()
                print(f"   {prompt}: {prob:.3f}")
            
            # Find highest scoring crow-related prompt
            max_idx = probs[0].argmax().item()
            max_prob = probs[0][max_idx].item()
            print(f"   🎯 Best match: '{crow_prompts[max_idx]}' ({max_prob:.3f})")
        
        print("\n✅ CLIP-based crow detection test completed!")
        return True
        
    except Exception as e:
        print(f"❌ CLIP approach failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🎯 GroundingDINO & Alternative Detection Models Test")
    print("=" * 55)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Test imports
    imports_ok, device = test_imports()
    if not imports_ok:
        return 1
    
    # Ask user what to test
    print("\nWhich detection approach would you like to test?")
    print("1. GroundingDINO (text-prompt based)")
    print("2. DETR (Transformers-based)")
    print("3. YOLOv8 (ultralytics)")
    print("4. CLIP (text-image similarity)")
    print("5. All approaches")
    
    choice = input("Enter choice (1/2/3/4/5): ").strip()
    
    success = False
    
    if choice in ['1', '5']:
        print("\n" + "="*50)
        model = load_groundingdino_model(device)
        if model:
            print("✅ GroundingDINO approach available")
            success = True
        else:
            print("❌ GroundingDINO approach failed")
    
    if choice in ['2', '5']:
        print("\n" + "="*50)
        if test_with_transformers_approach(device):
            success = True
    
    if choice in ['3', '5']:
        print("\n" + "="*50)
        if test_with_yolo_approach(device):
            success = True
    
    if choice in ['4', '5']:
        print("\n" + "="*50)
        if test_crow_detection_with_prompts():
            success = True
    
    if success:
        print("\n🎉 At least one detection approach is working!")
        print("\nNext steps:")
        print("1. Choose the best performing approach for your use case")
        print("2. YOLOv8 is generally fastest for real-time detection")
        print("3. CLIP is best for text-guided detection (specific birds)")
        print("4. DETR provides good general object detection")
    else:
        print("\n❌ All detection approaches failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())