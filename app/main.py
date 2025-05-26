"""
FastAPI application for Foe Be Gone - Wildlife Detection & Deterrent System
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.core.config import config
from app.core.database import create_db_and_tables, get_session, engine
from app.routes import settings, detections
from app.routes.api import integrations
from app.services.detection_worker import detection_worker
from app.models.setting import Setting
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance

# Validate configuration before setting up logging
config.validate()

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    create_db_and_tables()
    # Load persisted detection interval if set
    try:
        with Session(engine) as session:
            setting = session.get(Setting, 'detection_interval')
            if setting and setting.value.isdigit():
                detection_worker.check_interval = int(setting.value)
                logging.getLogger(__name__).info(
                    f"Loaded persisted detection interval: {detection_worker.check_interval}s"
                )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load persisted settings: {e}")
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
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount("/data", StaticFiles(directory="data"), name="data")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(settings.router)
app.include_router(integrations.router)
app.include_router(detections.router)

# Note: Database creation is now handled in the lifespan context manager


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    """Dashboard page with system overview"""
    
    # Get all camera devices from connected integrations
    cameras = session.exec(
        select(Device)
        .join(IntegrationInstance)
        .where(Device.device_type == "camera")
        .where(IntegrationInstance.status == "connected")
        .where(IntegrationInstance.enabled == True)
    ).all()
    
    context = {
        "request": request,
        "title": "Dashboard",
        "page": "dashboard",
        "cameras": cameras
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)