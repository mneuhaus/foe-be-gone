"""API routes for integration management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_session
from app.models.integration_instance import IntegrationInstance
from app.models.device import Device
from app.integrations.dummy_surveillance import DummySurveillanceIntegration

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class IntegrationCreate(BaseModel):
    """Schema for creating new integration."""
    integration_type: str
    name: str
    config: Dict[str, Any] = {}


class IntegrationResponse(BaseModel):
    """Response schema for integration."""
    id: str
    integration_type: str
    name: str
    enabled: bool
    status: str
    status_message: str | None
    

@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(session: Session = Depends(get_session)):
    """List all integration instances."""
    integrations = session.exec(select(IntegrationInstance)).all()
    return integrations


@router.post("", response_model=IntegrationResponse)
async def create_integration(
    integration: IntegrationCreate,
    session: Session = Depends(get_session)
):
    """Create a new integration instance."""
    # Validate integration type
    if integration.integration_type not in ["dummy-surveillance"]:
        raise HTTPException(status_code=400, detail="Invalid integration type")
    
    # Create integration instance
    db_integration = IntegrationInstance(
        integration_type=integration.integration_type,
        name=integration.name,
        config=integration.config
    )
    
    session.add(db_integration)
    session.commit()
    session.refresh(db_integration)
    
    # Try to connect to the integration
    if integration.integration_type == "dummy-surveillance":
        dummy = DummySurveillanceIntegration(db_integration.id, integration.config)
        if await dummy.connect():
            db_integration.update_status("connected", "Successfully connected")
            
            # Create devices from the integration
            cameras = dummy.get_cameras()
            for camera_data in cameras:
                device = Device(
                    integration_id=db_integration.id,
                    device_type="camera",
                    name=camera_data["name"],
                    model=camera_data.get("model"),
                    status=camera_data.get("status", "online"),
                    device_metadata={
                        "location": camera_data.get("location"),
                        "firmware_version": camera_data.get("firmware_version"),
                        "stream_url": camera_data.get("stream_url"),
                        "snapshot_url": camera_data.get("snapshot_url")
                    },
                    capabilities=camera_data.get("capabilities", {}),
                    current_image_url="/public/dummy-surveillance/nothing/Hühnerstall - 5-26-2025, 09.11.38 GMT+2.jpg"  # Default image
                )
                session.add(device)
        else:
            db_integration.update_status("error", "Failed to connect")
        
        session.add(db_integration)
        session.commit()
        session.refresh(db_integration)
    
    return db_integration


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Delete an integration instance."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Delete all devices associated with this integration
    devices = session.exec(select(Device).where(Device.integration_id == integration_id)).all()
    for device in devices:
        session.delete(device)
    
    session.delete(integration)
    session.commit()
    
    return {"success": True}


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Test an integration connection."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type == "dummy-surveillance":
        dummy = DummySurveillanceIntegration(integration.id, integration.config)
        connected = await dummy.connect()
        
        if connected:
            cameras = dummy.get_cameras()
            return {
                "success": True,
                "message": f"Connected successfully. Found {len(cameras)} camera(s)."
            }
        else:
            return {
                "success": False,
                "message": "Failed to connect to integration"
            }
    
    return {
        "success": False,
        "message": "Unknown integration type"
    }


@router.get("/{integration_id}/test-scenarios")
async def get_test_scenarios(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Get available test scenarios for dummy integration."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type != "dummy-surveillance":
        raise HTTPException(status_code=400, detail="Test scenarios only available for dummy integrations")
    
    scenarios = DummySurveillanceIntegration.get_test_scenarios()
    return {"scenarios": scenarios}


@router.post("/{integration_id}/test-scenario/{scenario}")
async def set_test_scenario(
    integration_id: str,
    scenario: str,
    session: Session = Depends(get_session)
):
    """Set a specific test scenario for dummy integration."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type != "dummy-surveillance":
        raise HTTPException(status_code=400, detail="Test scenarios only available for dummy integrations")
    
    dummy = DummySurveillanceIntegration(integration.id, integration.config)
    result = dummy.set_test_scenario(scenario)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Update device image URL
    devices = session.exec(
        select(Device).where(Device.integration_id == integration_id)
    ).all()
    
    for device in devices:
        if device.device_type == "camera":
            device.current_image_url = result.get("image_path", "/public/dummy-surveillance/nothing/1.jpg")
            device.updated_at = datetime.utcnow()
    
    session.commit()
    
    return result