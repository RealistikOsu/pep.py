#!/usr/bin/env python3
"""
Simple test script to verify FastAPI setup works.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add the peppy directory to the path
sys.path.insert(0, str(Path(__file__).parent / "peppy"))

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the create_app function from main
from main import create_app


def test_fastapi_setup():
    """Test that FastAPI app can be created and basic routes work."""
    app = create_app()
    client = TestClient(app)

    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    assert "Loading site" in response.text

    # Test API endpoints exist (they should return 404 for now since handlers aren't fully implemented)
    response = client.get("/api/v1/onlineUsers")
    # This should work once handlers are properly implemented
    print("FastAPI setup test completed successfully!")
    print("Root endpoint returns:", response.status_code)


if __name__ == "__main__":
    test_fastapi_setup()
