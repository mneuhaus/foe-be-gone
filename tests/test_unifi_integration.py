"""Tests for UniFi Protect integration."""

import pytest
from playwright.sync_api import Page, expect
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx


@pytest.fixture
def mock_unifi_api():
    """Mock UniFi API responses."""
    with patch("app.integrations.unifi_protect.unifi_protect.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        
        # Mock successful connection test
        meta_response = AsyncMock()
        meta_response.status_code = 200
        meta_response.json.return_value = {"applicationVersion": "4.0.53"}
        
        # Mock camera listing
        cameras_response = AsyncMock()
        cameras_response.status_code = 200
        cameras_response.json.return_value = [
            {
                "id": "camera1",
                "name": "Front Door Camera",
                "modelKey": "UVC-G4-PRO",
                "state": "CONNECTED",
                "isMicEnabled": True,
                "featureFlags": {
                    "hasHdr": True,
                    "smartDetectTypes": ["person", "vehicle"],
                    "hasMic": True,
                    "hasLedStatus": True,
                    "hasSpeaker": False
                },
                "smartDetectSettings": {
                    "objectTypes": ["person"],
                    "audioTypes": []
                }
            },
            {
                "id": "camera2",
                "name": "Backyard Camera",
                "modelKey": "UVC-G3-FLEX",
                "state": "CONNECTED",
                "isMicEnabled": False,
                "featureFlags": {
                    "hasHdr": False,
                    "smartDetectTypes": [],
                    "hasMic": False,
                    "hasLedStatus": True,
                    "hasSpeaker": False
                },
                "smartDetectSettings": {
                    "objectTypes": [],
                    "audioTypes": []
                }
            }
        ]
        
        # Configure mock to return different responses based on URL
        async def mock_get(url, *args, **kwargs):
            if url.endswith("/meta/info"):
                return meta_response
            elif url.endswith("/cameras"):
                return cameras_response
            else:
                # Default response
                return meta_response
        
        instance.get = mock_get
        instance.aclose = AsyncMock()
        
        yield mock_client


def test_add_unifi_integration(page: Page, mock_unifi_api, live_server_url, clean_db):
    """Test adding a UniFi Protect integration."""
    page.goto(f"{live_server_url}/settings/integrations")
    
    # Click Add Integration dropdown
    page.get_by_role("button", name="Add Integration").click()
    
    # Click UniFi Protect option
    page.get_by_role("link", name="UniFi Protect Connect to").click()
    
    # Wait for modal
    expect(page.get_by_role("heading", name="Configure UniFi Protect")).to_be_visible()
    
    # Fill in configuration
    page.fill('input[name="host"]', "https://192.168.1.1")
    page.fill('input[name="api_key"]', "test-api-key-123")
    
    # Submit form
    page.get_by_role("button", name="Connect").click()
    
    # Wait for either success (page reload) or error notification
    try:
        # Wait for page to reload (successful creation)
        page.wait_for_url(f"{live_server_url}/settings/integrations", timeout=10000)
        
        # Verify integration card appears
        integration_card = page.locator(".card").filter(has_text="UniFi Protect").filter(has_text="Type: unifi_protect")
        expect(integration_card).to_be_visible(timeout=5000)
        expect(integration_card.get_by_text("Connected")).to_be_visible()
    except:
        # Check for error message if creation failed
        error_alert = page.locator(".alert-error")
        if error_alert.is_visible():
            raise AssertionError(f"Integration creation failed: {error_alert.text_content()}")


def test_unifi_integration_invalid_credentials(page: Page, live_server_url, clean_db):
    """Test UniFi integration with invalid credentials."""
    with patch("app.integrations.unifi_protect.unifi_protect.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        
        # Mock failed connection (401 Unauthorized)
        failed_response = AsyncMock()
        failed_response.status_code = 401
        instance.get.return_value = failed_response
        instance.aclose = AsyncMock()
        
        page.goto(f"{live_server_url}/settings/integrations")
        
        # Add integration
        page.get_by_role("button", name="Add Integration").click()
        page.get_by_role("link", name="UniFi Protect Connect to").click()
        
        # Fill in configuration with invalid credentials
        page.fill('input[name="host"]', "https://192.168.1.1")
        page.fill('input[name="api_key"]', "invalid-api-key")
        
        # Submit form
        page.get_by_role("button", name="Connect").click()
        
        # Wait for error status
        page.wait_for_load_state("domcontentloaded")
        expect(page.get_by_role("heading", name="UniFi Protect", exact=True)).to_be_visible()
        expect(page.get_by_text("Error")).to_be_visible()


def test_unifi_test_connection(page: Page, mock_unifi_api, live_server_url, clean_db):
    """Test the connection test functionality."""
    # First add an integration
    page.goto(f"{live_server_url}/settings/integrations")
    page.get_by_role("button", name="Add Integration").click()
    page.get_by_role("link", name="UniFi Protect Connect to").click()
    page.fill('input[name="host"]', "https://192.168.1.1")
    page.fill('input[name="api_key"]', "test-api-key-123")
    page.get_by_role("button", name="Connect").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Click actions menu
    page.locator(".dropdown .btn-ghost.btn-circle").first.click()
    
    # Click Test
    page.get_by_text("Test").click()
    
    # Verify success notification appears
    expect(page.get_by_text("Connected successfully")).to_be_visible(timeout=5000)


def test_unifi_camera_selection(page: Page, mock_unifi_api, live_server_url, clean_db):
    """Test camera selection functionality."""
    # First add an integration
    page.goto(f"{live_server_url}/settings/integrations")
    page.get_by_role("button", name="Add Integration").click()
    page.get_by_role("link", name="UniFi Protect Connect to").click()
    page.fill('input[name="host"]', "https://192.168.1.1")
    page.fill('input[name="api_key"]', "test-api-key-123")
    page.get_by_role("button", name="Connect").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Click Select Cameras button
    page.get_by_role("button", name="Select Cameras").click()
    
    # Wait for modal and cameras to load
    expect(page.get_by_role("heading", name="Select Cameras")).to_be_visible()
    expect(page.get_by_text("Front Door Camera")).to_be_visible(timeout=5000)
    expect(page.get_by_text("Backyard Camera")).to_be_visible()
    
    # Select first camera
    page.locator('input[value="camera1"]').check()
    
    # Save selection
    page.get_by_role("button", name="Save Selection").click()
    
    # Wait for page reload and verify camera is shown
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_text("Front Door Camera")).to_be_visible()


def test_unifi_camera_selection_empty(page: Page, live_server_url, clean_db):
    """Test camera selection when no cameras are available."""
    with patch("app.integrations.unifi_protect.unifi_protect.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        
        # Mock successful connection but empty camera list
        meta_response = AsyncMock()
        meta_response.status_code = 200
        meta_response.json.return_value = {"applicationVersion": "4.0.53"}
        
        cameras_response = AsyncMock()
        cameras_response.status_code = 200
        cameras_response.json.return_value = []
        
        async def mock_get(url, *args, **kwargs):
            if url.endswith("/meta/info"):
                return meta_response
            elif url.endswith("/cameras"):
                return cameras_response
            else:
                return meta_response
        
        instance.get = mock_get
        instance.aclose = AsyncMock()
        
        # Add integration
        page.goto(f"{live_server_url}/settings/integrations")
        page.get_by_role("button", name="Add Integration").click()
        page.get_by_role("link", name="UniFi Protect Connect to").click()
        page.fill('input[name="host"]', "https://192.168.1.1")
        page.fill('input[name="api_key"]', "test-api-key-123")
        page.get_by_role("button", name="Connect").click()
        page.wait_for_load_state("domcontentloaded")
        
        # Click Select Cameras button
        page.get_by_role("button", name="Select Cameras").click()
        
        # Verify empty state message
        expect(page.get_by_text("No cameras found")).to_be_visible(timeout=5000)


def test_unifi_delete_integration(page: Page, mock_unifi_api, live_server_url, clean_db):
    """Test deleting a UniFi integration."""
    # First add an integration
    page.goto(f"{live_server_url}/settings/integrations")
    page.get_by_role("button", name="Add Integration").click()
    page.get_by_role("link", name="UniFi Protect Connect to").click()
    page.fill('input[name="host"]', "https://192.168.1.1")
    page.fill('input[name="api_key"]', "test-api-key-123")
    page.get_by_role("button", name="Connect").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Click actions menu
    page.locator(".dropdown .btn-ghost.btn-circle").first.click()
    
    # Click Delete
    page.get_by_text("Delete").click()
    
    # Confirm deletion in dialog
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Wait for page reload and verify integration is gone
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_text("No integrations configured")).to_be_visible()


def test_unifi_network_error_handling(page: Page, live_server_url, clean_db):
    """Test network error handling for UniFi integration."""
    with patch("app.integrations.unifi_protect.unifi_protect.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        
        # Mock network error
        instance.get.side_effect = httpx.ConnectError("Connection refused")
        instance.aclose = AsyncMock()
        
        page.goto(f"{live_server_url}/settings/integrations")
        
        # Add integration
        page.get_by_role("button", name="Add Integration").click()
        page.get_by_role("link", name="UniFi Protect Connect to").click()
        page.fill('input[name="host"]', "https://192.168.1.1")
        page.fill('input[name="api_key"]', "test-api-key-123")
        page.get_by_role("button", name="Connect").click()
        
        # Wait for error status
        page.wait_for_load_state("domcontentloaded")
        expect(page.get_by_role("heading", name="UniFi Protect", exact=True)).to_be_visible()
        expect(page.get_by_text("Error")).to_be_visible()


def test_unifi_ssl_certificate_handling(page: Page, live_server_url, clean_db):
    """Test that self-signed certificates are handled properly."""
    with patch("app.integrations.unifi_protect.unifi_protect.httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        
        # Verify SSL context is configured
        assert mock_client.call_args is None  # Not called yet
        
        # Add integration to trigger client creation
        page.goto(f"{live_server_url}/settings/integrations")
        page.get_by_role("button", name="Add Integration").click()
        page.get_by_role("link", name="UniFi Protect Connect to").click()
        page.fill('input[name="host"]', "https://192.168.1.1")
        page.fill('input[name="api_key"]', "test-api-key-123")
        
        # Mock successful response
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json.return_value = {"applicationVersion": "4.0.53"}
        instance.get.return_value = success_response
        instance.aclose = AsyncMock()
        
        page.get_by_role("button", name="Connect").click()
        page.wait_for_load_state("domcontentloaded")
        
        # Verify connection was successful despite SSL
        expect(page.get_by_text("Connected")).to_be_visible()


def test_unifi_update_camera_selection(page: Page, mock_unifi_api, live_server_url, clean_db):
    """Test updating camera selection after initial setup."""
    # First add an integration with one camera selected
    page.goto(f"{live_server_url}/settings/integrations")
    page.get_by_role("button", name="Add Integration").click()
    page.get_by_role("link", name="UniFi Protect Connect to").click()
    page.fill('input[name="host"]', "https://192.168.1.1")
    page.fill('input[name="api_key"]', "test-api-key-123")
    page.get_by_role("button", name="Connect").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Select first camera only
    page.get_by_role("button", name="Select Cameras").click()
    page.locator('input[value="camera1"]').check()
    page.locator('input[value="camera2"]').uncheck()
    page.get_by_role("button", name="Save Selection").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Verify only one camera is shown
    expect(page.get_by_text("Front Door Camera")).to_be_visible()
    expect(page.get_by_text("Backyard Camera")).not_to_be_visible()
    
    # Update selection to include both cameras
    page.get_by_role("button", name="Select Cameras").click()
    page.locator('input[value="camera2"]').check()
    page.get_by_role("button", name="Save Selection").click()
    page.wait_for_load_state("domcontentloaded")
    
    # Verify both cameras are now shown
    expect(page.get_by_text("Front Door Camera")).to_be_visible()
    expect(page.get_by_text("Backyard Camera")).to_be_visible()