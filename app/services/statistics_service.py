"""Service for aggregating and analyzing detection statistics."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case

from app.models.detection import Detection, Foe, DetectionStatus
from app.models.sound_effectiveness import SoundEffectiveness, SoundStatistics
from app.models.device import Device

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for generating comprehensive statistics and analytics."""
    
    def __init__(self, session: Session):
        self.session = session
    
    async def get_overview_stats(self) -> Dict[str, Any]:
        """Get high-level overview statistics."""
        # Total detections
        total_detections = self.session.query(Detection).count()
        
        # Detections with successful deterrents
        successful_deterrents = self.session.query(Detection).filter(
            Detection.deterrent_effective == True
        ).count()
        
        # Overall success rate
        success_rate = (successful_deterrents / total_detections * 100) if total_detections > 0 else 0
        
        # Detections today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        detections_today = self.session.query(Detection).filter(
            Detection.created_at >= today_start
        ).count()
        
        # Most common foe
        most_common_foe = self.session.query(
            Detection.detected_foe,
            func.count(Detection.id).label('count')
        ).filter(
            Detection.detected_foe != None
        ).group_by(Detection.detected_foe).order_by(desc('count')).first()
        
        # Active cameras
        active_cameras = self.session.query(Device).filter(
            Device.is_active == True
        ).count()
        
        # Friend vs foe ratio (we'll determine friends based on non-foe detections)
        friend_detections = self._get_friend_detections_count()
        foe_detections = self.session.query(Detection).filter(
            Detection.detected_foe != None
        ).count()
        
        return {
            "total_detections": total_detections,
            "successful_deterrents": successful_deterrents,
            "success_rate": round(success_rate, 1),
            "detections_today": detections_today,
            "most_common_foe": most_common_foe[0] if most_common_foe else None,
            "most_common_foe_count": most_common_foe[1] if most_common_foe else 0,
            "active_cameras": active_cameras,
            "friend_detections": friend_detections,
            "foe_detections": foe_detections,
            "friend_foe_ratio": round(friend_detections / foe_detections, 2) if foe_detections > 0 else 0
        }
    
    async def get_daily_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get daily detection and success trends."""
        start_date = datetime.now() - timedelta(days=days)
        
        # Daily detections and successes
        daily_stats = self.session.query(
            func.date(Detection.created_at).label('date'),
            func.count(Detection.id).label('total'),
            func.sum(case((Detection.deterrent_effective == True, 1), else_=0)).label('successful'),
            func.sum(case((Detection.detected_foe != None, 1), else_=0)).label('foes'),
            func.sum(case((Detection.detected_foe == None, 1), else_=0)).label('friends')
        ).filter(
            Detection.created_at >= start_date
        ).group_by(func.date(Detection.created_at)).all()
        
        dates = []
        totals = []
        successes = []
        foes = []
        friends = []
        success_rates = []
        
        for stat in daily_stats:
            dates.append(stat.date.strftime('%Y-%m-%d'))
            totals.append(stat.total)
            successes.append(stat.successful or 0)
            foes.append(stat.foes or 0)
            friends.append(stat.friends or 0)
            success_rate = (stat.successful / stat.foes * 100) if stat.foes > 0 else 0
            success_rates.append(round(success_rate, 1))
        
        return {
            "dates": dates,
            "totals": totals,
            "successes": successes,
            "foes": foes,
            "friends": friends,
            "success_rates": success_rates
        }
    
    async def get_hourly_patterns(self) -> Dict[str, Any]:
        """Get hourly activity patterns."""
        # Activity by hour
        hourly_stats = self.session.query(
            func.extract('hour', Detection.created_at).label('hour'),
            func.count(Detection.id).label('total'),
            func.sum(case((Detection.detected_foe != None, 1), else_=0)).label('foes'),
            func.sum(case((Detection.detected_foe == None, 1), else_=0)).label('friends')
        ).group_by(func.extract('hour', Detection.created_at)).all()
        
        hours = list(range(24))
        totals = [0] * 24
        foes = [0] * 24
        friends = [0] * 24
        
        for stat in hourly_stats:
            hour = int(stat.hour)
            totals[hour] = stat.total
            foes[hour] = stat.foes or 0
            friends[hour] = stat.friends or 0
        
        # Find peak hours
        peak_foe_hour = hours[foes.index(max(foes))] if max(foes) > 0 else None
        peak_friend_hour = hours[friends.index(max(friends))] if max(friends) > 0 else None
        
        return {
            "hours": hours,
            "totals": totals,
            "foes": foes,
            "friends": friends,
            "peak_foe_hour": peak_foe_hour,
            "peak_friend_hour": peak_friend_hour
        }
    
    async def get_sound_effectiveness_rankings(self) -> Dict[str, Any]:
        """Get comprehensive sound effectiveness rankings."""
        # Overall sound effectiveness
        overall_rankings = self.session.query(
            SoundStatistics.sound_file,
            SoundStatistics.times_played,
            SoundStatistics.times_effective,
            SoundStatistics.effectiveness_rate,
            func.avg(SoundStatistics.effectiveness_rate).label('avg_effectiveness')
        ).group_by(
            SoundStatistics.sound_file
        ).order_by(desc('avg_effectiveness')).limit(10).all()
        
        # Per-foe effectiveness
        per_foe_stats = self.session.query(
            SoundStatistics.foe_type,
            SoundStatistics.sound_file,
            SoundStatistics.effectiveness_rate,
            SoundStatistics.times_played
        ).filter(
            SoundStatistics.times_played >= 3  # Only sounds tested at least 3 times
        ).order_by(
            SoundStatistics.foe_type,
            desc(SoundStatistics.effectiveness_rate)
        ).all()
        
        # Group by foe type
        foe_sound_rankings = defaultdict(list)
        for stat in per_foe_stats:
            foe_sound_rankings[stat.foe_type].append({
                "sound": stat.sound_file,
                "effectiveness": round(stat.effectiveness_rate, 1),
                "times_played": stat.times_played
            })
        
        # Sounds needing more testing
        untested_sounds = self._get_untested_sounds()
        
        return {
            "overall_rankings": [
                {
                    "sound": r.sound_file,
                    "times_played": r.times_played,
                    "times_effective": r.times_effective,
                    "effectiveness": round(r.avg_effectiveness, 1)
                }
                for r in overall_rankings
            ],
            "per_foe_rankings": dict(foe_sound_rankings),
            "untested_sounds": untested_sounds
        }
    
    async def get_foe_analytics(self) -> Dict[str, Any]:
        """Get detailed foe behavior analytics."""
        # Foe frequency
        foe_counts = self.session.query(
            Detection.detected_foe,
            func.count(Detection.id).label('count'),
            func.sum(case((Detection.deterrent_effective == True, 1), else_=0)).label('deterred')
        ).filter(
            Detection.detected_foe != None
        ).group_by(Detection.detected_foe).all()
        
        foe_data = []
        for foe in foe_counts:
            deterred = foe.deterred or 0
            success_rate = (deterred / foe.count * 100) if foe.count > 0 else 0
            foe_data.append({
                "type": foe.detected_foe,
                "count": foe.count,
                "deterred": deterred,
                "success_rate": round(success_rate, 1)
            })
        
        # Sort by count
        foe_data.sort(key=lambda x: x['count'], reverse=True)
        
        # Most persistent foes (multiple detections within short time)
        persistent_foes = self._get_persistent_foes()
        
        # Time between detections per foe
        avg_intervals = self._get_average_detection_intervals()
        
        return {
            "foe_frequencies": foe_data,
            "persistent_foes": persistent_foes,
            "average_intervals": avg_intervals
        }
    
    async def get_friend_analytics(self) -> Dict[str, Any]:
        """Analyze impact on friendly creatures."""
        # Get detections where no foe was detected (potential friends)
        friend_detections = self._get_friend_detections()
        
        # Friend types from AI analysis
        friend_types = defaultdict(int)
        for detection in friend_detections:
            if detection.ai_analysis:
                # Extract friendly creatures from AI analysis
                analysis = detection.ai_analysis.lower()
                if 'squirrel' in analysis:
                    friend_types['squirrel'] += 1
                elif 'small bird' in analysis or 'songbird' in analysis:
                    friend_types['small_bird'] += 1
                elif 'butterfly' in analysis:
                    friend_types['butterfly'] += 1
                elif 'hedgehog' in analysis:
                    friend_types['hedgehog'] += 1
                else:
                    friend_types['other'] += 1
        
        # Trend of friends over time
        friend_trend = self._get_friend_trend()
        
        # Impact of deterrents on friends
        deterrent_impact = self._analyze_deterrent_impact_on_friends()
        
        return {
            "friend_types": dict(friend_types),
            "friend_trend": friend_trend,
            "deterrent_impact": deterrent_impact,
            "total_friends": len(friend_detections)
        }
    
    async def get_camera_statistics(self) -> Dict[str, Any]:
        """Get camera-specific statistics."""
        camera_stats = self.session.query(
            Device.name,
            Device.id,
            func.count(Detection.id).label('detections'),
            func.sum(case((Detection.detected_foe != None, 1), else_=0)).label('foes'),
            func.sum(case((Detection.deterrent_effective == True, 1), else_=0)).label('successful')
        ).join(
            Detection, Device.id == Detection.device_id
        ).group_by(Device.id, Device.name).all()
        
        camera_data = []
        for stat in camera_stats:
            success_rate = (stat.successful / stat.foes * 100) if stat.foes > 0 else 0
            camera_data.append({
                "name": stat.name,
                "detections": stat.detections,
                "foes": stat.foes or 0,
                "successful": stat.successful or 0,
                "success_rate": round(success_rate, 1)
            })
        
        # Sort by detection count
        camera_data.sort(key=lambda x: x['detections'], reverse=True)
        
        return {
            "cameras": camera_data,
            "most_active": camera_data[0]['name'] if camera_data else None
        }
    
    async def get_cost_analytics(self) -> Dict[str, Any]:
        """Analyze AI processing costs."""
        # Daily costs
        daily_costs = self.session.query(
            func.date(Detection.created_at).label('date'),
            func.sum(Detection.ai_cost).label('cost')
        ).filter(
            Detection.created_at >= datetime.now() - timedelta(days=30)
        ).group_by(func.date(Detection.created_at)).all()
        
        # Cost per successful deterrent
        total_cost = self.session.query(func.sum(Detection.ai_cost)).scalar() or 0
        successful_deterrents = self.session.query(Detection).filter(
            Detection.deterrent_effective == True
        ).count()
        
        cost_per_success = (total_cost / successful_deterrents) if successful_deterrents > 0 else 0
        
        # Monthly projection
        avg_daily_cost = total_cost / 30 if daily_costs else 0
        monthly_projection = avg_daily_cost * 30
        
        return {
            "daily_costs": [
                {"date": c.date.strftime('%Y-%m-%d'), "cost": float(c.cost or 0)}
                for c in daily_costs
            ],
            "total_cost": round(float(total_cost), 2),
            "cost_per_success": round(float(cost_per_success), 4),
            "monthly_projection": round(float(monthly_projection), 2),
            "avg_daily_cost": round(float(avg_daily_cost), 2)
        }
    
    async def get_recent_detections(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent detections for live updates."""
        since = datetime.now() - timedelta(hours=hours)
        
        detections = self.session.query(Detection).filter(
            Detection.created_at >= since
        ).order_by(desc(Detection.created_at)).limit(10).all()
        
        return [
            {
                "id": d.id,
                "timestamp": d.created_at.isoformat(),
                "device": d.device.name if d.device else "Unknown",
                "foe": d.detected_foe,
                "effective": d.deterrent_effective
            }
            for d in detections
        ]
    
    async def get_current_activity_level(self) -> str:
        """Determine current activity level."""
        # Count detections in last 15 minutes
        recent = datetime.now() - timedelta(minutes=15)
        recent_count = self.session.query(Detection).filter(
            Detection.created_at >= recent
        ).count()
        
        if recent_count == 0:
            return "quiet"
        elif recent_count <= 2:
            return "low"
        elif recent_count <= 5:
            return "moderate"
        else:
            return "high"
    
    async def get_detailed_foe_effectiveness(self, foe_type: str) -> Dict[str, Any]:
        """Get detailed effectiveness data for a specific foe type."""
        # All sounds tested against this foe
        sound_stats = self.session.query(SoundStatistics).filter(
            SoundStatistics.foe_type == foe_type
        ).order_by(desc(SoundStatistics.effectiveness_rate)).all()
        
        # Time-based effectiveness
        hourly_effectiveness = self.session.query(
            func.extract('hour', Detection.created_at).label('hour'),
            func.count(Detection.id).label('total'),
            func.sum(case((Detection.deterrent_effective == True, 1), else_=0)).label('effective')
        ).filter(
            Detection.detected_foe == foe_type
        ).group_by(func.extract('hour', Detection.created_at)).all()
        
        return {
            "foe_type": foe_type,
            "sound_rankings": [
                {
                    "sound": s.sound_file,
                    "effectiveness": round(s.effectiveness_rate, 1),
                    "times_played": s.times_played,
                    "times_effective": s.times_effective
                }
                for s in sound_stats
            ],
            "hourly_effectiveness": [
                {
                    "hour": int(h.hour),
                    "total": h.total,
                    "effective": h.effective or 0,
                    "rate": round((h.effective / h.total * 100) if h.total > 0 else 0, 1)
                }
                for h in hourly_effectiveness
            ]
        }
    
    # Helper methods
    def _get_friend_detections_count(self) -> int:
        """Count detections that are likely friends."""
        return self.session.query(Detection).filter(
            and_(
                Detection.detected_foe == None,
                Detection.status == DetectionStatus.PROCESSED
            )
        ).count()
    
    def _get_friend_detections(self) -> List[Detection]:
        """Get detections that are likely friends."""
        return self.session.query(Detection).filter(
            and_(
                Detection.detected_foe == None,
                Detection.status == DetectionStatus.PROCESSED
            )
        ).all()
    
    def _get_untested_sounds(self) -> List[str]:
        """Get sounds that need more testing."""
        # Get all available sounds (this would be from your sounds directory)
        # For now, returning placeholder
        all_sounds = []  # TODO: Get from sound directory
        
        # Get tested sounds
        tested = self.session.query(
            SoundStatistics.sound_file
        ).filter(
            SoundStatistics.times_played >= 5
        ).distinct().all()
        
        tested_files = {s[0] for s in tested}
        return [s for s in all_sounds if s not in tested_files]
    
    def _get_persistent_foes(self) -> List[Dict[str, Any]]:
        """Identify foes that return frequently."""
        # This would analyze detection patterns to find foes that return
        # within short time windows
        # Placeholder implementation
        return []
    
    def _get_average_detection_intervals(self) -> Dict[str, float]:
        """Calculate average time between detections for each foe."""
        # Placeholder - would calculate time differences between consecutive
        # detections of the same foe type
        return {}
    
    def _get_friend_trend(self) -> Dict[str, Any]:
        """Analyze friend detection trends over time."""
        # Daily friend counts for last 30 days
        friend_counts = self.session.query(
            func.date(Detection.created_at).label('date'),
            func.count(Detection.id).label('count')
        ).filter(
            and_(
                Detection.detected_foe == None,
                Detection.created_at >= datetime.now() - timedelta(days=30)
            )
        ).group_by(func.date(Detection.created_at)).all()
        
        return {
            "dates": [f.date.strftime('%Y-%m-%d') for f in friend_counts],
            "counts": [f.count for f in friend_counts]
        }
    
    def _analyze_deterrent_impact_on_friends(self) -> Dict[str, Any]:
        """Analyze how deterrents affect friendly creature appearances."""
        # Compare friend detections before and after deterrent events
        # Placeholder implementation
        return {
            "impact": "minimal",  # or "negative", "positive"
            "confidence": 0.75
        }