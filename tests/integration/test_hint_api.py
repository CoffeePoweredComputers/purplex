"""
Test suite for hint-related API endpoints.

Converted from Django TestCase to pytest style.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    ProblemHint,
    ProblemSetMembership,
    UserProgress,
)
from tests.factories import (
    CourseFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """Provide a DRF API client."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = UserFactory(is_staff=True, is_superuser=True)
    return user


@pytest.fixture
def student_user(db):
    """Create a student user."""
    return UserFactory()


@pytest.fixture
def problem(db, admin_user):
    """Create a test problem."""
    return EiplProblemFactory(created_by=admin_user)


@pytest.fixture
def problem_set(db, admin_user):
    """Create a test problem set."""
    return ProblemSetFactory(created_by=admin_user)


@pytest.fixture
def course(db, admin_user):
    """Create a test course."""
    return CourseFactory()


@pytest.fixture
def enrolled_student(student_user, course):
    """Enroll student in course."""
    CourseEnrollment.objects.create(user=student_user, course=course)
    return student_user


@pytest.fixture
def problem_in_set(problem, problem_set):
    """Add problem to problem set."""
    ProblemSetMembership.objects.create(
        problem=problem, problem_set=problem_set, order=1
    )
    return problem


class TestHintAvailability:
    """Tests for hint availability endpoint."""

    def test_get_hint_availability_no_hints_configured(
        self, api_client, student_user, problem
    ):
        """Test getting hint availability when no hints are configured."""
        api_client.force_authenticate(user=student_user)

        url = reverse("problem_hint_availability", kwargs={"slug": problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["available_hints"] == []
        assert data["hints_used"] == []
        assert data["current_attempts"] == 0

    def test_get_hint_availability_with_hints_configured(
        self, api_client, student_user, problem
    ):
        """Test getting hint availability with configured hints."""
        # Create hints
        ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=3,
            content={"mappings": [{"from": "x", "to": "count"}]},
        )

        ProblemHint.objects.create(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            min_attempts=2,
            content={"subgoals": []},
        )

        # Create disabled hint (should not appear)
        ProblemHint.objects.create(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=False,
            min_attempts=1,
            content={"suggested_call": "test()"},
        )

        api_client.force_authenticate(user=student_user)

        url = reverse("problem_hint_availability", kwargs={"slug": problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only show enabled hints
        assert len(data["available_hints"]) == 2

        hint_types = [hint["type"] for hint in data["available_hints"]]
        assert "variable_fade" in hint_types
        assert "subgoal_highlight" in hint_types
        assert "suggested_trace" not in hint_types

        # All hints should be locked (0 attempts)
        for hint in data["available_hints"]:
            assert not hint["unlocked"]
            assert not hint["available"]

    def test_get_hint_availability_with_progress(
        self, api_client, student_user, problem_in_set, problem_set
    ):
        """Test hint availability with user progress."""
        # Create hint
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=3,
            content={"mappings": []},
        )

        # Create user progress with attempts
        UserProgress.objects.create(
            user=student_user,
            problem=problem_in_set,
            problem_set=problem_set,
            attempts=5,  # More than min_attempts
        )

        api_client.force_authenticate(user=student_user)

        url = reverse("problem_hint_availability", kwargs={"slug": problem_in_set.slug})
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Hint should be unlocked
        assert len(data["available_hints"]) == 1
        hint = data["available_hints"][0]
        assert hint["unlocked"]
        assert hint["available"]
        assert hint["attempts_needed"] == 0
        assert data["current_attempts"] == 5


class TestHintContent:
    """Tests for hint content retrieval."""

    def test_get_hint_content_success(
        self, api_client, student_user, problem_in_set, problem_set
    ):
        """Test getting hint content successfully."""
        hint = ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=1,
            content={
                "mappings": [{"from": "x", "to": "count"}, {"from": "y", "to": "total"}]
            },
        )

        # Create progress to unlock hint
        UserProgress.objects.create(
            user=student_user,
            problem=problem_in_set,
            problem_set=problem_set,
            attempts=2,
        )

        api_client.force_authenticate(user=student_user)

        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["type"] == "variable_fade"
        assert data["content"] == hint.content
        assert data["min_attempts"] == 1

    def test_get_hint_content_not_unlocked(
        self, api_client, student_user, problem_in_set, problem_set
    ):
        """Test getting hint content when not unlocked."""
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=5,
            content={"mappings": []},
        )

        # Create progress with insufficient attempts
        UserProgress.objects.create(
            user=student_user,
            problem=problem_in_set,
            problem_set=problem_set,
            attempts=2,  # Less than min_attempts
        )

        api_client.force_authenticate(user=student_user)

        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "You need 3 more attempts" in data["error"]

    def test_get_hint_content_hint_not_found(self, api_client, student_user, problem):
        """Test getting hint content for non-existent hint."""
        api_client.force_authenticate(user=student_user)

        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Hint not found" in data["error"]

    def test_get_hint_content_disabled_hint(
        self, api_client, student_user, problem_in_set, problem_set
    ):
        """Test getting content for disabled hint."""
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=False,  # Disabled
            min_attempts=1,
            content={"mappings": []},
        )

        UserProgress.objects.create(
            user=student_user,
            problem=problem_in_set,
            problem_set=problem_set,
            attempts=5,
        )

        api_client.force_authenticate(user=student_user)

        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "This hint is not enabled" in data["error"]


class TestAdminHintEndpoints:
    """Tests for admin hint management endpoints."""

    def test_admin_get_problem_hints(self, api_client, admin_user, problem):
        """Test admin endpoint to get all hint configurations."""
        # Create hints
        ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=3,
            content={"mappings": []},
        )

        ProblemHint.objects.create(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=False,
            min_attempts=2,
            content={"subgoals": []},
        )

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["problem_slug"] == problem.slug
        # Should include default configs for missing types
        assert len(data["hints"]) == 3

        # Check that all hint types are present
        hint_types = [hint["type"] for hint in data["hints"]]
        assert "variable_fade" in hint_types
        assert "subgoal_highlight" in hint_types
        assert "suggested_trace" in hint_types

    def test_admin_update_hints_success(self, api_client, admin_user, problem):
        """Test admin endpoint to update hint configurations."""
        hints_data = {
            "hints": [
                {
                    "type": "variable_fade",
                    "is_enabled": True,
                    "min_attempts": 3,
                    "content": {
                        "mappings": [
                            {"from": "x", "to": "count"},
                            {"from": "y", "to": "total"},
                        ]
                    },
                },
                {
                    "type": "subgoal_highlight",
                    "is_enabled": True,
                    "min_attempts": 2,
                    "content": {
                        "subgoals": [
                            {
                                "line_start": 1,
                                "line_end": 3,
                                "title": "Initialize",
                                "explanation": "Set up variables",
                            }
                        ]
                    },
                },
                {
                    "type": "suggested_trace",
                    "is_enabled": False,
                    "min_attempts": 1,
                    "content": {
                        "suggested_call": "test_function()",
                        "explanation": "Try this call",
                    },
                },
            ]
        }

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.put(url, hints_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["problem_slug"] == problem.slug
        assert len(data["hints"]) == 3

        # Verify hints were created/updated
        assert ProblemHint.objects.filter(problem=problem).count() == 3

        variable_fade_hint = ProblemHint.objects.get(
            problem=problem, hint_type="variable_fade"
        )
        assert variable_fade_hint.is_enabled
        assert len(variable_fade_hint.content["mappings"]) == 2

    def test_admin_update_hints_invalid_content(self, api_client, admin_user, problem):
        """Test admin update with invalid hint content."""
        hints_data = {
            "hints": [
                {
                    "type": "variable_fade",
                    "is_enabled": True,
                    "min_attempts": 3,
                    "content": {"mappings": "invalid_not_a_list"},  # Should be a list
                }
            ]
        }

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.put(url, hints_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data

    def test_admin_update_hints_invalid_type(self, api_client, admin_user, problem):
        """Test admin update with invalid hint type."""
        hints_data = {
            "hints": [
                {
                    "type": "invalid_hint_type",
                    "is_enabled": True,
                    "min_attempts": 3,
                    "content": {},
                }
            ]
        }

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.put(url, hints_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid hint type" in data["error"]

    def test_admin_update_hints_missing_type(self, api_client, admin_user, problem):
        """Test admin update with missing hint type."""
        hints_data = {
            "hints": [
                {
                    # Missing 'type' field
                    "is_enabled": True,
                    "min_attempts": 3,
                    "content": {},
                }
            ]
        }

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.put(url, hints_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Each hint must have a type field" in data["error"]


class TestHintAuthentication:
    """Tests for hint endpoint authentication and authorization."""

    def test_hint_access_without_authentication(self, api_client, problem):
        """Test hint endpoints require authentication."""
        url = reverse("problem_hint_availability", kwargs={"slug": problem.slug})
        response = api_client.get(url)

        # DRF's IsAuthenticated permission returns 403 for unauthenticated requests
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_hints_require_admin_permission(
        self, api_client, student_user, problem
    ):
        """Test admin hint endpoints require admin permission."""
        api_client.force_authenticate(user=student_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestHintCourseContext:
    """Tests for hint access with course context."""

    def test_hint_with_course_context(
        self, api_client, enrolled_student, problem_in_set, problem_set, course
    ):
        """Test hint availability with course context."""
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=2,
            content={"mappings": []},
        )

        # Create progress with course context
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=course,
            attempts=3,
        )

        api_client.force_authenticate(user=enrolled_student)

        url = reverse("problem_hint_availability", kwargs={"slug": problem_in_set.slug})
        response = api_client.get(
            url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["current_attempts"] == 3
        assert data["available_hints"][0]["unlocked"]

    def test_hint_with_invalid_course(self, api_client, student_user, problem):
        """Test hint availability with invalid course ID."""
        api_client.force_authenticate(user=student_user)

        url = reverse("problem_hint_availability", kwargs={"slug": problem.slug})
        response = api_client.get(url, {"course_id": "INVALID123"})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Course not found" in data["error"]

    def test_hint_access_not_enrolled_course(
        self, api_client, student_user, problem, admin_user
    ):
        """Test hint access when not enrolled in course."""
        other_course = Course.objects.create(course_id="OTHER101", name="Other Course")

        api_client.force_authenticate(user=student_user)

        url = reverse("problem_hint_availability", kwargs={"slug": problem.slug})
        response = api_client.get(url, {"course_id": other_course.course_id})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "You are not enrolled in this course" in data["error"]


class TestLargeHintContent:
    """Tests for handling large hint content."""

    def test_large_hint_content(self, api_client, admin_user, problem):
        """Test handling of large hint content."""
        # Create a large subgoal list
        large_subgoals = []
        for i in range(1000):
            large_subgoals.append(
                {
                    "line_start": i * 2 + 1,
                    "line_end": i * 2 + 2,
                    "title": f"Step {i + 1}",
                    "explanation": f"This is a very long explanation for step {i + 1}. "
                    * 10,
                }
            )

        hints_data = {
            "hints": [
                {
                    "type": "subgoal_highlight",
                    "is_enabled": True,
                    "min_attempts": 1,
                    "content": {"subgoals": large_subgoals},
                }
            ]
        }

        api_client.force_authenticate(user=admin_user)

        url = reverse("admin_problem_hints", kwargs={"slug": problem.slug})
        response = api_client.put(url, hints_data, format="json")

        # Should handle large content gracefully
        assert response.status_code == status.HTTP_200_OK
