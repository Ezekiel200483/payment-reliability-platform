# Test configuration and utilities

import pytest
import asyncio
from typing import Generator
from fastapi.testclient import TestClient
import sys
import os

# Add services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../services/payment-service'))

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    return TestClient(app)
