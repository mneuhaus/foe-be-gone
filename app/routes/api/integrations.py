"""API routes for integration management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.core.database import get_session
from app.core.responses import success_response, error_response
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


class IntegrationUpdate(BaseModel):
    """Schema for updating existing integration."""
    name: str | None = Field(default=None, description="Display name for this integration instance")
    config: Dict[str, Any] | None = Field(default=None, description="Integration-specific configuration")
    enabled: bool | None = Field(default=None, description="Whether integration is enabled")


class IntegrationResponse(BaseModel):
    """Response schema for integration."""
    id: str = Field(description="Unique identifier")
    integration_type: str = Field(description="Type of integration")
    name: str = Field(description="Display name")
    enabled: bool = Field(description="Whether integration is enabled")
    status: str = Field(description="Connection status")
    status_message: str | None = Field(description="Status details or error message")
    config: Dict[str, Any] = Field(default={}, description="Integration configuration")
    

@router.get("", response_model=list[IntegrationResponse], summary="List all integrations")
async def list_integrations(session: Session = Depends(get_session)):
    """List all integration instances.
    
    Returns a list of all configured camera integrations with their current status.
    """
    integrations = session.exec(select(IntegrationInstance)).all()
    return integrations


@router.get("/{integration_id}", response_model=IntegrationResponse, summary="Get integration by ID")
async def get_integration(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific integration by its ID."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return IntegrationResponse(
        id=integration.id,
        integration_type=integration.integration_type,
        name=integration.name,
        enabled=integration.enabled,
        status=integration.status,
        status_message=integration.status_message,
        config=integration.config
    )


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
    
    logger.info(f"Creating integration '{integration.name}' of type '{integration.integration_type}'")
    
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
        
        session.add(db_integration)
        session.commit()
        session.refresh(db_integration)
    except ValueError as e:
        logger.error(f"Invalid configuration for integration {db_integration.name}: {e}")
        session.rollback()
        db_integration.update_status("error", f"Configuration error: {str(e)}")
        session.add(db_integration)
        session.commit()
        session.refresh(db_integration)
    except ConnectionError as e:
        logger.error(f"Connection failed for integration {db_integration.name}: {e}")
        session.rollback()
        db_integration.update_status("error", f"Connection failed: {str(e)}")
        session.add(db_integration)
        session.commit()
        session.refresh(db_integration)
    except Exception as e:
        logger.exception(f"Unexpected error creating integration {db_integration.name}")
        session.rollback()
        db_integration.update_status("error", f"Unexpected error: {str(e)}")
        session.add(db_integration)
        session.commit()
        session.refresh(db_integration)
    
    return db_integration


@router.put("/{integration_id}", response_model=IntegrationResponse, summary="Update integration")
async def update_integration(
    integration_id: str,
    integration_update: IntegrationUpdate,
    session: Session = Depends(get_session)
):
    """Update an existing integration instance.
    
    Allows updating the integration name, configuration (host, API key, etc.), 
    and enabled status. When configuration is updated, the integration will 
    automatically reconnect with the new settings.
    """
    # Get existing integration
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    logger.info(f"Updating integration {integration.name} ({integration_id})")
    
    # Store old config for comparison
    old_config = integration.config_dict
    config_changed = False
    
    # Update fields if provided
    if integration_update.name is not None:
        integration.name = integration_update.name
        logger.info(f"Updated integration name to: {integration_update.name}")
    
    if integration_update.enabled is not None:
        integration.enabled = integration_update.enabled
        logger.info(f"Updated integration enabled status to: {integration_update.enabled}")
    
    if integration_update.config is not None:
        # Merge with existing config to preserve other settings
        new_config = old_config.copy()
        new_config.update(integration_update.config)
        integration.config_json = json.dumps(new_config)
        config_changed = True
        logger.info(f"Updated integration config: {list(integration_update.config.keys())}")
    
    integration.updated_at = datetime.utcnow()
    
    # If config changed, test the new connection
    if config_changed and integration.enabled:
        try:
            integration_class = get_integration_class(integration.integration_type)
            if integration_class:
                logger.info(f"Testing connection with new configuration...")
                integration_instance = integration_class(integration)
                
                # Test connection
                success = await integration_instance.test_connection()
                if success:
                    integration.update_status("connected", "Successfully connected with new configuration")
                    logger.info(f"Successfully connected integration {integration.name} with new config")
                else:
                    integration.update_status("error", "Failed to connect with new configuration")
                    logger.error(f"Failed to connect integration {integration.name} with new config")
            else:
                integration.update_status("error", f"Unknown integration type: {integration.integration_type}")
                
        except Exception as e:
            error_msg = f"Configuration update failed: {str(e)}"
            integration.update_status("error", error_msg)
            logger.error(f"Error testing new config for {integration.name}: {str(e)}")
            # Don't raise exception - save the config but mark as error
    
    session.add(integration)
    session.commit()
    session.refresh(integration)
    
    return integration


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Delete an integration instance."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # First, delete all detections associated with devices from this integration
    from app.models.detection import Detection
    devices = session.exec(select(Device).where(Device.integration_id == integration_id)).all()
    
    for device in devices:
        # Delete all detections for this device
        detections = session.exec(select(Detection).where(Detection.device_id == device.id)).all()
        for detection in detections:
            session.delete(detection)
    
    # Now delete all devices associated with this integration
    for device in devices:
        session.delete(device)
    
    # Finally delete the integration itself
    session.delete(integration)
    session.commit()
    
    return success_response("Integration deleted successfully")


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
        return error_response(f"Unknown integration type: {integration.integration_type}")
    
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
            
            return success_response(
                f"Connected successfully. Found {len(devices)} device(s).",
                {"device_count": len(devices)}
            )
        else:
            return error_response("Failed to connect to integration")
    except ValueError as e:
        logger.error(f"Invalid configuration for integration {integration.name}: {e}")
        session.rollback()
        return error_response(f"Configuration error: {str(e)}")
    except ConnectionError as e:
        logger.error(f"Connection failed for integration {integration.name}: {e}")
        session.rollback()
        return error_response(f"Connection failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error testing integration {integration.name}")
        session.rollback()
        return error_response(f"Unexpected error: {str(e)}")


@router.get("/{integration_id}/test-scenarios")
async def get_test_scenarios(
    integration_id: str,
    session: Session = Depends(get_session)
):
    """Get available test scenarios for dummy integration."""
    integration = session.get(IntegrationInstance, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if integration.integration_type != "dummy_surveillance":
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
    
    if integration.integration_type != "dummy_surveillance":
        raise HTTPException(status_code=400, detail="Test scenarios only available for dummy integrations")
    
    dummy = DummySurveillanceIntegration(integration)
    result = dummy.set_test_scenario(scenario)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Update device image URL
    devices = session.exec(
        select(Device).where(Device.integration_id == integration_id)
    ).all()
    
    for device in devices:
        if device.device_type == "camera":
            device.current_image_url = result.get("image_path", "public/dummy-surveillance/nothing/Terrassentür  - 5-26-2025, 09.07.18 GMT+2.jpg")
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
            
            try:
                response = await integration_instance._client.get(url)
            except httpx.ConnectError as e:
                logger.error(f"Connection failed to UniFi Protect: {str(e)}")
                raise HTTPException(status_code=503, detail="Unable to connect to UniFi Protect. Please check your connection settings.")
            except httpx.TimeoutException:
                logger.error("Connection timeout to UniFi Protect")
                raise HTTPException(status_code=504, detail="Connection timeout to UniFi Protect")
            except Exception as e:
                logger.error(f"Unexpected error connecting to UniFi Protect: {type(e).__name__}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"UniFi API returned status {response.status_code}")
            
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
    enabled_cameras = camera_selection.get("enabled_cameras", [])
    config["enabled_cameras"] = enabled_cameras
    integration.config_json = json.dumps(config)
    
    # Get existing devices
    existing_devices = session.exec(
        select(Device).where(Device.integration_id == integration_id)
    ).all()
    existing_device_ids = {device.id for device in existing_devices}
    
    # AUTO-CLEANUP: Detect and remove duplicate devices before processing
    # Group existing devices by name to find duplicates
    devices_by_name = {}
    duplicates_to_remove = []
    
    for device in existing_devices:
        if device.name in devices_by_name:
            # Found a duplicate! Keep the newer one (or one with more recent activity)
            existing_device = devices_by_name[device.name]
            if device.updated_at > existing_device.updated_at:
                # Current device is newer, mark the old one for removal
                duplicates_to_remove.append(existing_device)
                devices_by_name[device.name] = device
            else:
                # Existing device is newer, mark current one for removal
                duplicates_to_remove.append(device)
        else:
            devices_by_name[device.name] = device
    
    # Remove duplicates
    if duplicates_to_remove:
        logger.info(f"Auto-cleanup: Removing {len(duplicates_to_remove)} duplicate cameras")
        for duplicate in duplicates_to_remove:
            # Check if duplicate has detections
            from app.models.detection import Detection
            detection_count = session.exec(
                select(Detection).where(Detection.device_id == duplicate.id).limit(1)
            ).first()
            
            if detection_count:
                # If device has detections, disable it instead of deleting
                duplicate.status = "disabled"
                duplicate.update_status("disabled - duplicate removed")
                logger.info(f"Disabled duplicate camera with detections: {duplicate.name}")
            else:
                # Safe to delete if no detections reference it
                session.delete(duplicate)
                logger.info(f"Deleted duplicate camera: {duplicate.name}")
        
        # Update our tracking lists after cleanup
        existing_devices = [d for d in existing_devices if d not in duplicates_to_remove]
        existing_device_ids = {device.id for device in existing_devices}
    
    # Get devices that would be created for the new selection
    integration_class = get_integration_class(integration.integration_type)
    integration_instance = integration_class(integration)
    
    try:
        new_devices = await integration_instance.get_devices()
        new_device_ids = {device.id for device in new_devices}
        
        # Only delete devices that are no longer in the selection
        devices_to_delete = existing_device_ids - new_device_ids
        for device in existing_devices:
            if device.id in devices_to_delete:
                # Check if this device has any detections
                from app.models.detection import Detection
                detection_count = session.exec(
                    select(Detection).where(Detection.device_id == device.id).limit(1)
                ).first()
                
                if detection_count:
                    # If device has detections, disable it instead of deleting
                    device.status = "disabled"
                    device.update_status("disabled")
                else:
                    # Safe to delete if no detections reference it
                    session.delete(device)
        
        # Add new devices that don't exist yet
        for new_device in new_devices:
            if new_device.id not in existing_device_ids:
                session.add(new_device)
                
        # Update existing devices that are still enabled
        for existing_device in existing_devices:
            if existing_device.id in new_device_ids:
                # Find corresponding new device to get updated properties
                for new_device in new_devices:
                    if new_device.id == existing_device.id:
                        existing_device.status = "online"
                        existing_device.name = new_device.name
                        existing_device.device_metadata = new_device.device_metadata
                        break
        
        devices = new_devices
        
    except Exception as e:
        integration.update_status("error", f"Failed to update devices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update camera selection: {str(e)}")
    
    session.commit()
    
    return success_response(f"Updated camera selection. {len(enabled_cameras)} camera(s) enabled.", {"device_count": len(enabled_cameras)})


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
                    return error_response("Camera ID not found. Please test the integration connection first.")
            
            # Get the device interface
            device_interface = await integration_instance.get_device(camera_id)
            if not device_interface:
                return error_response("Camera not found in UniFi system")
            
            # Test talkback
            success = await device_interface.test_talkback()
            
            if success:
                return success_response("Talkback test initiated")
            else:
                return error_response("Failed to initiate talkback")
    
    except Exception as e:
        return error_response(f"Talkback error: {str(e)}")


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