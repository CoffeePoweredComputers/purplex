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
    CourseProblemSetFactory,
    DebugFixProblemFactory,
    EiplProblemFactory,
    McqProblemFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetFactory,
    PromptProblemFactory,
    RefuteProblemFactory,
    TestCaseFactory,
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
    UserProfileFactory(user=user, role="instructor")
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin/superuser with profile.

    Sets both Django admin flags AND profile role for full admin access.
    """
    user = UserFactory(is_staff=True, is_superuser=True)
    UserProfileFactory(user=user, role="admin")
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


# =============================================================================
# Additional Problem Type Fixtures
# =============================================================================


@pytest.fixture
def debug_fix_problem(db):
    """Create a standard Debug Fix problem."""
    return DebugFixProblemFactory()


@pytest.fixture
def probeable_code_problem(db):
    """Create a standard Probeable Code problem."""
    return ProbeableCodeProblemFactory()


@pytest.fixture
def probeable_spec_problem(db):
    """Create a standard Probeable Spec problem."""
    return ProbeableSpecProblemFactory()


@pytest.fixture
def refute_problem(db):
    """Create a standard Refute problem."""
    return RefuteProblemFactory()


# =============================================================================
# CourseProblemSet Fixtures
# =============================================================================


@pytest.fixture
def course_problem_set(db, course, problem_set):
    """Create a CourseProblemSet linking a course and problem set."""
    return CourseProblemSetFactory(course=course, problem_set=problem_set)


@pytest.fixture
def course_with_due_dates(db, instructor):
    """Create a course with problem sets having various deadline types."""
    from datetime import timedelta

    from django.utils import timezone

    course = CourseFactory(instructor=instructor)
    ps1 = ProblemSetFactory(title="No Deadline Set")
    ps2 = ProblemSetFactory(title="Soft Deadline Set")
    ps3 = ProblemSetFactory(title="Hard Deadline Set")

    CourseProblemSetFactory(
        course=course,
        problem_set=ps1,
        order=0,
        deadline_type="none",
    )
    CourseProblemSetFactory(
        course=course,
        problem_set=ps2,
        order=1,
        deadline_type="soft",
        due_date=timezone.now() + timedelta(days=7),
    )
    CourseProblemSetFactory(
        course=course,
        problem_set=ps3,
        order=2,
        deadline_type="hard",
        due_date=timezone.now() + timedelta(days=14),
    )
    return course


# =============================================================================
# TestCase Fixtures
# =============================================================================


@pytest.fixture
def test_case(db, eipl_problem):
    """Create a test case for an EiPL problem."""
    return TestCaseFactory(problem=eipl_problem)


# =============================================================================
# Admin/Instructor Client Fixtures
# =============================================================================


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def instructor_client(api_client, instructor):
    """API client authenticated as instructor."""
    api_client.force_authenticate(user=instructor)
    return api_client
