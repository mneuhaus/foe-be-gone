"""Service for tracking and analyzing deterrent effectiveness."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlmodel import select, func

from app.models.sound_effectiveness import (
    SoundEffectiveness, 
    DeterrentResult, 
    SoundStatistics,
    TimeBasedEffectiveness
)
from app.models.detection import Detection, Foe
from app.core.session import get_db_session, safe_commit

logger = logging.getLogger(__name__)


class EffectivenessTracker:
    """Track and analyze the effectiveness of deterrent sounds."""
    
    def record_effectiveness(
        self,
        detection_id: int,
        foe_type: str,
        sound_file: str,
        playback_method: str,
        foes_before: List[Foe],
        foes_after: List[Foe],
        follow_up_image_path: Optional[str] = None,
        wait_duration: int = 10
    ) -> SoundEffectiveness:
        """
        Record the effectiveness of a deterrent sound.
        
        Args:
            detection_id: ID of the original detection
            foe_type: Type of foe being deterred
            sound_file: Name of the sound file played
            playback_method: How the sound was played (camera/local)
            foes_before: List of foes detected before deterrent
            foes_after: List of foes detected after deterrent
            follow_up_image_path: Path to follow-up snapshot
            wait_duration: Seconds waited before re-check
            
        Returns:
            SoundEffectiveness record
        """
        # Calculate metrics
        foes_before_count = len(foes_before)
        foes_after_count = len(foes_after)
        
        # Calculate average confidence
        confidence_before = sum(f.confidence for f in foes_before) / foes_before_count if foes_before else 0.0
        confidence_after = sum(f.confidence for f in foes_after) / foes_after_count if foes_after else 0.0
        
        # Determine result
        if foes_after_count == 0:
            result = DeterrentResult.SUCCESS
        elif foes_after_count < foes_before_count:
            result = DeterrentResult.PARTIAL
        else:
            result = DeterrentResult.FAILURE
            
        with get_db_session() as session:
            # Create effectiveness record
            effectiveness = SoundEffectiveness(
                detection_id=detection_id,
                foe_type=foe_type,
                sound_file=sound_file,
                playback_method=playback_method,
                foes_before=foes_before_count,
                foes_after=foes_after_count,
                confidence_before=confidence_before,
                confidence_after=confidence_after,
                wait_duration=wait_duration,
                result=result,
                follow_up_image_path=follow_up_image_path
            )
            
            # Calculate effectiveness score
            effectiveness.effectiveness_score = effectiveness.calculate_effectiveness_score()
            
            session.add(effectiveness)
            safe_commit(session)
            
            # Update aggregated statistics
            self._update_statistics(session, effectiveness)
            
            # Update time-based patterns
            self._update_time_patterns(session, effectiveness)
            
            logger.info(
                f"Recorded effectiveness: {sound_file} vs {foe_type} - "
                f"{result.value} (score: {effectiveness.effectiveness_score:.2f})"
            )
            
            return effectiveness
    
    def _update_statistics(self, session, effectiveness: SoundEffectiveness):
        """Update aggregated statistics for a sound/foe combination."""
        # Find or create statistics record
        stats = session.exec(
            select(SoundStatistics)
            .where(SoundStatistics.foe_type == effectiveness.foe_type)
            .where(SoundStatistics.sound_file == effectiveness.sound_file)
        ).first()
        
        if not stats:
            stats = SoundStatistics(
                foe_type=effectiveness.foe_type,
                sound_file=effectiveness.sound_file,
                first_used=effectiveness.timestamp
            )
            session.add(stats)
        
        # Update statistics
        stats.update_statistics(effectiveness)
        
        # Recalculate average effectiveness
        all_scores = session.exec(
            select(SoundEffectiveness.effectiveness_score)
            .where(SoundEffectiveness.foe_type == effectiveness.foe_type)
            .where(SoundEffectiveness.sound_file == effectiveness.sound_file)
        ).all()
        
        if all_scores:
            stats.average_effectiveness = sum(all_scores) / len(all_scores)
        
        safe_commit(session)
    
    def _update_time_patterns(self, session, effectiveness: SoundEffectiveness):
        """Update time-based effectiveness patterns."""
        hour = effectiveness.timestamp.hour
        
        # Find or create time pattern record
        pattern = session.exec(
            select(TimeBasedEffectiveness)
            .where(TimeBasedEffectiveness.foe_type == effectiveness.foe_type)
            .where(TimeBasedEffectiveness.hour_of_day == hour)
        ).first()
        
        if not pattern:
            pattern = TimeBasedEffectiveness(
                foe_type=effectiveness.foe_type,
                hour_of_day=hour
            )
            session.add(pattern)
        
        # Update pattern statistics
        pattern.total_detections += 1
        if effectiveness.result == DeterrentResult.SUCCESS:
            pattern.successful_deterrents += 1
        
        # Check if this sound is performing better than current best
        sound_stats = session.exec(
            select(SoundStatistics)
            .where(SoundStatistics.foe_type == effectiveness.foe_type)
            .where(SoundStatistics.sound_file == effectiveness.sound_file)
        ).first()
        
        if sound_stats and (not pattern.best_sound or sound_stats.success_rate > pattern.best_sound_success_rate):
            pattern.best_sound = effectiveness.sound_file
            pattern.best_sound_success_rate = sound_stats.success_rate
        
        pattern.last_updated = datetime.utcnow()
        safe_commit(session)
    
    def get_best_sound_for_foe(self, foe_type: str, hour: Optional[int] = None) -> Optional[str]:
        """
        Get the most effective sound for a specific foe type.
        
        Args:
            foe_type: Type of foe
            hour: Optional hour of day for time-based selection
            
        Returns:
            Name of the most effective sound file, or None
        """
        with get_db_session() as session:
            # If hour is specified, check time-based patterns first
            if hour is not None:
                pattern = session.exec(
                    select(TimeBasedEffectiveness)
                    .where(TimeBasedEffectiveness.foe_type == foe_type)
                    .where(TimeBasedEffectiveness.hour_of_day == hour)
                ).first()
                
                if pattern and pattern.best_sound:
                    logger.info(f"Using time-based best sound for {foe_type} at hour {hour}: {pattern.best_sound}")
                    return pattern.best_sound
            
            # Fall back to overall best performing sound
            best_stats = session.exec(
                select(SoundStatistics)
                .where(SoundStatistics.foe_type == foe_type)
                .order_by(SoundStatistics.average_effectiveness.desc())
                .limit(1)
            ).first()
            
            if best_stats:
                logger.info(f"Using overall best sound for {foe_type}: {best_stats.sound_file}")
                return best_stats.sound_file
                
            return None
    
    def get_statistics_summary(self, foe_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a summary of effectiveness statistics.
        
        Args:
            foe_type: Optional filter by foe type
            
        Returns:
            Dictionary with statistics summary
        """
        with get_db_session() as session:
            query = select(SoundStatistics)
            if foe_type:
                query = query.where(SoundStatistics.foe_type == foe_type)
            
            stats = session.exec(query.order_by(SoundStatistics.average_effectiveness.desc())).all()
            
            summary = {
                "total_sounds_tested": len(stats),
                "by_foe_type": {},
                "top_performers": []
            }
            
            # Group by foe type
            for stat in stats:
                if stat.foe_type not in summary["by_foe_type"]:
                    summary["by_foe_type"][stat.foe_type] = {
                        "sounds_tested": 0,
                        "total_uses": 0,
                        "overall_success_rate": 0.0,
                        "best_sound": None,
                        "best_success_rate": 0.0
                    }
                
                foe_summary = summary["by_foe_type"][stat.foe_type]
                foe_summary["sounds_tested"] += 1
                foe_summary["total_uses"] += stat.total_uses
                
                if stat.success_rate > foe_summary["best_success_rate"]:
                    foe_summary["best_sound"] = stat.sound_file
                    foe_summary["best_success_rate"] = stat.success_rate
                
                # Add to top performers
                if stat.total_uses >= 5 and stat.average_effectiveness >= 0.7:  # Min 5 uses, 70% effective
                    summary["top_performers"].append({
                        "foe_type": stat.foe_type,
                        "sound_file": stat.sound_file,
                        "success_rate": stat.success_rate,
                        "average_effectiveness": stat.average_effectiveness,
                        "total_uses": stat.total_uses
                    })
            
            # Calculate overall success rates
            for foe_type, foe_data in summary["by_foe_type"].items():
                total_success = sum(s.successful_uses for s in stats if s.foe_type == foe_type)
                total_uses = foe_data["total_uses"]
                if total_uses > 0:
                    foe_data["overall_success_rate"] = total_success / total_uses
            
            # Sort top performers
            summary["top_performers"].sort(key=lambda x: x["average_effectiveness"], reverse=True)
            summary["top_performers"] = summary["top_performers"][:10]  # Top 10
            
            return summary
    
    def get_time_patterns(self, foe_type: str) -> List[Dict[str, Any]]:
        """Get effectiveness patterns by time of day for a foe type."""
        with get_db_session() as session:
            patterns = session.exec(
                select(TimeBasedEffectiveness)
                .where(TimeBasedEffectiveness.foe_type == foe_type)
                .order_by(TimeBasedEffectiveness.hour_of_day)
            ).all()
            
            return [
                {
                    "hour": p.hour_of_day,
                    "total_detections": p.total_detections,
                    "success_rate": p.successful_deterrents / p.total_detections if p.total_detections > 0 else 0,
                    "best_sound": p.best_sound,
                    "best_sound_success_rate": p.best_sound_success_rate
                }
                for p in patterns
            ]


# Global effectiveness tracker instance
effectiveness_tracker = EffectivenessTracker()