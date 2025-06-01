#!/usr/bin/env python3
"""
Animal Species Classification using EfficientNet-B0
Classifies the animal crops extracted by MegaDetector
"""

import os
import sys
import time
import json
from pathlib import Path
import torch
import torchvision.transforms as transforms
from PIL import Image
import numpy as np

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
        import torchvision
        print(f"✅ Torchvision {torchvision.__version__}")
        
        from torchvision import models
        print("✅ Torchvision models imported")
        
    except ImportError as e:
        print(f"❌ Torchvision import failed: {e}")
        return False, None
    
    return True, device

def load_efficientnet_b0(device):
    """Load pre-trained EfficientNet-B0 model"""
    print("\n📥 Loading EfficientNet-B0 model...")
    
    try:
        from torchvision import models
        
        # Load pre-trained EfficientNet-B0
        start_time = time.time()
        model = models.efficientnet_b0(pretrained=True)
        model.eval()
        model = model.to(device)
        load_time = time.time() - start_time
        
        print(f"✅ EfficientNet-B0 loaded successfully in {load_time:.2f} seconds")
        print(f"   Model device: {next(model.parameters()).device}")
        print(f"   Total parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        return model
        
    except Exception as e:
        print(f"❌ EfficientNet-B0 loading failed: {e}")
        return None

def get_imagenet_classes():
    """Get ImageNet class labels"""
    # This is a subset of ImageNet classes that are relevant to wildlife/animals
    # EfficientNet-B0 was trained on ImageNet which has 1000 classes
    # We'll return the top predictions and map them to common animal names
    
    imagenet_classes = {
        # Birds
        7: "cock", 8: "hen", 9: "ostrich", 10: "brambling", 11: "goldfinch", 12: "house_finch",
        13: "junco", 14: "indigo_bunting", 15: "robin", 16: "bulbul", 17: "jay", 18: "magpie",
        19: "chickadee", 20: "water_ouzel", 21: "kite", 22: "bald_eagle", 23: "vulture",
        24: "great_grey_owl", 80: "black_grouse", 81: "ptarmigan", 82: "ruffed_grouse",
        83: "prairie_chicken", 84: "peacock", 85: "quail", 86: "partridge", 87: "african_grey",
        88: "macaw", 89: "sulphur-crested_cockatoo", 90: "lorikeet", 91: "coucal", 92: "bee_eater",
        93: "hornbill", 94: "hummingbird", 95: "jacamar", 96: "toucan", 97: "drake",
        98: "red-breasted_merganser", 99: "goose", 100: "black_swan", 127: "white_stork",
        128: "black_stork", 129: "spoonbill", 130: "flamingo", 131: "little_blue_heron",
        132: "american_egret", 133: "bittern", 134: "crane", 135: "limpkin", 136: "european_gallinule",
        137: "american_coot", 138: "bustard", 139: "ruddy_turnstone", 140: "red-backed_sandpiper",
        141: "redshank", 142: "dowitcher", 143: "oystercatcher", 144: "pelican", 145: "king_penguin",
        
        # Mammals - cats/felines
        281: "tabby", 282: "tiger_cat", 283: "persian_cat", 284: "siamese_cat", 285: "egyptian_cat",
        286: "cougar", 287: "lynx", 288: "leopard", 289: "snow_leopard", 290: "jaguar", 291: "lion",
        292: "tiger", 293: "cheetah",
        
        # Mammals - dogs/canines
        151: "chihuahua", 152: "japanese_spaniel", 153: "maltese_dog", 154: "pekinese",
        155: "shih-tzu", 156: "blenheim_spaniel", 157: "papillon", 158: "toy_terrier",
        159: "rhodesian_ridgeback", 160: "afghan_hound", 161: "basset", 162: "beagle",
        163: "bloodhound", 164: "bluetick", 165: "black-and-tan_coonhound", 166: "walker_hound",
        167: "english_foxhound", 168: "redbone", 169: "borzoi", 170: "irish_wolfhound",
        171: "italian_greyhound", 172: "whippet", 173: "ibizan_hound", 174: "norwegian_elkhound",
        175: "otterhound", 176: "saluki", 177: "scottish_deerhound", 178: "weimaraner",
        179: "staffordshire_bullterrier", 180: "american_staffordshire_terrier", 181: "bedlington_terrier",
        182: "border_terrier", 183: "kerry_blue_terrier", 184: "irish_terrier", 185: "norfolk_terrier",
        186: "norwich_terrier", 187: "yorkshire_terrier", 188: "wire-haired_fox_terrier",
        189: "lakeland_terrier", 190: "sealyham_terrier", 191: "airedale", 192: "cairn",
        193: "australian_terrier", 194: "dandie_dinmont", 195: "boston_bull", 196: "miniature_schnauzer",
        197: "giant_schnauzer", 198: "standard_schnauzer", 199: "scotch_terrier", 200: "tibetan_terrier",
        201: "silky_terrier", 202: "soft-coated_wheaten_terrier", 203: "west_highland_white_terrier",
        204: "lhasa", 205: "flat-coated_retriever", 206: "curly-coated_retriever", 207: "golden_retriever",
        208: "labrador_retriever", 209: "chesapeake_bay_retriever", 210: "german_short-haired_pointer",
        211: "vizsla", 212: "english_setter", 213: "irish_setter", 214: "gordon_setter",
        215: "brittany_spaniel", 216: "clumber", 217: "english_springer", 218: "welsh_springer_spaniel",
        219: "cocker_spaniel", 220: "sussex_spaniel", 221: "irish_water_spaniel", 222: "kuvasz",
        223: "schipperke", 224: "groenendael", 225: "malinois", 226: "briard", 227: "kelpie",
        228: "komondor", 229: "old_english_sheepdog", 230: "shetland_sheepdog", 231: "collie",
        232: "border_collie", 233: "bouvier_des_flandres", 234: "rottweiler", 235: "german_shepherd",
        236: "doberman", 237: "miniature_pinscher", 238: "greater_swiss_mountain_dog",
        239: "bernese_mountain_dog", 240: "appenzeller", 241: "entlebucher", 242: "boxer",
        243: "bull_mastiff", 244: "tibetan_mastiff", 245: "french_bulldog", 246: "great_dane",
        247: "saint_bernard", 248: "eskimo_dog", 249: "malamute", 250: "siberian_husky",
        251: "dalmatian", 252: "affenpinscher", 253: "basenji", 254: "pug", 255: "leonberg",
        256: "newfoundland", 257: "great_pyrenees", 258: "samoyed", 259: "pomeranian",
        260: "chow", 261: "keeshond", 262: "brabancon_griffon", 263: "pembroke", 264: "cardigan",
        265: "toy_poodle", 266: "miniature_poodle", 267: "standard_poodle", 268: "mexican_hairless",
        269: "timber_wolf", 270: "white_wolf", 271: "red_wolf", 272: "coyote", 273: "dingo",
        274: "dhole", 275: "african_hunting_dog",
        
        # Other mammals
        276: "hyena", 277: "red_fox", 278: "kit_fox", 279: "arctic_fox", 280: "grey_fox",
        294: "brown_bear", 295: "american_black_bear", 296: "ice_bear", 297: "sloth_bear",
        298: "mongoose", 299: "meerkat", 300: "tiger_beetle", 301: "ladybug", 302: "ground_beetle",
        303: "long-horned_beetle", 304: "leaf_beetle", 305: "dung_beetle", 306: "rhinoceros_beetle",
        307: "weevil", 308: "fly", 309: "bee", 310: "ant", 311: "grasshopper", 312: "cricket",
        313: "walking_stick", 314: "cockroach", 315: "mantis", 316: "cicada", 317: "leafhopper",
        318: "lacewing", 319: "dragonfly", 320: "damselfly", 321: "admiral", 322: "ringlet",
        323: "monarch", 324: "cabbage_butterfly", 325: "sulphur_butterfly", 326: "lycaenid",
        327: "starfish", 328: "sea_urchin", 329: "sea_cucumber", 330: "wood_rabbit",
        331: "hare", 332: "angora", 333: "hamster", 334: "porcupine", 335: "fox_squirrel",
        336: "marmot", 337: "beaver", 338: "guinea_pig", 339: "sorrel", 340: "zebra",
        341: "hog", 342: "wild_boar", 343: "warthog", 344: "hippopotamus", 345: "ox",
        346: "water_buffalo", 347: "bison", 348: "ram", 349: "bighorn", 350: "ibex",
        351: "hartebeest", 352: "impala", 353: "gazelle", 354: "arabian_camel", 355: "llama",
        356: "weasel", 357: "mink", 358: "polecat", 359: "black-footed_ferret", 360: "otter",
        361: "skunk", 362: "badger", 363: "armadillo", 364: "three-toed_sloth", 365: "orangutan",
        366: "gorilla", 367: "chimpanzee", 368: "gibbon", 369: "siamang", 370: "guenon",
        371: "patas", 372: "baboon", 373: "macaque", 374: "langur", 375: "colobus",
        376: "proboscis_monkey", 377: "marmoset", 378: "capuchin", 379: "howler_monkey",
        380: "titi", 381: "spider_monkey", 382: "squirrel_monkey", 383: "madagascar_cat",
        384: "indri", 385: "indian_elephant", 386: "african_elephant", 387: "lesser_panda",
        388: "giant_panda", 389: "barracouta", 390: "eel", 391: "coho", 392: "rock_beauty",
        393: "anemone_fish", 394: "sturgeon", 395: "gar", 396: "lionfish", 397: "puffer",
        398: "abacus", 399: "abaya"
    }
    
    return imagenet_classes

def get_animal_group(class_name, class_id):
    """Map ImageNet class to broader animal groups relevant to wildlife surveillance"""
    class_name = class_name.lower()
    
    # Birds (corvids and related)
    if any(bird in class_name for bird in ['crow', 'raven', 'magpie', 'jay', 'jackdaw']):
        return "corvid"
    elif any(bird in class_name for bird in ['robin', 'finch', 'bunting', 'chickadee', 'sparrow']):
        return "small_bird"
    elif any(bird in class_name for bird in ['hawk', 'eagle', 'vulture', 'owl', 'kite']):
        return "raptor"
    elif any(bird in class_name for bird in ['duck', 'goose', 'swan', 'drake']):
        return "waterfowl"
    elif class_id in range(7, 146):  # Most birds in ImageNet are in this range
        return "bird"
    
    # Mammals - cats
    elif any(cat in class_name for cat in ['cat', 'cougar', 'lynx', 'leopard', 'jaguar', 'lion', 'tiger', 'cheetah']):
        return "feline"
    
    # Mammals - dogs/canines
    elif any(dog in class_name for dog in ['dog', 'wolf', 'coyote', 'fox', 'dingo']):
        return "canine"
    
    # Rodents
    elif any(rodent in class_name for rodent in ['squirrel', 'rabbit', 'hare', 'hamster', 'guinea_pig', 'beaver']):
        return "rodent"
    
    # Large mammals
    elif any(large in class_name for large in ['bear', 'deer', 'elk', 'moose', 'bison', 'buffalo']):
        return "large_mammal"
    
    # Small mammals
    elif any(small in class_name for small in ['weasel', 'mink', 'ferret', 'otter', 'skunk', 'badger']):
        return "small_mammal"
    
    # Default classification
    elif class_id in range(7, 146):
        return "bird"
    elif class_id in range(151, 398):
        return "mammal"
    else:
        return "unknown"

def classify_image(model, image_path, device, top_k=5):
    """Classify a single image using EfficientNet-B0"""
    try:
        # Define transforms for EfficientNet-B0 (ImageNet preprocessing)
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        input_tensor = transform(image).unsqueeze(0).to(device)
        
        # Run inference
        with torch.no_grad():
            outputs = model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            
        # Get top predictions
        top_probs, top_indices = torch.topk(probabilities, top_k)
        
        # Get class names
        imagenet_classes = get_imagenet_classes()
        
        predictions = []
        for i in range(top_k):
            class_id = top_indices[i].item()
            confidence = top_probs[i].item()
            class_name = imagenet_classes.get(class_id, f"class_{class_id}")
            animal_group = get_animal_group(class_name, class_id)
            
            predictions.append({
                'rank': i + 1,
                'class_id': class_id,
                'class_name': class_name,
                'animal_group': animal_group,
                'confidence': confidence
            })
        
        return predictions
        
    except Exception as e:
        print(f"❌ Error classifying {image_path}: {e}")
        return []

def classify_animal_crops(crops_directory, device, output_dir):
    """Classify all animal crops using EfficientNet-B0"""
    print(f"\n🔍 Starting animal species classification...")
    
    # Load EfficientNet-B0
    model = load_efficientnet_b0(device)
    if model is None:
        return False
    
    # Find all animal crop images
    crops_dir = Path(crops_directory)
    if not crops_dir.exists():
        print(f"❌ Crops directory not found: {crops_dir}")
        return False
    
    # Look for animal crops in subdirectory
    animal_crops_dir = crops_dir / "animal_crops"
    if animal_crops_dir.exists():
        crops_dir = animal_crops_dir
    
    crop_files = list(crops_dir.glob("*.jpg"))
    
    if not crop_files:
        print(f"❌ No animal crop images found in {crops_dir}")
        return False
    
    print(f"📊 Found {len(crop_files)} animal crops to classify")
    
    try:
        # Create output directory for classification results
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        classification_results = {}
        group_counts = {}
        
        start_time = time.time()
        
        for i, crop_file in enumerate(crop_files, 1):
            print(f"🔍 Classifying {i}/{len(crop_files)}: {crop_file.name}")
            
            # Classify the image
            predictions = classify_image(model, crop_file, device, top_k=5)
            
            if predictions:
                top_prediction = predictions[0]
                animal_group = top_prediction['animal_group']
                
                # Count animal groups
                group_counts[animal_group] = group_counts.get(animal_group, 0) + 1
                
                # Store results
                classification_results[crop_file.name] = {
                    'file_path': str(crop_file),
                    'predictions': predictions,
                    'top_class': top_prediction['class_name'],
                    'top_confidence': top_prediction['confidence'],
                    'animal_group': animal_group
                }
                
                print(f"  🎯 Top prediction: {top_prediction['class_name']} ({animal_group}) - {top_prediction['confidence']:.3f}")
                other_preds = ', '.join([f"{p['class_name']} ({p['confidence']:.3f})" for p in predictions[1:3]])
                print(f"     Other: {other_preds}")
            else:
                print(f"  ❌ Classification failed")
        
        total_time = time.time() - start_time
        avg_time = total_time / len(crop_files)
        
        print(f"\n✅ Classification completed!")
        print(f"   Total time: {total_time:.2f} seconds")
        print(f"   Average per image: {avg_time:.3f} seconds")
        print(f"   Images per second: {len(crop_files)/total_time:.2f}")
        
        # Save classification results
        results_file = output_path / "classification_results.json"
        with open(results_file, 'w') as f:
            json.dump(classification_results, f, indent=2)
        
        # Create summary
        summary = {
            'total_images_classified': len(crop_files),
            'processing_time': total_time,
            'avg_time_per_image': avg_time,
            'animal_group_counts': group_counts,
            'model_info': {
                'model': 'EfficientNet-B0',
                'pretrained': 'ImageNet',
                'device': str(device),
                'top_k_predictions': 5
            }
        }
        
        summary_file = output_path / "classification_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print(f"\n📊 Animal Group Distribution:")
        for group, count in sorted(group_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(crop_files)) * 100
            print(f"  {group}: {count} images ({percentage:.1f}%)")
        
        print(f"\n📁 Output files:")
        print(f"  📄 {results_file} - Detailed classification results")
        print(f"  📄 {summary_file} - Summary statistics")
        
        # Group results by animal type
        grouped_results = {}
        for filename, result in classification_results.items():
            group = result['animal_group']
            if group not in grouped_results:
                grouped_results[group] = []
            grouped_results[group].append({
                'filename': filename,
                'class': result['top_class'],
                'confidence': result['top_confidence']
            })
        
        # Show sample results for each group
        print(f"\n🦌 Sample Classifications by Group:")
        for group, items in sorted(grouped_results.items()):
            print(f"\n  {group.upper()} ({len(items)} images):")
            for item in sorted(items, key=lambda x: x['confidence'], reverse=True)[:3]:
                print(f"    - {item['filename']}: {item['class']} ({item['confidence']:.3f})")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main classification function"""
    print("🧠 Animal Species Classification with EfficientNet-B0")
    print("=" * 55)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Test imports
    imports_ok, device = test_imports()
    if not imports_ok:
        return 1
    
    # Look for existing animal crops
    possible_dirs = [
        "megadetector_video_extraction",
        "megadetector_animal_extraction"
    ]
    
    crops_dir = None
    for dir_name in possible_dirs:
        if Path(dir_name).exists():
            # Check if it has animal_crops subdirectory
            animal_crops_path = Path(dir_name) / "animal_crops"
            if animal_crops_path.exists() and list(animal_crops_path.glob("*.jpg")):
                crops_dir = dir_name
                print(f"✅ Found animal crops in: {dir_name}")
                break
    
    if not crops_dir:
        print("❌ No animal crops found!")
        print("Please run the MegaDetector test script first to extract animal crops:")
        print("python test_megadetector.py")
        return 1
    
    # Create output directory
    output_dir = f"{crops_dir}_classification"
    
    print(f"📂 Input directory: {crops_dir}")
    print(f"📂 Output directory: {output_dir}")
    
    # Run classification
    success = classify_animal_crops(crops_dir, device, output_dir)
    
    if success:
        print("\n🎉 Classification completed successfully!")
        print("\nNext steps:")
        print("1. Review the classification results in the output directory")
        print("2. The classifications can help identify corvids vs other species")
        print("3. Integrate these results into your crow deterrent system")
    else:
        print("\n❌ Classification failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())