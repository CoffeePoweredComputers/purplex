"""
Pytest configuration for Purplex test suite.

This is a minimal conftest.py for rebuilding tests from scratch.
Add fixtures as needed when writing new tests.
"""
import pytest
from django.test import Client


@pytest.fixture
def api_client():
    """Provide a Django test client for API testing."""
    return Client()
