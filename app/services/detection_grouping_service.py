"""Service for grouping detections by visual similarity."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

from sqlmodel import Session, select
from app.models.detection import Detection
from app.services.visual_hash_service import VisualHashService

logger = logging.getLogger(__name__)


@dataclass
class DetectionGroup:
    """A group of visually similar detections."""
    primary_detection: Detection  # The "best" detection to show as representative
    similar_detections: List[Detection]  # All detections in the group (including primary)
    group_size: int  # Total number of detections in group
    visual_hash: str  # The visual hash that groups these detections
    
    @property
    def has_multiple(self) -> bool:
        """Check if this group contains multiple detections."""
        return self.group_size > 1


class DetectionGroupingService:
    """Service for grouping detections by visual similarity."""
    
    @staticmethod
    def select_primary_detection(detections: List[Detection]) -> Detection:
        """
        Select the best detection from a group to use as the primary representative.
        
        Selection criteria (in order of preference):
        1. Detection with the highest foe confidence
        2. Detection with the most foes detected
        3. Most recent detection
        
        Args:
            detections: List of detections to choose from
            
        Returns:
            The selected primary detection
        """
        if len(detections) == 1:
            return detections[0]
        
        # Score each detection
        best_detection = detections[0]
        best_score = -1
        
        for detection in detections:
            score = 0
            
            # Factor 1: Highest foe confidence (weight: 100)
            if detection.foes:
                max_confidence = max(foe.confidence for foe in detection.foes)
                score += max_confidence * 100
            
            # Factor 2: Number of foes detected (weight: 10)
            score += len(detection.foes) * 10
            
            # Factor 3: Recent timestamp (weight: 1)
            # Use timestamp as tiebreaker (more recent is better)
            score += detection.timestamp.timestamp() / 1e6  # Normalize to small value
            
            if score > best_score:
                best_score = score
                best_detection = detection
        
        return best_detection
    
    @classmethod
    def group_detections(
        cls, 
        detections: List[Detection], 
        max_group_size: int = 5
    ) -> List[DetectionGroup]:
        """
        Group detections by visual similarity.
        
        Args:
            detections: List of detections to group
            max_group_size: Maximum number of detections per group
            
        Returns:
            List of detection groups
        """
        if not detections:
            return []
        
        # Separate detections with and without visual hashes
        hashed_detections = [d for d in detections if d.visual_hash]
        unhashed_detections = [d for d in detections if not d.visual_hash]
        
        logger.debug(f"Grouping {len(hashed_detections)} hashed detections, "
                    f"{len(unhashed_detections)} without hashes")
        
        groups = []
        
        # Group hashed detections by similarity
        if hashed_detections:
            groups.extend(cls._group_by_visual_hash(hashed_detections, max_group_size))
        
        # Add unhashed detections as individual groups
        for detection in unhashed_detections:
            groups.append(DetectionGroup(
                primary_detection=detection,
                similar_detections=[detection],
                group_size=1,
                visual_hash=""  # No hash available
            ))
        
        # Sort groups by primary detection timestamp (most recent first)
        groups.sort(key=lambda g: g.primary_detection.timestamp, reverse=True)
        
        logger.debug(f"Created {len(groups)} detection groups from {len(detections)} detections")
        return groups
    
    @classmethod
    def _group_by_visual_hash(
        cls, 
        detections: List[Detection], 
        max_group_size: int
    ) -> List[DetectionGroup]:
        """Group detections that have visual hashes."""
        hash_to_detections = defaultdict(list)
        
        # Group detections by exact hash match first
        for detection in detections:
            hash_to_detections[detection.visual_hash].append(detection)
        
        # Now check for similar hashes between groups
        hash_groups = []
        processed_hashes = set()
        
        for primary_hash, group_detections in hash_to_detections.items():
            if primary_hash in processed_hashes:
                continue
            
            # Start with exact matches
            merged_group = group_detections[:]
            processed_hashes.add(primary_hash)
            
            # Look for similar hashes if group is not too large
            if len(merged_group) < max_group_size:
                for other_hash, other_detections in hash_to_detections.items():
                    if (other_hash not in processed_hashes and 
                        len(merged_group) + len(other_detections) <= max_group_size):
                        
                        if VisualHashService.are_similar(primary_hash, other_hash):
                            merged_group.extend(other_detections)
                            processed_hashes.add(other_hash)
            
            # Create group
            primary_detection = cls.select_primary_detection(merged_group)
            hash_groups.append(DetectionGroup(
                primary_detection=primary_detection,
                similar_detections=sorted(merged_group, key=lambda d: d.timestamp, reverse=True),
                group_size=len(merged_group),
                visual_hash=primary_hash
            ))
        
        return hash_groups
    
    @staticmethod
    def expand_group(group: DetectionGroup, limit: Optional[int] = None) -> List[Detection]:
        """
        Get all detections in a group for expansion view.
        
        Args:
            group: The detection group to expand
            limit: Optional limit on number of detections to return
            
        Returns:
            List of detections in the group
        """
        detections = group.similar_detections
        if limit:
            detections = detections[:limit]
        return detections
    
    @staticmethod
    def get_group_stats(groups: List[DetectionGroup]) -> Dict[str, Any]:
        """
        Get statistics about the grouped detections.
        
        Args:
            groups: List of detection groups
            
        Returns:
            Dictionary with grouping statistics
        """
        total_detections = sum(group.group_size for group in groups)
        multi_detection_groups = [g for g in groups if g.has_multiple]
        singles = [g for g in groups if not g.has_multiple]
        
        return {
            "total_groups": len(groups),
            "total_detections": total_detections,
            "multi_detection_groups": len(multi_detection_groups),
            "single_detections": len(singles),
            "largest_group_size": max((g.group_size for g in groups), default=0),
            "average_group_size": total_detections / len(groups) if groups else 0,
            "compression_ratio": len(groups) / total_detections if total_detections > 0 else 0
        }