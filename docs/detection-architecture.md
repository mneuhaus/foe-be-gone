# Detection Architecture

## Overview

Foe Be Gone uses a multi-stage detection pipeline to identify and classify animals:

1. **YOLO Stage**: Fast object detection to find animals in the image
2. **Species Identification Stage**: Detailed species classification and foe determination
3. **OpenAI Fallback**: Used only when previous stages don't detect animals

## Detection Flow

```
Camera Snapshot
    ↓
[Change Detection]
    ↓
YOLO Detection (Animals Only)
    ↓
    ├─→ No Animals → Skip or use OpenAI
    │
    └─→ Animals Found
            ↓
        Species Identification (Ollama/Qwen)
            ↓
            ├─→ Foe Identified → Trigger Deterrent
            │
            └─→ Friend/Unknown → No Action
```

## Stage Details

### 1. YOLO Detection Stage

- **Purpose**: Fast, local detection of animals in images
- **Model**: YOLOv11n (nano - fastest)
- **Function**: `detect_animals()` - filters to only return animal detections
- **Returns**: List of bounding boxes with class names (bird, cat, dog, etc.)
- **No Classification**: YOLO does NOT determine if an animal is a foe

### 2. Species Identification Stage

- **Purpose**: Precise species identification and foe classification
- **Providers**:
  - **Ollama** (default): Local, free, uses LLaVA or similar vision models
  - **Qwen**: Local, more accurate but requires loading large model
- **Function**: `identify_species()` - analyzes cropped animal regions
- **Returns**: 
  - Specific species (e.g., "European Magpie", "House Cat")
  - Foe classification (RATS, CROWS, CATS, HERONS, PIGEONS, or null)
  - Confidence scores
  - Identifying features

### 3. OpenAI Fallback

- **Purpose**: Full scene analysis when local methods fail
- **When Used**:
  - YOLO finds no animals but image changed significantly
  - Species identification is disabled
  - As configured by capture level settings
- **Cost**: $0.01-0.03 per image

## Configuration

### Environment Variables

```bash
# Enable/disable YOLO detection
YOLO_ENABLED=true
YOLO_CONFIDENCE_THRESHOLD=0.25

# Species identification provider
SPECIES_IDENTIFICATION_ENABLED=true
SPECIES_IDENTIFICATION_PROVIDER=ollama  # or "qwen"

# Ollama settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llava:13b

# Detection intervals
DETECTION_INTERVAL=10  # seconds between checks
```

### Key Benefits of New Architecture

1. **Separation of Concerns**:
   - YOLO: Fast object detection only
   - Species ID: Detailed classification and foe determination

2. **Flexibility**:
   - Easy to switch species ID providers
   - Can update foe classifications without retraining YOLO

3. **Cost Efficiency**:
   - Local processing with Ollama is free
   - OpenAI only used as fallback

4. **Accuracy**:
   - Species-specific identification instead of generic "bird" or "cat"
   - Better foe/friend distinction

## Example Detection Flow

```
1. Camera captures image of a bird
2. YOLO detects: "bird" at coordinates [100, 200, 150, 250]
3. Species ID analyzes cropped region:
   - Species: "European Magpie"
   - Foe Type: "CROWS"
   - Confidence: 0.92
4. System plays crow deterrent sound
5. Effectiveness tracked for future optimization
```