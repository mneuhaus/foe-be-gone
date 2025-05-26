"""Sound playback service for foe deterrence."""
import os
import random
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SoundPlayer:
    """Service for playing deterrent sounds when foes are detected."""
    
    def __init__(self, sounds_dir: str = "public/sounds"):
        """Initialize the sound player."""
        self.sounds_dir = Path(sounds_dir)
        
    def get_available_sounds(self, foe_type: str) -> List[Path]:
        """Get list of available sound files for a foe type."""
        foe_dir = self.sounds_dir / foe_type
        
        if not foe_dir.exists():
            logger.warning(f"Sound directory not found: {foe_dir}")
            return []
            
        # Find all audio files
        sound_files = []
        for ext in ['*.mp3', '*.wav']:
            sound_files.extend(foe_dir.glob(ext))
            
        # Filter out incomplete downloads
        sound_files = [f for f in sound_files if not f.name.endswith('.crdownload')]
        
        return sound_files
    
    def _select_random_sound(self, available_sounds: List[Path]) -> Path:
        """Select a random sound from a list of available sounds."""
        return random.choice(available_sounds)
    
    def play_random_sound(self, foe_type: str) -> bool:
        """Play a random deterrent sound for the detected foe type."""
        available_sounds = self.get_available_sounds(foe_type)
        
        if not available_sounds:
            logger.warning(f"No sounds available for foe type: {foe_type}")
            return False
            
        # Pick a random sound
        selected_sound = self._select_random_sound(available_sounds)
        
        return self.play_sound(selected_sound)
    
    def play_sound(self, sound_path: Path) -> bool:
        """Play a specific sound file."""
        try:
            if not sound_path.exists():
                logger.error(f"Sound file not found: {sound_path}")
                return False
                
            logger.info(f"Playing deterrent sound: {sound_path.name}")
            
            # Use system audio player based on OS
            if os.name == 'nt':  # Windows
                # Use Windows Media Player
                subprocess.run(['start', str(sound_path)], shell=True, check=True)
            elif os.name == 'posix':  # macOS/Linux
                # Try different audio players
                if self._command_exists('afplay'):  # macOS
                    subprocess.run(['afplay', str(sound_path)], check=True)
                elif self._command_exists('paplay'):  # Linux (PulseAudio)
                    subprocess.run(['paplay', str(sound_path)], check=True)
                elif self._command_exists('aplay'):  # Linux (ALSA)
                    subprocess.run(['aplay', str(sound_path)], check=True)
                elif self._command_exists('mpg123'):  # Cross-platform
                    subprocess.run(['mpg123', str(sound_path)], check=True)
                else:
                    logger.error("No suitable audio player found")
                    return False
            else:
                logger.error(f"Unsupported operating system: {os.name}")
                return False
                
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to play sound {sound_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error playing sound {sound_path}: {e}")
            return False
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH."""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def list_sounds_by_type(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of available sounds by foe type."""
        summary: Dict[str, Dict[str, Any]] = {}
        
        for foe_dir in self.sounds_dir.iterdir():
            if foe_dir.is_dir() and not foe_dir.name.startswith('.'):
                sounds = self.get_available_sounds(foe_dir.name)
                summary[foe_dir.name] = {
                    'count': len(sounds),
                    'files': [s.name for s in sounds]
                }
                
        return summary


# Global sound player instance
sound_player = SoundPlayer()