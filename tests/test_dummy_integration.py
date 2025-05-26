"""Tests for dummy surveillance integration functionality."""

import pytest
from playwright.sync_api import Page, expect
from sqlmodel import Session, select

from app.core.database import engine
from app.models.integration_instance import IntegrationInstance


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure clean database state for each test."""
    # Clean up any existing integrations before test
    with Session(engine) as session:
        integrations = session.exec(select(IntegrationInstance)).all()
        for integration in integrations:
            session.delete(integration)
        session.commit()
    
    yield
    
    # Clean up after test
    with Session(engine) as session:
        integrations = session.exec(select(IntegrationInstance)).all()
        for integration in integrations:
            session.delete(integration)
        session.commit()


def test_add_dummy_integration_and_set_test_scenario(page: Page, live_server_url: str):
    """Test adding a dummy surveillance integration and setting test scenarios."""
    
    # Navigate to integrations page
    page.goto(f"{live_server_url}/settings/integrations")
    
    # Verify page loaded
    expect(page.locator("h1")).to_contain_text("Integrations")
    
    # Check initial state - should show no integrations
    expect(page.locator("text=No integrations configured")).to_be_visible()
    
    # Click Add Integration button
    page.click("[role='button']:has-text('Add Integration')")
    
    # Wait for dropdown to appear
    expect(page.locator("text=Dummy Surveillance")).to_be_visible()
    
    # Click on Dummy Surveillance option
    page.click("text=Dummy Surveillance")
    
    # Wait for page reload after integration is added
    page.wait_for_load_state("networkidle")
    
    # Verify integration was added
    expect(page.locator("p:has-text('Type: dummy-surveillance')")).to_be_visible()
    expect(page.locator("span:has-text('Connected')")).to_be_visible()
    expect(page.locator("p:has-text('Successfully connected')")).to_be_visible()
    
    # Find the Test Scenario button
    test_scenario_button = page.locator("[role='button']:has-text('Test Scenario')")
    expect(test_scenario_button).to_be_visible()
    
    # Click Test Scenario button to load scenarios
    test_scenario_button.click()
    
    # Wait for scenarios to load
    page.wait_for_timeout(500)  # Give time for API call
    
    # Verify scenarios are loaded
    expect(page.locator("text=Cat")).to_be_visible()
    expect(page.locator("text=Magpie")).to_be_visible()
    expect(page.locator("text=Nothing")).to_be_visible()
    expect(page.locator("text=Hedgehog")).to_be_visible()
    
    # Click on Cat scenario
    page.click("text=Cat")
    
    # Wait for API call to complete
    page.wait_for_timeout(1000)
    
    # Test another scenario
    test_scenario_button.click()
    page.wait_for_timeout(500)  # Wait for dropdown to show
    page.click("text=Magpie")
    
    # Wait for API call to complete
    page.wait_for_timeout(1000)
    
    # Test the integration connection
    # Click the three dots menu (actions button)
    actions_button = page.locator(".btn-circle").last
    actions_button.click()
    # Wait for dropdown menu to appear
    page.wait_for_timeout(300)
    # Click on the Test menu item using exact text match
    page.get_by_text("Test", exact=True).click()
    
    # Should see success notification
    expect(page.locator(".alert-success")).to_be_visible(timeout=5000)
    expect(page.locator(".alert-success")).to_contain_text("Connected successfully")
    
    # Delete the integration
    # Set up dialog handler before clicking delete
    page.on("dialog", lambda dialog: dialog.accept())
    
    actions_button.click()  # Click the actions menu again
    page.click("text=Delete")
    
    # Wait for page reload
    page.wait_for_load_state("networkidle")
    
    # Verify integration was deleted
    expect(page.locator("text=No integrations configured")).to_be_visible()


def test_multiple_integrations_with_different_scenarios(page: Page, live_server_url: str):
    """Test adding multiple dummy integrations and setting different scenarios."""
    
    # Navigate to integrations page
    page.goto(f"{live_server_url}/settings/integrations")
    
    # Add first integration
    page.click("[role='button']:has-text('Add Integration')")
    page.click("text=Dummy Surveillance")
    page.wait_for_load_state("networkidle")
    
    # Add second integration
    page.click("[role='button']:has-text('Add Integration')")
    page.click("text=Dummy Surveillance")
    page.wait_for_load_state("networkidle")
    
    # Should have 2 integrations now
    integration_cards = page.locator(".card")
    expect(integration_cards).to_have_count(2)
    
    # Set different scenarios for each
    test_buttons = page.locator("[role='button']:has-text('Test Scenario')")
    
    # First integration - set to cat
    test_buttons.nth(0).click()
    page.wait_for_timeout(500)
    page.click("text=Cat")
    page.wait_for_timeout(500)  # Wait for dropdown to close
    
    # Second integration - set to squirrel  
    test_buttons.nth(1).click()
    page.wait_for_timeout(500)
    page.click("text=Squirrel", force=True)
    
    # Verify both were set (check console logs or API calls)
    # Note: In a real test, you might want to check the actual API response
    # or database state to verify the scenarios were set correctly


def test_error_handling_for_invalid_scenario(page: Page, live_server_url: str):
    """Test error handling when API fails."""
    
    # Navigate to integrations page
    page.goto(f"{live_server_url}/settings/integrations")
    
    # Add integration
    page.click("[role='button']:has-text('Add Integration')")
    page.click("text=Dummy Surveillance")
    page.wait_for_load_state("networkidle")
    
    # Intercept API call to simulate error
    def handle_route(route):
        route.fulfill(status=400, json={"detail": "Invalid scenario"})
    
    page.route("**/api/integrations/**/test-scenario/**", handle_route)
    
    # Try to set scenario
    page.click("[role='button']:has-text('Test Scenario')")
    page.wait_for_timeout(300)
    page.click("text=Cat")
    
    # Should see error notification
    expect(page.locator(".alert-error")).to_be_visible(timeout=5000)
    expect(page.locator(".alert-error")).to_contain_text("Failed to set scenario")