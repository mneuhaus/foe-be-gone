"""Refactored detection worker using domain-specific services."""

import asyncio
import logging
import threading
from typing import Optional
from datetime import datetime

from app.services.camera_manager import CameraManager
from app.services.detection_processor import DetectionProcessor
from app.services.sound_player import sound_player
from app.services.video_capture import video_capture
from app.core.session import get_db_session

logger = logging.getLogger(__name__)


class DetectionWorker:
    """Background worker that coordinates detection, video capture, and deterrence."""
    
    def __init__(self, check_interval: int = 10):
        """
        Initialize the detection worker.
        
        Args:
            check_interval: Seconds between detection checks (default: 10)
        """
        self.check_interval = check_interval
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Initialize services
        self.camera_manager = CameraManager()
        self.detection_processor = DetectionProcessor()
        
    async def start(self):
        """Start the detection worker in a background thread."""
        if self.is_running:
            logger.warning("Detection worker is already running")
            return
            
        self.is_running = True
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()
        logger.info(f"Detection worker started (interval: {self.check_interval}s)")
        
    async def stop(self):
        """Stop the detection worker."""
        self.is_running = False
        
        # Clean up camera manager
        await self.camera_manager.cleanup()
        
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Detection worker stopped")
        
    def _run_in_thread(self):
        """Run the async event loop in a separate thread."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._loop = asyncio.get_event_loop()
        
        try:
            self._loop.run_until_complete(self._run())
        finally:
            self._loop.close()
            
    async def _run(self):
        """Main detection loop."""
        while self.is_running:
            try:
                await self._check_all_cameras()
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                
            # Wait for next check
            await asyncio.sleep(self.check_interval)
            
    async def _check_all_cameras(self):
        """Check all active cameras for foes."""
        cameras = self.camera_manager.get_active_cameras()
        
        if not cameras:
            logger.debug("No active cameras to check")
            return
            
        logger.debug(f"Checking {len(cameras)} cameras")
        
        # Check cameras concurrently
        tasks = [self._check_camera(camera) for camera in cameras]
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _check_camera(self, camera):
        """Check a single camera for foes."""
        try:
            logger.debug(f"Checking camera: {camera.name}")
            
            # Capture snapshot
            snapshot_data = await self.camera_manager.capture_snapshot(camera)
            if not snapshot_data:
                logger.warning(f"Failed to capture snapshot from {camera.name}")
                return
                
            # Process snapshot for detection
            detection = await self.detection_processor.process_snapshot(camera, snapshot_data)
            
            if not detection:
                return
                
            # Get primary foe type
            foe_type = self.detection_processor.get_primary_foe_type(detection)
            if not foe_type:
                return
                
            logger.info(f"Detected {foe_type} on {camera.name} - starting response")
            
            # Start video capture (non-blocking)
            video_task = None
            rtsp_url = video_capture.get_rtsp_url(camera.device_metadata)
            if rtsp_url and video_capture.check_ffmpeg_available():
                video_task = asyncio.create_task(
                    video_capture.capture_video(
                        rtsp_url=rtsp_url,
                        camera_name=camera.name,
                        duration=15,  # 15 seconds
                        detection_id=detection.id
                    )
                )
                logger.info(f"Started video capture for detection {detection.id}")
            else:
                logger.warning(f"Video capture not available for {camera.name}")
            
            # Play deterrent sound
            played_sounds = []
            
            # Try to play on camera first
            sound_files = sound_player.get_available_sounds(foe_type)
            if sound_files:
                selected_sound = sound_player._select_random_sound(sound_files)
                camera_success = await self.camera_manager.play_sound_on_camera(camera, selected_sound)
                
                if camera_success:
                    played_sounds.append(f"camera:{selected_sound.name}")
                    self.detection_processor.record_deterrent_action(
                        detection.id,
                        f"sound_camera_{foe_type}",
                        True,
                        f"Played {selected_sound.name} on camera"
                    )
                else:
                    # Fall back to local playback
                    local_success = sound_player.play_sound(selected_sound)
                    if local_success:
                        played_sounds.append(f"local:{selected_sound.name}")
                        self.detection_processor.record_deterrent_action(
                            detection.id,
                            f"sound_local_{foe_type}",
                            True,
                            f"Played {selected_sound.name} locally"
                        )
            
            # Wait for video capture to complete
            if video_task:
                video_path = await video_task
                if video_path:
                    # Update detection with video path
                    with get_db_session() as session:
                        detection_db = session.get(Detection, detection.id)
                        if detection_db:
                            detection_db.video_path = str(video_path)
                            detection_db.played_sounds = played_sounds
                            session.commit()
                    logger.info(f"Video capture completed: {video_path}")
                else:
                    logger.warning("Video capture failed")
                    
        except Exception as e:
            logger.error(f"Error checking camera {camera.name}: {e}")


# Import Detection model here to avoid circular import
from app.models.detection import Detection

# Global detection worker instance
detection_worker = DetectionWorker()