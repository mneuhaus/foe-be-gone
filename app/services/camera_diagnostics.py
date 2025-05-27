"""Camera diagnostics service for troubleshooting issues."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from sqlmodel import select
from app.core.session import get_db_session
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance

logger = logging.getLogger(__name__)


class CameraDiagnostics:
    """Service for diagnosing camera issues and tracking camera health."""
    
    def __init__(self):
        self.camera_errors: Dict[str, List[Dict[str, Any]]] = {}
        self.max_error_history = 100  # Keep last 100 errors per camera
    
    def record_camera_error(self, camera_id: str, camera_name: str, error_type: str, error_details: str):
        """Record a camera error for diagnostics."""
        if camera_id not in self.camera_errors:
            self.camera_errors[camera_id] = []
        
        error_record = {
            "timestamp": datetime.utcnow(),
            "camera_name": camera_name,
            "error_type": error_type,
            "error_details": error_details
        }
        
        self.camera_errors[camera_id].append(error_record)
        
        # Keep only recent errors
        if len(self.camera_errors[camera_id]) > self.max_error_history:
            self.camera_errors[camera_id] = self.camera_errors[camera_id][-self.max_error_history:]
        
        logger.warning(f"Camera error recorded - {camera_name}: {error_type} - {error_details}")
    
    def get_camera_health_status(self) -> Dict[str, Any]:
        """Get health status for all cameras."""
        with get_db_session() as session:
            # Get all cameras
            cameras = session.exec(
                select(Device)
                .join(IntegrationInstance)
                .where(Device.device_type == "camera")
            ).all()
            
            health_status = {
                "total_cameras": len(cameras),
                "healthy_cameras": 0,
                "unhealthy_cameras": 0,
                "camera_details": []
            }
            
            now = datetime.utcnow()
            error_threshold = now - timedelta(minutes=5)  # Errors in last 5 minutes
            
            for camera in cameras:
                camera_id = camera.id
                recent_errors = []
                
                if camera_id in self.camera_errors:
                    recent_errors = [
                        err for err in self.camera_errors[camera_id]
                        if err["timestamp"] > error_threshold
                    ]
                
                is_healthy = len(recent_errors) == 0
                
                if is_healthy:
                    health_status["healthy_cameras"] += 1
                else:
                    health_status["unhealthy_cameras"] += 1
                
                camera_detail = {
                    "id": camera_id,
                    "name": camera.name,
                    "status": camera.status,
                    "is_healthy": is_healthy,
                    "recent_error_count": len(recent_errors),
                    "last_error": recent_errors[-1] if recent_errors else None,
                    "integration": camera.integration.name if camera.integration else "Unknown"
                }
                
                health_status["camera_details"].append(camera_detail)
            
            return health_status
    
    def get_camera_error_history(self, camera_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get error history for a specific camera."""
        if camera_id not in self.camera_errors:
            return []
        
        # Return most recent errors
        return self.camera_errors[camera_id][-limit:]
    
    def suggest_fixes(self, camera_id: str) -> List[str]:
        """Suggest potential fixes based on error patterns."""
        if camera_id not in self.camera_errors:
            return ["No errors recorded for this camera"]
        
        recent_errors = self.camera_errors[camera_id][-10:]  # Last 10 errors
        suggestions = []
        
        # Check for consistent 500 errors
        if all(err["error_type"] == "HTTP 500" for err in recent_errors[-3:]):
            suggestions.append("Camera appears offline or disconnected. Check:")
            suggestions.append("- Camera power and network connection")
            suggestions.append("- UniFi Protect app to verify camera status")
            suggestions.append("- Camera firmware updates in UniFi Protect")
        
        # Check for timeout errors
        if any("timeout" in err["error_details"].lower() for err in recent_errors):
            suggestions.append("Network connectivity issues detected:")
            suggestions.append("- Check network path to camera")
            suggestions.append("- Verify firewall rules")
            suggestions.append("- Consider increasing timeout values")
        
        # Check for authentication errors
        if any("401" in err["error_type"] or "403" in err["error_type"] for err in recent_errors):
            suggestions.append("Authentication issues detected:")
            suggestions.append("- Re-authenticate with UniFi Protect")
            suggestions.append("- Check API permissions")
            suggestions.append("- Verify integration credentials")
        
        return suggestions if suggestions else ["No specific issues detected. Monitor camera behavior."]


# Global diagnostics instance
camera_diagnostics = CameraDiagnostics()