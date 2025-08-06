"""
Basic test to verify pytest setup is working correctly.
"""
import pytest
from django.conf import settings


def test_pytest_is_working():
    """Verify pytest is properly configured."""
    assert True


def test_django_settings_loaded():
    """Verify Django settings are loaded in test environment."""
    assert settings.SECRET_KEY is not None
    assert hasattr(settings, 'DATABASES')


@pytest.mark.django_db
def test_database_access(test_user):
    """Verify database access and fixtures work."""
    assert test_user.username == 'testuser'
    assert test_user.email == 'test@example.com'