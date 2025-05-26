"""
Basic tests for the FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"


def test_dashboard_page():
    """Test the dashboard page returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Foe Be Gone" in response.text


def test_static_files_accessible():
    """Test that static files are accessible"""
    response = client.get("/static/css/main.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_public_files_accessible():
    """Test that public files (logo) are accessible"""
    response = client.get("/public/logo.jpg")
    assert response.status_code == 200