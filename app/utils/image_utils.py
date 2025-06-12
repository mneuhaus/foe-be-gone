"""Image utility functions."""

import hashlib
import os
from pathlib import Path
from PIL import Image
from typing import Tuple, Optional


def crop_image_with_padding(image: Image.Image, bbox: Tuple[int, int, int, int], 
                           padding_percent: float = 0.5) -> Image.Image:
    """
    Crop an image with padding around a bounding box.
    
    Args:
        image: PIL Image to crop
        bbox: Bounding box as (x1, y1, x2, y2)
        padding_percent: Padding to add as percentage of bbox size (0.5 = 50%)
        
    Returns:
        Cropped PIL Image
    """
    x1, y1, x2, y2 = bbox
    
    # Calculate padding
    width = x2 - x1
    height = y2 - y1
    padding_x = int(width * padding_percent)
    padding_y = int(height * padding_percent)
    
    # Apply padding with bounds checking
    padded_x1 = max(0, x1 - padding_x)
    padded_y1 = max(0, y1 - padding_y)
    padded_x2 = min(image.width, x2 + padding_x)
    padded_y2 = min(image.height, y2 + padding_y)
    
    # Crop the image
    return image.crop((padded_x1, padded_y1, padded_x2, padded_y2))


def resize_image_smart(image: Image.Image, max_width: int, max_height: int, 
                      quality: int = 85, maintain_aspect: bool = True) -> Image.Image:
    """
    Resize an image intelligently with various options.
    
    Args:
        image: PIL Image to resize
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (10-100)
        maintain_aspect: Whether to maintain aspect ratio
        
    Returns:
        Resized PIL Image
    """
    original_width, original_height = image.size
    
    if maintain_aspect:
        # Calculate resize ratio maintaining aspect ratio
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        resize_ratio = min(width_ratio, height_ratio)
        
        # Don't upscale if image is already smaller
        if resize_ratio >= 1.0:
            return image
            
        new_width = int(original_width * resize_ratio)
        new_height = int(original_height * resize_ratio)
    else:
        new_width = min(max_width, original_width)
        new_height = min(max_height, original_height)
    
    # Use high-quality resampling
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def get_cache_path(original_path: str, width: int, height: int, quality: int = 85) -> Path:
    """
    Generate a cache file path for a resized image.
    
    Args:
        original_path: Path to original image
        width: Target width
        height: Target height
        quality: JPEG quality
        
    Returns:
        Path to cached resized image
    """
    # Create a hash of the original file path and resize parameters
    cache_key = f"{original_path}_{width}x{height}_q{quality}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    
    # Use data/cache/thumbnails directory
    cache_dir = Path("data/cache/thumbnails")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Get original file extension
    original_ext = Path(original_path).suffix.lower()
    cache_ext = ".jpg" if original_ext in ['.jpg', '.jpeg', '.png', '.bmp'] else original_ext
    
    return cache_dir / f"{cache_hash}{cache_ext}"


def get_cached_resized_image(original_path: str, width: int, height: int, 
                           quality: int = 85, max_age_hours: int = 24) -> Optional[Path]:
    """
    Get a cached resized image if it exists and is fresh.
    
    Args:
        original_path: Path to original image
        width: Target width
        height: Target height
        quality: JPEG quality
        max_age_hours: Maximum age of cache in hours
        
    Returns:
        Path to cached image if valid, None otherwise
    """
    cache_path = get_cache_path(original_path, width, height, quality)
    
    if not cache_path.exists():
        return None
    
    # Check if original file exists and cache is newer
    original_file = Path(original_path)
    if not original_file.exists():
        return None
    
    cache_mtime = cache_path.stat().st_mtime
    original_mtime = original_file.stat().st_mtime
    
    # Check if cache is newer than original and within max age
    import time
    current_time = time.time()
    cache_age_hours = (current_time - cache_mtime) / 3600
    
    if cache_mtime >= original_mtime and cache_age_hours <= max_age_hours:
        return cache_path
    
    # Remove stale cache
    try:
        cache_path.unlink()
    except:
        pass
    
    return None


def create_cached_resized_image(original_path: str, width: int, height: int, 
                               quality: int = 85) -> Optional[Path]:
    """
    Create and cache a resized image.
    
    Args:
        original_path: Path to original image
        width: Target width
        height: Target height
        quality: JPEG quality
        
    Returns:
        Path to cached resized image or None if failed
    """
    try:
        original_file = Path(original_path)
        if not original_file.exists():
            return None
        
        # Load and resize image
        with Image.open(original_file) as image:
            # Convert to RGB if needed (for transparency handling)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            resized_image = resize_image_smart(image, width, height, quality)
            
            # Save to cache
            cache_path = get_cache_path(original_path, width, height, quality)
            
            # Ensure directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with appropriate format
            if cache_path.suffix.lower() in ['.jpg', '.jpeg']:
                resized_image.save(cache_path, 'JPEG', quality=quality, optimize=True)
            else:
                resized_image.save(cache_path, quality=quality, optimize=True)
            
            return cache_path
            
    except Exception as e:
        print(f"Error creating cached resized image: {e}")
        return None