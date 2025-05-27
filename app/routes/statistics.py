"""Statistics page routes."""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.core.database import get_session
from app.core.templates import templates
from app.models.detection import Detection, Foe, DetectionStatus
from app.models.sound_effectiveness import SoundEffectiveness, SoundStatistics
from app.models.device import Device
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/", response_class=HTMLResponse, name="view_statistics")
async def statistics_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Render comprehensive statistics page."""
    stats_service = StatisticsService(session)
    
    # Get various statistics
    overview = stats_service.get_overview_stats()
    daily_trends = stats_service.get_daily_trends(days=30)
    hourly_patterns = stats_service.get_hourly_patterns()
    sound_effectiveness = stats_service.get_sound_effectiveness_rankings()
    foe_analytics = stats_service.get_foe_analytics()
    friend_analytics = stats_service.get_friend_analytics()
    camera_stats = stats_service.get_camera_statistics()
    cost_analytics = stats_service.get_cost_analytics()
    
    return templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "overview": overview,
            "daily_trends": daily_trends,
            "hourly_patterns": hourly_patterns,
            "sound_effectiveness": sound_effectiveness,
            "foe_analytics": foe_analytics,
            "friend_analytics": friend_analytics,
            "camera_stats": camera_stats,
            "cost_analytics": cost_analytics,
            "current_page": "statistics"
        }
    )


@router.get("/api/live-data")
async def get_live_statistics(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get live statistics data for real-time updates."""
    stats_service = StatisticsService(session)
    
    # Get last hour's data for live updates
    recent_detections = stats_service.get_recent_detections(hours=1)
    current_activity = stats_service.get_current_activity_level()
    
    return {
        "recent_detections": recent_detections,
        "current_activity": current_activity,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/effectiveness/{foe_type}")
async def get_foe_effectiveness_details(
    foe_type: str,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get detailed effectiveness data for a specific foe type."""
    stats_service = StatisticsService(session)
    
    return stats_service.get_detailed_foe_effectiveness(foe_type)