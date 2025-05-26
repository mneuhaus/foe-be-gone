"""Pytest configuration and fixtures."""

import pytest
from playwright.sync_api import Page
import subprocess
import time
import socket
from pathlib import Path


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
    
    # Start the server
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give the server time to start
    time.sleep(2)
    
    yield f"http://localhost:{port}"
    
    # Cleanup
    process.terminate()
    process.wait()


@pytest.fixture
def browser_context_args(browser_context_args):
    """Configure browser context to ignore HTTPS errors."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }