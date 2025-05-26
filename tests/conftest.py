"""Pytest configuration and fixtures."""

import pytest
from playwright.sync_api import Page
import subprocess
import time
import socket
from pathlib import Path
import shutil
import os


def find_free_port():
    """Find a free port to run the test server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="session")
def live_server_url():
    """Start the FastAPI server for testing."""
    port = find_free_port()
    
    # Create a test database
    test_db = "test_foe_be_gone.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Set test database environment variable
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db}"
    
    # Run migrations
    subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
    
    # Start the server
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    
    # Give the server time to start
    time.sleep(2)
    
    yield f"http://localhost:{port}"
    
    # Cleanup
    process.terminate()
    process.wait()
    
    # Remove test database
    if os.path.exists(test_db):
        os.remove(test_db)


@pytest.fixture
def clean_db():
    """Reset database between tests."""
    # Clear all tables by recreating the database
    test_db = "test_foe_be_gone.db"
    
    # Set environment for migrations
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db}"
    
    # Instead of downgrade/upgrade, let's use a more direct approach
    from sqlmodel import Session, text
    from app.core.database import engine
    
    with Session(engine) as session:
        # Delete all data from tables in reverse dependency order
        try:
            session.exec(text("DELETE FROM deterrent_actions"))
        except:
            pass  # Table might not exist
        try:
            session.exec(text("DELETE FROM foes"))
        except:
            pass  # Table might not exist
        try:
            session.exec(text("DELETE FROM detections"))
        except:
            pass  # Table might not exist
        session.exec(text("DELETE FROM devices"))
        session.exec(text("DELETE FROM integration_instances"))
        session.commit()
    
    yield
    
    # Cleanup is automatic when next test runs


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context to ignore HTTPS errors."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }