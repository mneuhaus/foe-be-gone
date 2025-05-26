"""Background worker for periodic detection checks.

This module has been refactored into domain-specific services.
The DetectionWorker is now a thin coordinator that uses:
- CameraManager: For camera device management
- DetectionProcessor: For AI detection and image analysis
- VideoCapture: For recording video during detections
- SoundPlayer: For deterrent sound playback
"""

# Import the refactored detection worker
from app.services.detection_worker_new import detection_worker

# For backward compatibility, expose the same interface
__all__ = ['detection_worker']