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
from app.services.effectiveness_tracker import effectiveness_tracker
from app.core.session import get_db_session
from app.core.config import config

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
            
            # Store detection ID immediately while object is still attached
            detection_id = detection.id
            if not detection_id:
                return
                
            # Get primary foe type using the ID
            foe_type = self.detection_processor.get_primary_foe_type(detection_id)
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
                        duration=config.VIDEO_CAPTURE_DURATION,
                        detection_id=detection_id
                    )
                )
                logger.info(f"Started video capture for detection {detection_id}")
            else:
                logger.warning(f"Video capture not available for {camera.name}")
            
            # Store initial foe data for effectiveness tracking - get from fresh session
            initial_foes = []
            with get_db_session() as foe_session:
                fresh_detection = foe_session.get(Detection, detection_id)
                if fresh_detection and fresh_detection.foes:
                    initial_foes = [foe for foe in fresh_detection.foes]
            
            # Play deterrent sound
            played_sounds = []
            selected_sound_file = None
            
            # Try to play on camera first
            sound_files = sound_player.get_available_sounds(foe_type)
            if sound_files:
                import random
                
                # 50% chance to explore new sounds vs exploit best known
                use_best_sound = random.random() < 0.5
                
                if use_best_sound:
                    # Try to use the most effective sound based on statistics
                    best_sound_name = effectiveness_tracker.get_best_sound_for_foe(
                        foe_type, 
                        hour=datetime.now().hour
                    )
                    
                    if best_sound_name:
                        # Find the best sound in available files
                        selected_sound = next(
                            (f for f in sound_files if f.name == best_sound_name),
                            None
                        )
                        if selected_sound:
                            logger.info(f"Using statistically best sound: {best_sound_name}")
                        else:
                            # Fall back to random if best not available
                            selected_sound = sound_player._select_random_sound(sound_files)
                            logger.info(f"Best sound not available, using random: {selected_sound.name}")
                    else:
                        # No statistics yet, use random
                        selected_sound = sound_player._select_random_sound(sound_files)
                        logger.info(f"No statistics yet, using random: {selected_sound.name}")
                else:
                    # Exploration: prefer least-tested sounds
                    sound_names = [f.name for f in sound_files]
                    least_tested = effectiveness_tracker.get_least_tested_sound(foe_type, sound_names)
                    
                    if least_tested:
                        selected_sound = next(
                            (f for f in sound_files if f.name == least_tested),
                            None
                        )
                        if selected_sound:
                            logger.info(f"Exploring least-tested sound: {selected_sound.name}")
                        else:
                            selected_sound = sound_player._select_random_sound(sound_files)
                            logger.info(f"Fallback to random exploration: {selected_sound.name}")
                    else:
                        # Fallback to pure random
                        selected_sound = sound_player._select_random_sound(sound_files)
                        logger.info(f"Random exploration (no usage data): {selected_sound.name}")
                
                selected_sound_file = selected_sound.name
                camera_success = await self.camera_manager.play_sound_on_camera(camera, selected_sound)
                
                playback_method = None
                if camera_success:
                    played_sounds.append(f"camera:{selected_sound.name}")
                    playback_method = "camera"
                    self.detection_processor.record_deterrent_action(
                        detection_id,
                        f"sound_camera_{foe_type}",
                        True,
                        f"Played {selected_sound.name} on camera"
                    )
                else:
                    # Fall back to local playback
                    local_success = sound_player.play_sound(selected_sound)
                    if local_success:
                        played_sounds.append(f"local:{selected_sound.name}")
                        playback_method = "local"
                        self.detection_processor.record_deterrent_action(
                            detection_id,
                            f"sound_local_{foe_type}",
                            True,
                            f"Played {selected_sound.name} locally"
                        )
            
            # Wait for deterrent to take effect
            if selected_sound_file and playback_method:
                # Cap sound playback at 10 seconds max
                sound_duration = 10  # Maximum 10 seconds for any sound
                logger.info(f"Playing sound for up to {sound_duration} seconds...")
                
                # If playing on camera, the sound plays asynchronously
                # For local playback, we need to wait for it to finish
                if playback_method == "local":
                    # Local playback is synchronous, so it's already done
                    pass
                else:
                    # Camera playback might be async, wait for sound duration
                    await asyncio.sleep(sound_duration)
                
                # Sound finished, check effectiveness immediately
                logger.info(f"Sound finished. Checking deterrent effectiveness now...")
                
                # Take follow-up snapshot
                logger.info(f"Taking follow-up snapshot to check effectiveness")
                follow_up_snapshot = await self.camera_manager.capture_snapshot(camera)
                
                if follow_up_snapshot:
                    # Save follow-up snapshot
                    follow_up_path = self.detection_processor.save_snapshot(
                        follow_up_snapshot, 
                        f"{camera.name}_followup"
                    )
                    
                    # Run AI detection on follow-up snapshot
                    follow_up_result = self.detection_processor.ai_detector.detect_foes(follow_up_snapshot)
                    
                    # Record effectiveness
                    effectiveness_tracker.record_effectiveness(
                        detection_id=detection_id,
                        foe_type=foe_type,
                        sound_file=selected_sound_file,
                        playback_method=playback_method,
                        foes_before=initial_foes,
                        foes_after=follow_up_result.foes if follow_up_result.foes_detected else [],
                        follow_up_image_path=str(follow_up_path),
                        wait_duration=sound_duration  # Just the sound duration
                    )
                    
                    # Log result
                    if not follow_up_result.foes_detected:
                        logger.info(f"SUCCESS: {foe_type} deterred by {selected_sound_file}!")
                    elif len(follow_up_result.foes) < len(initial_foes):
                        logger.info(f"PARTIAL: Reduced {foe_type} count with {selected_sound_file}")
                    else:
                        logger.warning(f"FAILURE: {selected_sound_file} did not deter {foe_type}")
            
            # Wait for video capture to complete
            if video_task:
                video_path = await video_task
                if video_path:
                    # Update detection with video path
                    with get_db_session() as session:
                        detection_db = session.get(Detection, detection_id)
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