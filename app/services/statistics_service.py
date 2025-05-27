"""Service for aggregating and analyzing detection statistics - Fixed version."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case, text
from sqlmodel import select, col

from app.models.detection import Detection, Foe, DetectionStatus
from app.models.sound_effectiveness import SoundEffectiveness, SoundStatistics
from app.models.device import Device

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for generating comprehensive statistics and analytics."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_overview_stats(self) -> Dict[str, Any]:
        """Get high-level overview statistics."""
        # Total detections
        total_detections = len(self.session.exec(select(Detection)).all())
        
        # Detections with successful deterrents
        successful_deterrents = len(self.session.exec(
            select(Detection).where(Detection.deterrent_effective == True)
        ).all())
        
        # Overall success rate
        success_rate = (successful_deterrents / total_detections * 100) if total_detections > 0 else 0
        
        # Detections today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        detections_today = len(self.session.exec(
            select(Detection).where(Detection.created_at >= today_start)
        ).all())
        
        # Most common foe - using raw SQL for aggregation
        result = self.session.execute(
            text("""
            SELECT detected_foe, COUNT(*) as count
            FROM detections
            WHERE detected_foe IS NOT NULL
            GROUP BY detected_foe
            ORDER BY count DESC
            LIMIT 1
            """)
        ).first()
        
        most_common_foe = result[0] if result else None
        most_common_foe_count = result[1] if result else 0
        
        # Active cameras
        active_cameras = len(self.session.exec(
            select(Device).where(Device.status == "online")
        ).all())
        
        # Friend vs foe ratio
        friend_detections = self._get_friend_detections_count()
        foe_detections = len(self.session.exec(
            select(Detection).where(Detection.detected_foe != None)
        ).all())
        
        return {
            "total_detections": total_detections,
            "successful_deterrents": successful_deterrents,
            "success_rate": round(success_rate, 1),
            "detections_today": detections_today,
            "most_common_foe": most_common_foe,
            "most_common_foe_count": most_common_foe_count,
            "active_cameras": active_cameras,
            "friend_detections": friend_detections,
            "foe_detections": foe_detections,
            "friend_foe_ratio": round(friend_detections / foe_detections, 2) if foe_detections > 0 else 0
        }
    
    def get_daily_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get daily detection and success trends."""
        start_date = datetime.now() - timedelta(days=days)
        
        # Use raw SQL for complex aggregation
        daily_stats = self.session.execute(
            text(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN deterrent_effective = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN detected_foe IS NOT NULL THEN 1 ELSE 0 END) as foes,
                SUM(CASE WHEN detected_foe IS NULL THEN 1 ELSE 0 END) as friends
            FROM detections
            WHERE created_at >= '{start_date.isoformat()}'
            GROUP BY DATE(created_at)
            ORDER BY date
            """)
        ).all()
        
        dates = []
        totals = []
        successes = []
        foes = []
        friends = []
        success_rates = []
        
        for stat in daily_stats:
            dates.append(stat[0])
            totals.append(stat[1])
            successes.append(stat[2] or 0)
            foes.append(stat[3] or 0)
            friends.append(stat[4] or 0)
            success_rate = (stat[2] / stat[3] * 100) if stat[3] > 0 else 0
            success_rates.append(round(success_rate, 1))
        
        return {
            "dates": dates,
            "totals": totals,
            "successes": successes,
            "foes": foes,
            "friends": friends,
            "success_rates": success_rates
        }
    
    def get_hourly_patterns(self) -> Dict[str, Any]:
        """Get hourly activity patterns."""
        # Activity by hour using raw SQL
        hourly_stats = self.session.execute(
            text("""
            SELECT 
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN detected_foe IS NOT NULL THEN 1 ELSE 0 END) as foes,
                SUM(CASE WHEN detected_foe IS NULL THEN 1 ELSE 0 END) as friends
            FROM detections
            GROUP BY hour
            ORDER BY hour
            """)
        ).all()
        
        hours = list(range(24))
        totals = [0] * 24
        foes = [0] * 24
        friends = [0] * 24
        
        for stat in hourly_stats:
            hour = int(stat[0])
            totals[hour] = stat[1]
            foes[hour] = stat[2] or 0
            friends[hour] = stat[3] or 0
        
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
    
    def get_sound_effectiveness_rankings(self) -> Dict[str, Any]:
        """Get comprehensive sound effectiveness rankings."""
        # Overall sound effectiveness
        overall_rankings = self.session.exec(
            select(SoundStatistics)
            .order_by(col(SoundStatistics.success_rate).desc())
            .limit(10)
        ).all()
        
        # Per-foe effectiveness
        per_foe_stats = self.session.exec(
            select(SoundStatistics)
            .where(SoundStatistics.total_uses >= 3)
            .order_by(SoundStatistics.foe_type, col(SoundStatistics.success_rate).desc())
        ).all()
        
        # Group by foe type
        foe_sound_rankings = defaultdict(list)
        for stat in per_foe_stats:
            foe_sound_rankings[stat.foe_type].append({
                "sound": stat.sound_file,
                "effectiveness": round(stat.success_rate, 1),
                "total_uses": stat.total_uses
            })
        
        # Sounds needing more testing
        untested_sounds = self._get_untested_sounds()
        
        return {
            "overall_rankings": [
                {
                    "sound": r.sound_file,
                    "total_uses": r.total_uses,
                    "successful_uses": r.successful_uses,
                    "effectiveness": round(r.success_rate, 1)
                }
                for r in overall_rankings
            ],
            "per_foe_rankings": dict(foe_sound_rankings),
            "untested_sounds": untested_sounds
        }
    
    def get_foe_analytics(self) -> Dict[str, Any]:
        """Get detailed foe behavior analytics."""
        # Foe frequency using raw SQL
        foe_counts = self.session.execute(
            text("""
            SELECT 
                detected_foe,
                COUNT(*) as count,
                SUM(CASE WHEN deterrent_effective = 1 THEN 1 ELSE 0 END) as deterred
            FROM detections
            WHERE detected_foe IS NOT NULL
            GROUP BY detected_foe
            """)
        ).all()
        
        foe_data = []
        for foe in foe_counts:
            deterred = foe[2] or 0
            success_rate = (deterred / foe[1] * 100) if foe[1] > 0 else 0
            foe_data.append({
                "type": foe[0],
                "count": foe[1],
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
    
    def get_friend_analytics(self) -> Dict[str, Any]:
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
    
    def get_camera_statistics(self) -> Dict[str, Any]:
        """Get camera-specific statistics."""
        camera_stats = self.session.execute(
            text("""
            SELECT 
                d.name,
                d.id,
                COUNT(det.id) as detections,
                SUM(CASE WHEN det.detected_foe IS NOT NULL THEN 1 ELSE 0 END) as foes,
                SUM(CASE WHEN det.deterrent_effective = 1 THEN 1 ELSE 0 END) as successful
            FROM devices d
            LEFT JOIN detections det ON d.id = det.device_id
            GROUP BY d.id, d.name
            """)
        ).all()
        
        camera_data = []
        for stat in camera_stats:
            success_rate = (stat[4] / stat[3] * 100) if stat[3] > 0 else 0
            camera_data.append({
                "name": stat[0],
                "detections": stat[2],
                "foes": stat[3] or 0,
                "successful": stat[4] or 0,
                "success_rate": round(success_rate, 1)
            })
        
        # Sort by detection count
        camera_data.sort(key=lambda x: x['detections'], reverse=True)
        
        return {
            "cameras": camera_data,
            "most_active": camera_data[0]['name'] if camera_data else None
        }
    
    def get_cost_analytics(self) -> Dict[str, Any]:
        """Analyze AI processing costs."""
        # Daily costs
        daily_costs = self.session.execute(
            text(f"""
            SELECT 
                DATE(created_at) as date,
                SUM(ai_cost) as cost
            FROM detections
            WHERE created_at >= '{(datetime.now() - timedelta(days=30)).isoformat()}'
            GROUP BY DATE(created_at)
            ORDER BY date
            """)
        ).all()
        
        # Cost per successful deterrent
        total_cost_result = self.session.execute(
            text("SELECT SUM(ai_cost) FROM detections")
        ).scalar() or 0
        total_cost = float(total_cost_result) if total_cost_result else 0.0
        
        successful_deterrents = len(self.session.exec(
            select(Detection).where(Detection.deterrent_effective == True)
        ).all())
        
        cost_per_success = (total_cost / successful_deterrents) if successful_deterrents > 0 else 0
        
        # Monthly projection
        avg_daily_cost = total_cost / 30 if daily_costs else 0
        monthly_projection = avg_daily_cost * 30
        
        return {
            "daily_costs": [
                {"date": c[0], "cost": float(c[1] or 0)}
                for c in daily_costs
            ],
            "total_cost": round(float(total_cost), 2),
            "cost_per_success": round(float(cost_per_success), 4),
            "monthly_projection": round(float(monthly_projection), 2),
            "avg_daily_cost": round(float(avg_daily_cost), 2)
        }
    
    def get_recent_detections(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent detections for live updates."""
        since = datetime.now() - timedelta(hours=hours)
        
        detections = self.session.exec(
            select(Detection)
            .where(Detection.created_at >= since)
            .order_by(col(Detection.created_at).desc())
            .limit(10)
        ).all()
        
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
    
    def get_current_activity_level(self) -> str:
        """Determine current activity level."""
        # Count detections in last 15 minutes
        recent = datetime.now() - timedelta(minutes=15)
        recent_count = len(self.session.exec(
            select(Detection).where(Detection.created_at >= recent)
        ).all())
        
        if recent_count == 0:
            return "quiet"
        elif recent_count <= 2:
            return "low"
        elif recent_count <= 5:
            return "moderate"
        else:
            return "high"
    
    def get_detailed_foe_effectiveness(self, foe_type: str) -> Dict[str, Any]:
        """Get detailed effectiveness data for a specific foe type."""
        # All sounds tested against this foe
        sound_stats = self.session.exec(
            select(SoundStatistics)
            .where(SoundStatistics.foe_type == foe_type)
            .order_by(col(SoundStatistics.success_rate).desc())
        ).all()
        
        # Time-based effectiveness
        hourly_effectiveness = self.session.execute(
            text(f"""
            SELECT 
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN deterrent_effective = 1 THEN 1 ELSE 0 END) as effective
            FROM detections
            WHERE detected_foe = '{foe_type}'
            GROUP BY hour
            """)
        ).all()
        
        return {
            "foe_type": foe_type,
            "sound_rankings": [
                {
                    "sound": s.sound_file,
                    "effectiveness": round(s.success_rate, 1),
                    "total_uses": s.total_uses,
                    "successful_uses": s.successful_uses
                }
                for s in sound_stats
            ],
            "hourly_effectiveness": [
                {
                    "hour": int(h[0]),
                    "total": h[1],
                    "effective": h[2] or 0,
                    "rate": round((h[2] / h[1] * 100) if h[1] > 0 else 0, 1)
                }
                for h in hourly_effectiveness
            ]
        }
    
    # Helper methods
    def _get_friend_detections_count(self) -> int:
        """Count detections that are likely friends."""
        return len(self.session.exec(
            select(Detection)
            .where(Detection.detected_foe == None)
            .where(Detection.status == DetectionStatus.PROCESSED)
        ).all())
    
    def _get_friend_detections(self) -> List[Detection]:
        """Get detections that are likely friends."""
        return self.session.exec(
            select(Detection)
            .where(Detection.detected_foe == None)
            .where(Detection.status == DetectionStatus.PROCESSED)
        ).all()
    
    def _get_untested_sounds(self) -> List[str]:
        """Get sounds that need more testing."""
        # Get all available sounds (this would be from your sounds directory)
        # For now, returning placeholder
        all_sounds = []  # TODO: Get from sound directory
        
        # Get tested sounds
        tested = self.session.exec(
            select(SoundStatistics.sound_file)
            .where(SoundStatistics.total_uses >= 5)
            .distinct()
        ).all()
        
        tested_files = set(tested)
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
        friend_counts = self.session.execute(
            text(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM detections
            WHERE detected_foe IS NULL
            AND created_at >= '{(datetime.now() - timedelta(days=30)).isoformat()}'
            GROUP BY DATE(created_at)
            ORDER BY date
            """)
        ).all()
        
        return {
            "dates": [f[0] for f in friend_counts],
            "counts": [f[1] for f in friend_counts]
        }
    
    def _analyze_deterrent_impact_on_friends(self) -> Dict[str, Any]:
        """Analyze how deterrents affect friendly creature appearances."""
        # Compare friend detections before and after deterrent events
        # Placeholder implementation
        return {
            "impact": "minimal",  # or "negative", "positive"
            "confidence": 0.75
        }