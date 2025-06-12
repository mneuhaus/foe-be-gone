#!/usr/bin/env python3
"""
Fix database integrity issues with device_id constraints.
This script will:
1. Find detections with invalid device_id references
2. Either fix them by creating placeholder devices or removing orphaned detections
"""

import asyncio
from sqlmodel import Session, select
from app.models.detection import Detection
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance
from app.core.database import engine

async def fix_device_integrity():
    """Fix device_id integrity constraints."""
    
    with Session(engine) as session:
        # Find detections with invalid device_id references
        detections_with_invalid_devices = session.exec(
            select(Detection).where(
                ~Detection.device_id.in_(
                    select(Device.id)
                )
            )
        ).all()
        
        print(f"Found {len(detections_with_invalid_devices)} detections with invalid device_id references")
        
        if not detections_with_invalid_devices:
            print("No integrity issues found!")
            return
        
        # Group by device_id to see which devices are missing
        missing_device_ids = set()
        for detection in detections_with_invalid_devices:
            missing_device_ids.add(detection.device_id)
        
        print(f"Missing device IDs: {missing_device_ids}")
        
        # Option 1: Create placeholder devices for missing device IDs
        for device_id in missing_device_ids:
            print(f"Creating placeholder device for ID: {device_id}")
            
            # Try to find an integration to associate with
            integration = session.exec(select(IntegrationInstance)).first()
            
            placeholder_device = Device(
                id=device_id,
                integration_id=integration.id if integration else "unknown",
                device_type="camera",
                name=f"Placeholder Device {device_id}",
                status="disabled",
                device_metadata_json='{"placeholder": true}'
            )
            
            session.add(placeholder_device)
        
        # Commit the changes
        session.commit()
        print("Fixed device integrity constraints by creating placeholder devices")

if __name__ == "__main__":
    asyncio.run(fix_device_integrity())