"""
Pytest configuration for Purplex test suite.

Shared fixtures are defined here using factory_boy for consistent test data.
These fixtures are available to all tests in both unit/ and integration/ directories.

Usage:
    def test_something(user, eipl_problem):
        # user and eipl_problem are automatically injected
        assert user.username.startswith('user_')
"""

import pytest
from rest_framework.test import APIClient

from tests.factories import (
    CourseFactory,
    EiplProblemFactory,
    McqProblemFactory,
    ProblemSetFactory,
    PromptProblemFactory,
    UserFactory,
    UserProfileFactory,
)

# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Provide a DRF API client for API testing."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """API client authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def user(db):
    """Create a standard test user with profile."""
    user = UserFactory()
    UserProfileFactory(user=user)
    return user


@pytest.fixture
def instructor(db):
    """Create an instructor user with profile."""
    user = UserFactory(username="instructor")
    UserProfileFactory(user=user)
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin/superuser with profile."""
    user = UserFactory(is_staff=True, is_superuser=True)
    UserProfileFactory(user=user)
    return user


# =============================================================================
# Problem Fixtures
# =============================================================================


@pytest.fixture
def eipl_problem(db):
    """Create a standard EiPL problem."""
    return EiplProblemFactory()


@pytest.fixture
def mcq_problem(db):
    """Create a standard MCQ problem."""
    return McqProblemFactory()


@pytest.fixture
def prompt_problem(db):
    """Create a standard Prompt problem."""
    return PromptProblemFactory()


# =============================================================================
# Container Fixtures
# =============================================================================


@pytest.fixture
def problem_set(db):
    """Create an empty problem set."""
    return ProblemSetFactory()


@pytest.fixture
def course(db, instructor):
    """Create a course with an instructor."""
    return CourseFactory(instructor=instructor)
