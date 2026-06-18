"""
Integration tests for counterexample hint delivery on Refute problems.

Tests the full flow: admin creates hint → student attempts → hint unlocks → content delivered.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from purplex.problems_app.models import (
    CourseEnrollment,
    ProblemHint,
    ProblemSetMembership,
    UserProgress,
)
from tests.factories import (
    CourseFactory,
    ProblemSetFactory,
    RefuteProblemFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def student_user(db):
    return UserFactory()


@pytest.fixture
def refute_problem(db, admin_user):
    return RefuteProblemFactory(created_by=admin_user)


@pytest.fixture
def refute_problem_no_counterexample(db, admin_user):
    return RefuteProblemFactory(
        created_by=admin_user,
        expected_counterexample={},
    )


@pytest.fixture
def problem_set(db, admin_user):
    return ProblemSetFactory(created_by=admin_user)


@pytest.fixture
def course(db):
    return CourseFactory()


@pytest.fixture
def enrolled_student(student_user, course):
    CourseEnrollment.objects.create(user=student_user, course=course)
    return student_user


@pytest.fixture
def refute_in_set(refute_problem, problem_set):
    ProblemSetMembership.objects.create(
        problem=refute_problem, problem_set=problem_set, order=1
    )
    return refute_problem


@pytest.fixture
def counterexample_hint(refute_problem):
    """Create an enabled counterexample hint for the refute problem."""
    return ProblemHint.objects.create(
        problem=refute_problem,
        hint_type="counterexample",
        is_enabled=True,
        min_attempts=3,
        content={"input": {"x": -5}, "explanation": "Try a negative number"},
    )


# =============================================================================
# Hint Availability
# =============================================================================


class TestRefuteHintAvailability:
    """Test hint availability endpoint with counterexample hints."""

    def test_counterexample_hint_appears_in_availability(
        self, api_client, student_user, refute_problem, counterexample_hint
    ):
        api_client.force_authenticate(user=student_user)
        url = reverse("problem_hint_availability", kwargs={"slug": refute_problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        hint_types = [h["type"] for h in data["available_hints"]]
        assert "counterexample" in hint_types

    def test_counterexample_hint_locked_with_zero_attempts(
        self, api_client, student_user, refute_problem, counterexample_hint
    ):
        api_client.force_authenticate(user=student_user)
        url = reverse("problem_hint_availability", kwargs={"slug": refute_problem.slug})
        response = api_client.get(url)

        data = response.json()
        hint = next(h for h in data["available_hints"] if h["type"] == "counterexample")
        assert hint["available"] is False
        assert hint["attempts_needed"] == 3

    def test_counterexample_hint_unlocked_after_enough_attempts(
        self,
        api_client,
        enrolled_student,
        refute_in_set,
        problem_set,
        course,
        counterexample_hint,
    ):
        # Create progress with enough attempts
        UserProgress.objects.create(
            user=enrolled_student,
            problem=refute_in_set,
            problem_set=problem_set,
            course=course,
            attempts=5,
        )

        api_client.force_authenticate(user=enrolled_student)
        url = reverse("problem_hint_availability", kwargs={"slug": refute_in_set.slug})
        response = api_client.get(
            url,
            {"course_id": str(course.course_id), "problem_set_slug": problem_set.slug},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        hint = next(h for h in data["available_hints"] if h["type"] == "counterexample")
        assert hint["available"] is True
        assert hint["attempts_needed"] == 0

    def test_disabled_counterexample_hint_not_in_availability(
        self, api_client, student_user, refute_problem
    ):
        ProblemHint.objects.create(
            problem=refute_problem,
            hint_type="counterexample",
            is_enabled=False,
            min_attempts=3,
            content={"input": {"x": -5}},
        )

        api_client.force_authenticate(user=student_user)
        url = reverse("problem_hint_availability", kwargs={"slug": refute_problem.slug})
        response = api_client.get(url)

        data = response.json()
        hint_types = [h["type"] for h in data["available_hints"]]
        assert "counterexample" not in hint_types


# =============================================================================
# Hint Content
# =============================================================================


class TestRefuteHintContent:
    """Test hint content endpoint delivers counterexample data."""

    def test_get_counterexample_content_when_unlocked(
        self,
        api_client,
        enrolled_student,
        refute_in_set,
        problem_set,
        course,
        counterexample_hint,
    ):
        UserProgress.objects.create(
            user=enrolled_student,
            problem=refute_in_set,
            problem_set=problem_set,
            course=course,
            attempts=5,
        )

        api_client.force_authenticate(user=enrolled_student)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": refute_in_set.slug, "hint_type": "counterexample"},
        )
        response = api_client.get(
            url,
            {"course_id": str(course.course_id), "problem_set_slug": problem_set.slug},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["type"] == "counterexample"
        assert data["content"]["input"] == {"x": -5}
        assert data["content"]["explanation"] == "Try a negative number"

    def test_get_counterexample_content_forbidden_when_locked(
        self, api_client, student_user, refute_problem, counterexample_hint
    ):
        api_client.force_authenticate(user=student_user)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": refute_problem.slug, "hint_type": "counterexample"},
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_counterexample_content_forbidden_when_disabled(
        self, api_client, student_user, refute_problem
    ):
        ProblemHint.objects.create(
            problem=refute_problem,
            hint_type="counterexample",
            is_enabled=False,
            content={"input": {"x": -5}},
        )

        api_client.force_authenticate(user=student_user)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": refute_problem.slug, "hint_type": "counterexample"},
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Admin hint config
# =============================================================================


class TestRefuteAdminHintConfig:
    """Test admin hint endpoints include counterexample type."""

    def test_admin_get_config_includes_counterexample_default(
        self, api_client, admin_user, refute_problem
    ):
        api_client.force_authenticate(user=admin_user)
        url = reverse("admin_problem_hints", kwargs={"slug": refute_problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        hint_types = [h["type"] for h in data["hints"]]
        assert "counterexample" in hint_types

        # Default content should be populated from expected_counterexample
        ce_hint = next(h for h in data["hints"] if h["type"] == "counterexample")
        assert ce_hint["content"]["input"] == {"x": -5}
        assert ce_hint["is_enabled"] is False  # disabled by default

    def test_admin_create_counterexample_hint(
        self, api_client, admin_user, refute_problem
    ):
        api_client.force_authenticate(user=admin_user)
        url = reverse("admin_problem_hints", kwargs={"slug": refute_problem.slug})
        response = api_client.put(
            url,
            {
                "hints": [
                    {
                        "type": "counterexample",
                        "is_enabled": True,
                        "min_attempts": 2,
                        "content": {
                            "input": {"x": -5},
                            "explanation": "Try negative",
                        },
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        ce_hint = next(h for h in data["hints"] if h["type"] == "counterexample")
        assert ce_hint["is_enabled"] is True
        assert ce_hint["min_attempts"] == 2
        assert ce_hint["content"]["input"] == {"x": -5}

        # Verify persisted
        hint = ProblemHint.objects.get(
            problem=refute_problem, hint_type="counterexample"
        )
        assert hint.is_enabled is True
        assert hint.min_attempts == 2

    def test_admin_create_counterexample_hint_invalid_content(
        self, api_client, admin_user, refute_problem
    ):
        api_client.force_authenticate(user=admin_user)
        url = reverse("admin_problem_hints", kwargs={"slug": refute_problem.slug})
        response = api_client.put(
            url,
            {
                "hints": [
                    {
                        "type": "counterexample",
                        "is_enabled": True,
                        "content": {"explanation": "missing input field"},
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
