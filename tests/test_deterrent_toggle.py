"""Tests for deterrent toggle functionality."""

import pytest
from playwright.sync_api import Page, expect


def test_deterrent_toggle_visibility(page: Page):
    """Test that the deterrent toggle is visible in the navbar."""
    # Navigate to the dashboard
    page.goto("/")
    
    # Check that the deterrent toggle is present
    deterrent_toggle = page.locator("#deterrent-toggle-wrapper")
    expect(deterrent_toggle).to_be_visible()
    
    # Check that the toggle has a proper title/tooltip
    expect(deterrent_toggle).to_have_attribute("title", "Deterrents")


def test_deterrent_toggle_initial_state(page: Page):
    """Test that the deterrent toggle loads with the correct initial state."""
    # Navigate to the dashboard
    page.goto("/")
    
    # Wait for the toggle state to be loaded
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    
    # Check that the toggle is checked by default (deterrents enabled)
    deterrent_toggle = page.locator("#deterrent-toggle")
    expect(deterrent_toggle).to_be_checked()


def test_deterrent_toggle_functionality(page: Page):
    """Test that toggling the deterrent switch updates the state."""
    # Navigate to the dashboard
    page.goto("/")
    
    # Wait for the toggle to be ready
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    
    # Get the initial state
    deterrent_toggle = page.locator("#deterrent-toggle")
    initial_state = deterrent_toggle.is_checked()
    
    # Click the toggle
    page.locator("#deterrent-toggle-wrapper").click()
    
    # Wait for the state to update
    page.wait_for_timeout(500)
    
    # Check that the state has changed
    new_state = deterrent_toggle.is_checked()
    assert new_state != initial_state
    
    # Toggle back
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    
    # Check that it's back to the original state
    final_state = deterrent_toggle.is_checked()
    assert final_state == initial_state


def test_deterrent_api_endpoint(page: Page):
    """Test that the deterrent API endpoints work correctly."""
    # Navigate to the dashboard to ensure the app is running
    page.goto("/")
    
    # Test the status endpoint
    response = page.request.get("/api/settings/deterrents/status")
    assert response.ok
    data = response.json()
    assert "deterrents_enabled" in data
    assert isinstance(data["deterrents_enabled"], bool)
    
    # Test the toggle endpoint
    response = page.request.put("/api/settings/deterrents/toggle")
    assert response.ok
    toggle_data = response.json()
    assert "deterrents_enabled" in toggle_data
    
    # Verify the state changed
    response = page.request.get("/api/settings/deterrents/status")
    status_data = response.json()
    assert status_data["deterrents_enabled"] == toggle_data["deterrents_enabled"]
    
    # Toggle back to original state
    page.request.put("/api/settings/deterrents/toggle")


def test_deterrent_toggle_persists_across_pages(page: Page):
    """Test that the deterrent toggle state persists when navigating between pages."""
    # Navigate to the dashboard
    page.goto("/")
    
    # Wait for the toggle to be ready
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    
    # Get the initial state
    deterrent_toggle = page.locator("#deterrent-toggle")
    initial_state = deterrent_toggle.is_checked()
    
    # Toggle the state
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    new_state = deterrent_toggle.is_checked()
    
    # Navigate to detections page
    page.goto("/detections")
    
    # Check that the toggle still exists and has the same state
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    deterrent_toggle_on_detections = page.locator("#deterrent-toggle")
    expect(deterrent_toggle_on_detections).to_be_visible()
    assert deterrent_toggle_on_detections.is_checked() == new_state
    
    # Navigate back to dashboard
    page.goto("/")
    
    # Verify state is still preserved
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    deterrent_toggle_on_dashboard = page.locator("#deterrent-toggle")
    assert deterrent_toggle_on_dashboard.is_checked() == new_state
    
    # Toggle back to original state
    if deterrent_toggle_on_dashboard.is_checked() != initial_state:
        page.locator("#deterrent-toggle-wrapper").click()


def test_deterrent_toggle_visual_feedback(page: Page):
    """Test that the deterrent toggle provides visual feedback when toggled."""
    # Navigate to the dashboard
    page.goto("/")
    
    # Wait for the toggle to be ready
    page.wait_for_function("() => document.getElementById('deterrent-toggle') !== null")
    
    # Check that the sound-on icon is visible when enabled
    sound_on_icon = page.locator("#deterrent-toggle-wrapper .swap-on")
    sound_off_icon = page.locator("#deterrent-toggle-wrapper .swap-off")
    
    # Initially, deterrents should be enabled (showing sound-on icon)
    expect(sound_on_icon).to_be_visible()
    
    # Toggle off
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    
    # Sound-off icon should now be visible
    expect(sound_off_icon).to_be_visible()
    
    # Toggle back on
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    
    # Sound-on icon should be visible again
    expect(sound_on_icon).to_be_visible()


def test_deterrent_setting_in_general_settings(page: Page, session):
    """Test that the deterrent setting is properly stored in the database."""
    from app.services.settings_service import SettingsService
    
    # Check initial state in database
    settings_service = SettingsService(session)
    initial_db_state = settings_service.get_deterrents_enabled()
    
    # Navigate to the dashboard
    page.goto("/")
    
    # Toggle the deterrent state
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    
    # Check that the database was updated
    new_db_state = settings_service.get_deterrents_enabled()
    assert new_db_state != initial_db_state
    
    # Toggle back
    page.locator("#deterrent-toggle-wrapper").click()
    page.wait_for_timeout(500)
    
    # Verify database is back to original state
    final_db_state = settings_service.get_deterrents_enabled()
    assert final_db_state == initial_db_state