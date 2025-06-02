"""Image utility functions."""

from PIL import Image
from typing import Tuple


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