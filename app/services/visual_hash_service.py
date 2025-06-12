"""Service for calculating and comparing visual hashes of images."""

import logging
from pathlib import Path
from typing import Optional, List, Set
from PIL import Image
import imagehash

logger = logging.getLogger(__name__)


class VisualHashService:
    """Service for visual image hashing and similarity detection."""
    
    # Hamming distance threshold for considering images similar
    # Lower values = more strict similarity matching
    SIMILARITY_THRESHOLD = 8  # Out of 64 bits for average hash
    
    @staticmethod
    def calculate_hash(image_path: str, algorithm: str = 'average') -> Optional[str]:
        """
        Calculate perceptual hash for an image.
        
        Args:
            image_path: Path to the image file
            algorithm: Hash algorithm ('average', 'difference', 'perceptual', 'wavelet')
            
        Returns:
            Hex string of the hash, or None if calculation failed
        """
        try:
            if not Path(image_path).exists():
                logger.warning(f"Image file not found: {image_path}")
                return None
                
            with Image.open(image_path) as img:
                # Convert to RGB if needed (handles RGBA, grayscale, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate hash based on algorithm
                if algorithm == 'average':
                    hash_obj = imagehash.average_hash(img)
                elif algorithm == 'difference':
                    hash_obj = imagehash.dhash(img)
                elif algorithm == 'perceptual':
                    hash_obj = imagehash.phash(img)
                elif algorithm == 'wavelet':
                    hash_obj = imagehash.whash(img)
                else:
                    logger.warning(f"Unknown hash algorithm: {algorithm}, using average")
                    hash_obj = imagehash.average_hash(img)
                
                return str(hash_obj)
                
        except Exception as e:
            logger.error(f"Failed to calculate hash for {image_path}: {e}")
            return None
    
    @staticmethod
    def calculate_hamming_distance(hash1: str, hash2: str) -> Optional[int]:
        """
        Calculate Hamming distance between two hashes.
        
        Args:
            hash1: First hash as hex string
            hash2: Second hash as hex string
            
        Returns:
            Hamming distance (number of different bits), or None if calculation failed
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2  # This returns Hamming distance
        except Exception as e:
            logger.error(f"Failed to calculate distance between {hash1} and {hash2}: {e}")
            return None
    
    @classmethod
    def are_similar(cls, hash1: str, hash2: str) -> bool:
        """
        Check if two images are visually similar based on their hashes.
        
        Args:
            hash1: First hash as hex string
            hash2: Second hash as hex string
            
        Returns:
            True if images are considered similar
        """
        distance = cls.calculate_hamming_distance(hash1, hash2)
        if distance is None:
            return False
        return distance <= cls.SIMILARITY_THRESHOLD
    
    @classmethod
    def find_similar_hashes(cls, target_hash: str, hash_list: List[str]) -> List[str]:
        """
        Find all hashes in a list that are similar to the target hash.
        
        Args:
            target_hash: Hash to compare against
            hash_list: List of hashes to search through
            
        Returns:
            List of similar hashes
        """
        similar = []
        for hash_str in hash_list:
            if cls.are_similar(target_hash, hash_str):
                similar.append(hash_str)
        return similar
    
    @classmethod
    def group_similar_hashes(cls, hash_list: List[str]) -> List[List[str]]:
        """
        Group a list of hashes into clusters of similar hashes.
        
        Args:
            hash_list: List of hashes to group
            
        Returns:
            List of groups, where each group is a list of similar hashes
        """
        if not hash_list:
            return []
        
        groups = []
        processed: Set[str] = set()
        
        for hash_str in hash_list:
            if hash_str in processed:
                continue
                
            # Find all hashes similar to this one
            similar_group = [hash_str]
            processed.add(hash_str)
            
            for other_hash in hash_list:
                if other_hash != hash_str and other_hash not in processed:
                    if cls.are_similar(hash_str, other_hash):
                        similar_group.append(other_hash)
                        processed.add(other_hash)
            
            groups.append(similar_group)
        
        return groups


def calculate_detection_hash(image_path: str) -> Optional[str]:
    """
    Convenience function to calculate hash for a detection image.
    Uses average hash which is fast and good for basic similarity detection.
    """
    return VisualHashService.calculate_hash(image_path, algorithm='average')