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
from django.db import connection
from rest_framework.test import APIClient

# =============================================================================
# Database Triggers (required because --nomigrations skips RunSQL)
# =============================================================================


@pytest.fixture(scope="session")
def _userconsent_immutability_trigger(django_db_setup, django_db_blocker):
    """Install the UserConsent immutability trigger on the test DB.

    --nomigrations creates tables from model definitions via syncdb, which
    skips RunSQL operations in migrations. This fixture installs the trigger
    from the migration's FORWARD_SQL so the test DB matches production.
    """
    from purplex.users_app.sql import FORWARD_SQL

    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute(FORWARD_SQL)


@pytest.fixture(scope="session")
def _activityevent_immutability_trigger(django_db_setup, django_db_blocker):
    """Install the ActivityEvent immutability trigger on the test DB.

    --nomigrations creates tables from model definitions via syncdb, which
    skips RunSQL operations in migrations. This fixture installs the trigger
    from the migration's FORWARD_SQL so the test DB matches production.
    """
    from purplex.submissions.sql import FORWARD_SQL

    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute(FORWARD_SQL)


from tests.factories import (  # noqa: E402
    AgeVerificationFactory,
    CourseEnrollmentFactory,
    CourseFactory,
    CourseInstructorFactory,
    CourseProblemSetFactory,
    DataPrincipalNomineeFactory,
    DebugFixProblemFactory,
    EiplProblemFactory,
    McqProblemFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    PromptProblemFactory,
    RefuteProblemFactory,
    SubmissionFactory,
    TestCaseFactory,
    UserConsentFactory,
    UserFactory,
    UserProfileFactory,
    UserProgressFactory,
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
    c = CourseFactory()
    CourseInstructorFactory(course=c, user=instructor, role="primary")
    return c


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

    course = CourseFactory()
    CourseInstructorFactory(course=course, user=instructor, role="primary")
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


# =============================================================================
# Privacy & Consent Fixtures
# =============================================================================


@pytest.fixture
def user_consent(db, user):
    """Create a single privacy_policy consent for the default user."""
    return UserConsentFactory(user=user)


@pytest.fixture
def age_verification(db, user):
    """Create an adult age verification for the default user."""
    return AgeVerificationFactory(user=user)


@pytest.fixture
def minor_user(db):
    """Create a minor user (under 18) with profile and age verification."""
    u = UserFactory(username="minor_user")
    UserProfileFactory(user=u)
    AgeVerificationFactory(user=u, is_minor=True, is_child=False)
    return u


@pytest.fixture
def child_user(db):
    """Create a child user (under 13) with profile and age verification."""
    u = UserFactory(username="child_user")
    UserProfileFactory(user=u)
    AgeVerificationFactory(
        user=u, is_minor=True, is_child=True, parental_consent_given=False
    )
    return u


@pytest.fixture
def nominee(db, user):
    """Create a DataPrincipalNominee for the default user."""
    return DataPrincipalNomineeFactory(user=user)


@pytest.fixture
def user_with_all_consents(db):
    """Create a user with all 6 consent types granted."""
    from purplex.users_app.models import ConsentType

    u = UserFactory(username="consented_user")
    UserProfileFactory(user=u)
    for ct, _label in ConsentType.choices:
        UserConsentFactory(user=u, consent_type=ct)
    return u


@pytest.fixture
def user_with_deletion_requested(db):
    """Create a user with a pending deletion (inactive, scheduled in the past)."""
    from datetime import timedelta

    from django.utils import timezone

    u = UserFactory(username="deleting_user", is_active=False)
    profile = UserProfileFactory(user=u)
    profile.deletion_requested_at = timezone.now() - timedelta(days=31)
    profile.deletion_scheduled_at = timezone.now() - timedelta(days=1)
    profile.save()
    return u


# =============================================================================
# Multi-Instructor Fixtures
# =============================================================================


@pytest.fixture
def ta_user(db):
    """Create a TA user with instructor profile."""
    user = UserFactory(username="ta_user")
    UserProfileFactory(user=user, role="instructor")
    return user


@pytest.fixture
def ta_client(api_client, ta_user):
    """API client authenticated as a TA."""
    api_client.force_authenticate(user=ta_user)
    return api_client


@pytest.fixture
def course_with_team(db, instructor, ta_user):
    """Create a course with a primary instructor and a TA."""
    c = CourseFactory()
    CourseInstructorFactory(course=c, user=instructor, role="primary")
    CourseInstructorFactory(course=c, user=ta_user, role="ta", added_by=instructor)
    return c


# =============================================================================
# Composite Scenario Fixtures
# =============================================================================


@pytest.fixture
def enrolled_course_with_submission(db, instructor, user):
    """Course with enrolled student, problem in problem set, and one submission.

    Returns dict with: course, problem_set, problem, submission, course_problem_set.
    Useful for testing instructor submission views and student progress endpoints.
    """
    course = CourseFactory()
    CourseInstructorFactory(course=course, user=instructor, role="primary")
    CourseEnrollmentFactory(user=user, course=course)
    ps = ProblemSetFactory(created_by=instructor)
    problem = EiplProblemFactory(created_by=instructor)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    cps = CourseProblemSetFactory(course=course, problem_set=ps, order=0)
    submission = SubmissionFactory(
        user=user, problem=problem, problem_set=ps, course=course
    )
    UserProgressFactory(
        user=user,
        problem=problem,
        problem_set=ps,
        course=course,
        attempts=1,
        best_score=submission.score,
    )
    return {
        "course": course,
        "problem_set": ps,
        "problem": problem,
        "submission": submission,
        "course_problem_set": cps,
    }
