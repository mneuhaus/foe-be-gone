"""Video capture service for recording camera streams during detections."""

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

from app.core.config import config

logger = logging.getLogger(__name__)


class VideoCapture:
    """Captures video from RTSP streams using ffmpeg."""
    
    def __init__(self):
        """Initialize the video capture service."""
        self.video_dir = Path("data/videos")
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
    async def capture_video(
        self, 
        rtsp_url: str, 
        camera_name: str,
        duration: int = config.VIDEO_CAPTURE_DURATION,
        detection_id: Optional[int] = None
    ) -> Optional[Path]:
        """
        Capture video from an RTSP stream.
        
        Args:
            rtsp_url: RTSP URL of the camera stream
            camera_name: Name of the camera (for filename)
            duration: Duration to record in seconds (default: from config)
            detection_id: Optional detection ID to link video to
            
        Returns:
            Path to the saved video file, or None if capture failed
        """
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detection_suffix = f"_det{detection_id}" if detection_id else ""
        filename = f"{camera_name}_{timestamp}{detection_suffix}_{uuid.uuid4().hex[:8]}.mp4"
        filepath = self.video_dir / filename
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",  # Use TCP for more reliable RTSP
            "-i", rtsp_url,            # Input RTSP stream
            "-t", str(duration),       # Duration
            "-c:v", "copy",           # Copy video codec (no re-encoding)
            "-c:a", "copy",           # Copy audio codec if present
            "-movflags", "frag_keyframe+empty_moov",  # Allow streaming write
            "-y",                     # Overwrite output file
            str(filepath)
        ]
        
        logger.info(f"Starting video capture from {camera_name} for {duration}s")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        try:
            # Run ffmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=duration + 10  # Add buffer for ffmpeg startup/shutdown
                )
                
                if process.returncode == 0:
                    logger.info(f"Video captured successfully: {filepath}")
                    return filepath
                else:
                    logger.error(f"FFmpeg failed with return code {process.returncode}")
                    logger.error(f"FFmpeg stderr: {stderr.decode()}")
                    return None
                    
            except asyncio.TimeoutError:
                logger.error(f"Video capture timed out after {duration + 10}s")
                process.kill()
                await process.communicate()  # Clean up
                return None
                
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install ffmpeg to enable video capture.")
            return None
        except Exception as e:
            logger.error(f"Error capturing video: {e}")
            return None
    
    def check_ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available on the system."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_rtsp_url(self, camera_metadata: dict) -> Optional[str]:
        """
        Extract RTSP URL from camera metadata.
        
        Args:
            camera_metadata: Camera device metadata
            
        Returns:
            RTSP URL if available, None otherwise
        """
        # Try different possible keys for RTSP URL
        rtsp_keys = ["rtsp_url", "rtspUrl", "stream_url", "streamUrl"]
        
        for key in rtsp_keys:
            if key in camera_metadata:
                return camera_metadata[key]
        
        # Try to construct from UniFi Protect metadata
        if all(k in camera_metadata for k in ["host", "camera_id"]):
            # UniFi Protect RTSP URL format
            host = camera_metadata["host"]
            camera_id = camera_metadata["camera_id"]
            # Default to high quality stream
            return f"rtsp://{host}:{config.RTSP_PORT}/{camera_id}"
        
        return None
    
    async def cleanup_old_videos(self, retention_days: int = 7):
        """Clean up video files older than retention period."""
        try:
            cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
            
            for video_file in self.video_dir.glob("*.mp4"):
                if video_file.stat().st_mtime < cutoff_date:
                    video_file.unlink()
                    logger.info(f"Deleted old video: {video_file}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old videos: {e}")


# Global video capture instance
video_capture = VideoCapture()