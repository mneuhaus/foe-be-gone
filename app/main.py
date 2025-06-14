"""
FastAPI application for Foe Be Gone - Wildlife Detection & Deterrent System
"""

import logging
import logging.handlers
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.core.config import config
from app.core.database import create_db_and_tables, get_session, engine
from app.core.session import get_db_session
from app.routes import settings, detections, statistics, logs
from app.routes.api import integrations
from app.routes.api import detections as api_detections
from app.routes.api import settings as api_settings
from app.routes.api import test_images as api_test_images
from app.services.detection_worker import detection_worker
from app.services.settings_service import SettingsService
from app.models.setting import Setting
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.models.test_image import TestImage, GroundTruthLabel, TestResult, TestRun
from app.core.templates import format_datetime_tz

# Validate configuration before setting up logging
config.validate()

# Create logs directory if it doesn't exist
# Use /data/logs for Home Assistant addon, or local logs directory
if os.path.exists("/data"):
    logs_dir = Path("/data/logs")
else:
    logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Set up logging with both console and file handlers
logger = logging.getLogger()
logger.setLevel(getattr(logging, config.LOG_LEVEL))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    logs_dir / "foe_be_gone.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    create_db_and_tables()
    
    # Initialize default settings and load persisted values
    with get_db_session() as session:
        settings_service = SettingsService(session)
        settings_service.initialize_defaults()
        
        # Load persisted detection interval
        detection_worker.check_interval = settings_service.get_detection_interval()
        logging.getLogger(__name__).info(
            f"Loaded detection interval: {detection_worker.check_interval}s"
        )
    
    # Start worker
    await detection_worker.start()
    yield
    # Shutdown
    await detection_worker.stop()

# Initialize FastAPI app
app = FastAPI(
    title="Foe Be Gone",
    description="AI-powered wildlife detection and deterrent system",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "dashboard",
            "description": "Main dashboard and UI pages"
        },
        {
            "name": "detections",
            "description": "Detection management and viewing"
        },
        {
            "name": "settings",
            "description": "System configuration and settings"
        },
        {
            "name": "integrations",
            "description": "Camera integration management"
        },
        {
            "name": "statistics",
            "description": "System analytics and reporting"
        },
        {
            "name": "health",
            "description": "System health and status"
        },
        {
            "name": "logs",
            "description": "Application log viewing and management"
        }
    ]
)

# Home Assistant Ingress IP filtering middleware
@app.middleware("http")
async def ingress_security_middleware(request: Request, call_next):
    """Security middleware for Home Assistant Ingress.
    
    Only allow connections from Home Assistant Ingress (172.30.32.2),
    localhost (for development), and local network (10.0.42.*).
    """
    client_ip = request.client.host if request.client else None
    
    # Allow localhost for development
    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        return await call_next(request)
    
    # Allow Home Assistant Ingress IP
    if client_ip == "172.30.32.2":
        return await call_next(request)
    
    # Allow local network 10.0.42.*
    if client_ip and client_ip.startswith("10.0.42."):
        return await call_next(request)
    
    # In development mode, allow all connections
    from app.core.config import config
    if getattr(config, 'DEV_MODE', False):
        return await call_next(request)
    
    # Block all other IPs when running in production
    from fastapi import HTTPException
    logger.warning(f"Blocked access from unauthorized IP: {client_ip}")
    raise HTTPException(status_code=403, detail="Access denied")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/sounds", StaticFiles(directory="public/sounds"), name="sounds")

# Import shared templates
from app.core.templates import templates

# Include routers
app.include_router(settings.router)
app.include_router(integrations.router)
app.include_router(detections.router)
app.include_router(statistics.router)
app.include_router(logs.router)
app.include_router(api_detections.router)
app.include_router(api_settings.router)
app.include_router(api_test_images.router)

# Import and include providers router
from app.routes import providers
app.include_router(providers.router)

# Import and include test images router
from app.routes import test_images
app.include_router(test_images.router)

# Add API documentation info
@app.get("/api", tags=["documentation"], summary="API Documentation")
async def api_docs_redirect():
    """Redirect to the interactive API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

# Note: Database creation is now handled in the lifespan context manager


@app.get("/", response_class=HTMLResponse, tags=["dashboard"], summary="Main dashboard", name="dashboard")
async def dashboard(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Dashboard page with system overview.
    
    Shows active cameras and recent detection activity.
    """
    from app.services.statistics_service import StatisticsService
    from datetime import datetime, timedelta
    
    # Get all camera devices from connected integrations
    cameras = session.exec(
        select(Device)
        .join(IntegrationInstance)
        .where(Device.device_type == "camera")
        .where(IntegrationInstance.status == "connected")
        .where(IntegrationInstance.enabled == True)
    ).all()
    
    # Get basic statistics for overview cards
    stats_service = StatisticsService(session)
    overview_stats = stats_service.get_overview_stats()
    
    # Calculate activity status
    activity_status = "Quiet"
    last_detection_time = "No recent activity"
    
    if overview_stats.get('detections_today', 0) > 0:
        # Get last detection time
        from app.models.detection import Detection
        last_detection = session.exec(
            select(Detection).order_by(Detection.timestamp.desc()).limit(1)
        ).first()
        
        if last_detection:
            time_diff = datetime.utcnow() - last_detection.timestamp
            if time_diff < timedelta(hours=1):
                activity_status = "Active"
                minutes_ago = int(time_diff.total_seconds() / 60)
                last_detection_time = f"{minutes_ago}m ago" if minutes_ago > 0 else "Just now"
            elif time_diff < timedelta(hours=6):
                activity_status = "Recent"
                hours_ago = int(time_diff.total_seconds() / 3600)
                last_detection_time = f"{hours_ago}h ago"
            else:
                # Get timezone setting
                settings_service = SettingsService(session)
                timezone = settings_service.get_timezone()
                last_detection_time = format_datetime_tz(last_detection.timestamp, timezone, "%m/%d %H:%M")
    
    # Get system status
    settings_service = SettingsService(session)
    camera_tracking_enabled = settings_service.get_camera_tracking_enabled()
    deterrents_enabled = settings_service.get_deterrents_enabled()
    
    # Prepare stats for template
    stats = {
        'total_detections': overview_stats.get('total_detections', 0),
        'detections_today': overview_stats.get('detections_today', 0),
        'success_rate': overview_stats.get('success_rate', 0),
        'successful_deterrents': overview_stats.get('successful_deterrents', 0),
        'most_common_foe': overview_stats.get('most_common_foe', 'None'),
        'most_common_foe_count': overview_stats.get('most_common_foe_count', 0),
        'activity_status': activity_status,
        'last_detection_time': last_detection_time,
        'camera_tracking_enabled': camera_tracking_enabled,
        'deterrents_enabled': deterrents_enabled
    }
    
    context = {
        "request": request,
        "title": "Dashboard",
        "current_page": "dashboard",
        "cameras": cameras,
        "stats": stats
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@app.get("/health", tags=["health"], summary="Health check endpoint")
async def health_check() -> dict[str, str]:
    """Health check endpoint.
    
    Returns:
        dict: Status and version information
    """
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/debug/urls", tags=["health"], summary="Debug URL generation")
async def debug_urls(request: Request) -> dict:
    """Debug endpoint to check URL generation for Home Assistant ingress.
    
    Returns:
        dict: URL generation debug information
    """
    from app.core.url_helpers import get_base_url, static_url, url_for
    
    base_url = get_base_url(request)
    test_api_path = "api/integrations/test/devices/test/snapshot"
    test_static_path = "public/dummy-surveillance/nothing/test.jpg"
    
    return {
        "client_ip": request.client.host if request.client else None,
        "headers": dict(request.headers),
        "base_url": base_url,
        "ingress_path": request.headers.get("X-Ingress-Path", ""),
        "root_path": request.scope.get("root_path", ""),
        "url_examples": {
            "api_endpoint": static_url(request, "/" + test_api_path),
            "static_file": static_url(request, test_static_path),
            "dashboard_route": url_for(request, "dashboard")
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)