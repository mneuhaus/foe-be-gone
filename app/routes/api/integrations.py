"""API routes for integration management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.core.database import get_session
from app.models.integration_instance import IntegrationInstance
from app.models.device import Device
from app.integrations.dummy_surveillance import DummySurveillanceIntegration
from app.integrations import get_integration_class
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class IntegrationCreate(BaseModel):
    """Schema for creating new integration."""
    integration_type: str = Field(description="Type of integration (e.g., 'dummy_surveillance', 'unifi_protect')")
    name: str = Field(description="Display name for this integration instance")
    config: Dict[str, Any] = Field(default={}, description="Integration-specific configuration")


class IntegrationResponse(BaseModel):
    """Response schema for integration."""
    id: str = Field(description="Unique identifier")
    integration_type: str = Field(description="Type of integration")
    name: str = Field(description="Display name")
    enabled: bool = Field(description="Whether integration is enabled")
    status: str = Field(description="Connection status")
    status_message: str | None = Field(description="Status details or error message")
    

@router.get("", response_model=list[IntegrationResponse], summary="List all integrations")
async def list_integrations(session: Session = Depends(get_session)):
    """List all integration instances.
    
    Returns a list of all configured camera integrations with their current status.
    """
    integrations = session.exec(select(IntegrationInstance)).all()
    return integrations


@router.post("", response_model=IntegrationResponse, summary="Create new integration")
async def create_integration(
    integration: IntegrationCreate,
    session: Session = Depends(get_session)
):
    """Create a new integration instance."""
    # Validate integration type
    integration_class = get_integration_class(integration.integration_type)
    if not integration_class:
        raise HTTPException(status_code=400, detail="Invalid integration type")
    
    print(f"Creating integration with config: {integration.config}")
    
    # Create integration instance
    db_integration = IntegrationInstance(
        integration_type=integration.integration_type,
        name=integration.name,
        config_json=json.dumps(integration.config) if integration.config else "{}"
    )
    
    session.add(db_integration)
    session.commit()
    session.refresh(db_integration)
    
    # Try to connect to the integration
    integration_instance = integration_class(db_integration)
    
    try:
        if await integration_instance.test_connection():
            db_integration.update_status("connected", "Successfully connected")
            
            # Get devices from the integration
            devices = await integration_instance.get_devices()
            for device in devices:
                session.add(device)
        else:
            db_integration.update_status("error", "Failed to connect")
    except Exception as e:
        db_integration.update_status("error", str(e))
    
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
    
    integration_class = get_integration_class(integration.integration_type)
    if not integration_class:
        return {
            "success": False,
            "message": "Unknown integration type"
        }
    
    integration_instance = integration_class(integration)
    
    try:
        connected = await integration_instance.test_connection()
        
        if connected:
            # Remove existing devices before getting new ones
            existing_devices = session.exec(
                select(Device).where(Device.integration_id == integration_id)
            ).all()
            for device in existing_devices:
                session.delete(device)
            
            # Get and save new devices
            devices = await integration_instance.get_devices()
            for device in devices:
                session.add(device)
            
            # Update integration status
            integration.update_status("connected", "Successfully connected")
            session.add(integration)
            session.commit()
            
            return {
                "success": True,
                "message": f"Connected successfully. Found {len(devices)} device(s)."
            }
        else:
            return {
                "success": False,
                "message": "Failed to connect to integration"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
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


@router.get("/{integration_id}/cameras")
async def get_cameras(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Get all available cameras from UniFi Protect."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type != "unifi_protect":
        raise HTTPException(status_code=400, detail="Camera listing only available for UniFi Protect")
    
    integration_class = get_integration_class(integration.integration_type)
    integration_instance = integration_class(integration)
    
    try:
        # Get all cameras from UniFi
        async with integration_instance:
            if not integration_instance._client:
                integration_instance._init_client()
            
            url = f"{integration_instance.host}/proxy/protect/integration/v1/cameras"
            response = await integration_instance._client.get(url)
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch cameras from UniFi")
            
            cameras = response.json()
            enabled_cameras = integration.config_dict.get("enabled_cameras", [])
            
            # Format camera data with enabled status
            camera_list = []
            for camera in cameras:
                camera_list.append({
                    "id": camera["id"],
                    "name": camera["name"],
                    "model": camera.get("modelKey", "Unknown"),
                    "state": camera.get("state", "UNKNOWN"),
                    "enabled": camera["id"] in enabled_cameras
                })
            
            return {"cameras": camera_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cameras: {str(e)}")


@router.put("/{integration_id}/cameras")
async def update_camera_selection(
    integration_id: str,
    camera_selection: Dict[str, list] = {"enabled_cameras": []},
    session: Session = Depends(get_session)
):
    """Update camera selection for UniFi Protect integration."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type != "unifi_protect":
        raise HTTPException(status_code=400, detail="Camera selection only available for UniFi Protect")
    
    # Update configuration with selected cameras
    config = integration.config_dict
    config["enabled_cameras"] = camera_selection.get("enabled_cameras", [])
    integration.config_json = json.dumps(config)
    
    # Remove existing devices
    existing_devices = session.exec(
        select(Device).where(Device.integration_id == integration_id)
    ).all()
    for device in existing_devices:
        session.delete(device)
    
    # Recreate devices based on new selection
    integration_class = get_integration_class(integration.integration_type)
    integration_instance = integration_class(integration)
    
    try:
        devices = await integration_instance.get_devices()
        for device in devices:
            session.add(device)
    except Exception as e:
        integration.update_status("error", f"Failed to update devices: {str(e)}")
    
    session.commit()
    
    return {"success": True, "message": f"Updated camera selection. {len(devices)} camera(s) enabled."}


@router.post("/{integration_id}/devices/{device_id}/talkback")
async def test_device_talkback(
    integration_id: str,
    device_id: str,
    session: Session = Depends(get_session)
):
    """Test talkback functionality for a camera device."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Get the device
    device = session.exec(
        select(Device).where(
            Device.integration_id == integration_id,
            Device.id == device_id
        )
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.device_type != "camera":
        raise HTTPException(status_code=400, detail="Talkback only available for camera devices")
    
    # Get the integration instance
    integration_class = get_integration_class(integration.integration_type)
    integration_instance = integration_class(integration)
    
    try:
        async with integration_instance:
            # For UniFi Protect, the device_id in our database corresponds to the device.id (UUID)
            # but we need the UniFi camera ID from metadata
            logger.info(f"Device metadata: {device.device_metadata}")
            camera_id = device.device_metadata.get("camera_id")
            logger.info(f"Camera ID from metadata: {camera_id}")
            
            # If camera_id is not in metadata, try using the device_id directly
            # (this might happen with older device records)
            if not camera_id:
                # Let's refresh the device data by testing the integration
                devices = await integration_instance.get_devices()
                # Find our device in the fresh list
                for fresh_device in devices:
                    if fresh_device.name == device.name:
                        camera_id = fresh_device.device_metadata.get("camera_id")
                        break
                
                if not camera_id:
                    return {"success": False, "message": "Camera ID not found. Please test the integration connection first."}
            
            # Get the device interface
            device_interface = await integration_instance.get_device(camera_id)
            if not device_interface:
                return {"success": False, "message": "Camera not found in UniFi system"}
            
            # Test talkback
            success = await device_interface.test_talkback()
            
            if success:
                return {"success": True, "message": "Talkback test initiated"}
            else:
                return {"success": False, "message": "Failed to initiate talkback"}
    
    except Exception as e:
        return {"success": False, "message": f"Talkback error: {str(e)}"}


@router.get("/{integration_id}/devices/{device_id}/snapshot")
async def get_device_snapshot(
    integration_id: str,
    device_id: str,
    session: Session = Depends(get_session)
):
    """Get current snapshot from a camera device."""
    from fastapi.responses import Response
    
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # For UniFi cameras, device_id is the UniFi camera ID
    integration_class = get_integration_class(integration.integration_type)
    integration_instance = integration_class(integration)
    
    try:
        async with integration_instance:
            if not integration_instance._client:
                integration_instance._init_client()
            
            # Get snapshot from UniFi
            url = f"{integration_instance.host}/proxy/protect/integration/v1/cameras/{device_id}/snapshot"
            response = await integration_instance._client.get(url)
            
            if response.status_code == 200:
                return Response(
                    content=response.content,
                    media_type="image/jpeg",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to get snapshot")
    
    except Exception as e:
        logger.error(f"Error getting snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Snapshot error: {str(e)}")