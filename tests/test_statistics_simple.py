"""Simple test for statistics page."""
import pytest
from playwright.sync_api import Page, expect
from sqlmodel import Session
from sqlalchemy import text
from app.core.database import engine
from app.models.detection import Detection
from app.models.device import Device
from app.models.integration_instance import IntegrationInstance


def test_statistics_page_renders_empty(page: Page, live_server_url: str):
    """Test that statistics page renders even with no data."""
    # Clear any existing data
    with Session(engine) as session:
        # Use raw SQL to avoid deprecation warnings
        session.execute(text("DELETE FROM sound_effectiveness"))
        session.execute(text("DELETE FROM sound_statistics"))
        session.execute(text("DELETE FROM foes"))
        session.execute(text("DELETE FROM detections"))
        session.execute(text("DELETE FROM devices"))
        session.execute(text("DELETE FROM integration_instances"))
        session.commit()
    
    # Navigate to statistics page
    response = page.goto(f"{live_server_url}/statistics/")
    
    # Check response status
    assert response.status == 200, f"Page returned {response.status}"
    
    # Check page title
    expect(page).to_have_title("Statistics - Foe Be Gone")
    
    # Check main heading
    expect(page.locator("h1")).to_contain_text("System Analytics")
    
    # Check that stat cards are present (should be around 16)
    stat_cards = page.locator(".stat-card")
    expect(stat_cards).to_have_count(16, timeout=10000)
    
    # Check that charts are present (even if empty)
    expect(page.locator("#dailyTrendsChart")).to_be_visible()
    expect(page.locator("#hourlyPatternsChart")).to_be_visible()


def test_statistics_page_with_minimal_data(page: Page, live_server_url: str):
    """Test statistics page with minimal data."""
    with Session(engine) as session:
        # Clear existing data
        session.execute(text("DELETE FROM detections"))
        session.execute(text("DELETE FROM devices"))
        session.execute(text("DELETE FROM integration_instances"))
        
        # Add minimal data
        integration = IntegrationInstance(
            id="test-int",
            integration_type="test",
            name="Test Integration",
            status="connected"
        )
        session.add(integration)
        
        device = Device(
            id="test-dev",
            integration_id="test-int",
            device_type="camera",
            name="Test Camera",
            status="online"
        )
        session.add(device)
        
        # Add one detection
        from app.models.detection import DetectionStatus
        detection = Detection(
            device_id="test-dev",
            status=DetectionStatus.PROCESSED,
            detected_foe="crows",
            deterrent_effective=True,
            ai_cost=0.01
        )
        session.add(detection)
        session.commit()
    
    # Navigate to statistics page
    response = page.goto(f"{live_server_url}/statistics/")
    
    # Check response status
    assert response.status == 200
    
    # Check that statistics page renders successfully
    expect(page.locator("h1")).to_contain_text("System Analytics")
    
    # Check that stat values are present (even if 0)
    total_detections = page.locator(".stat-value").first
    expect(total_detections).to_be_visible()