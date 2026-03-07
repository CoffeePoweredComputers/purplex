"""
End-to-end integration tests for the complete hint workflow.

Converted from Django TransactionTestCase to pytest style.
These tests cover the full lifecycle from admin creating hints to students using them.
"""

import threading

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

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


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
def course(db, admin_user):
    """Create a test course."""
    return CourseFactory(
        course_id="CS101",
        name="Introduction to Programming",
    )


@pytest.fixture
def problem_set(db, admin_user):
    """Create a test problem set."""
    return ProblemSetFactory(
        slug="basics",
        title="Programming Basics",
        created_by=admin_user,
    )


@pytest.fixture
def problem(db, admin_user):
    """Create a test problem."""
    return EiplProblemFactory(
        slug="sum-function",
        title="Sum Function",
        function_name="add_numbers",
        function_signature="def add_numbers(a, b):",
        reference_solution="def add_numbers(a, b):\n    return a + b",
        created_by=admin_user,
    )


@pytest.fixture
def problem_in_set(problem, problem_set):
    """Link problem to problem set."""
    ProblemSetMembership.objects.create(
        problem_set=problem_set, problem=problem, order=1
    )
    return problem


@pytest.fixture
def enrolled_student(student_user, course):
    """Enroll student in course."""
    CourseEnrollment.objects.create(user=student_user, course=course, is_active=True)
    return student_user


class TestCompleteHintLifecycle:
    """Test complete workflow from admin creating hints to student using them."""

    def test_complete_hint_lifecycle_admin_to_student(
        self,
        api_client,
        admin_user,
        enrolled_student,
        problem_in_set,
        problem_set,
        course,
    ):
        """Test complete workflow from admin creating hints to student using them."""
        # Step 1: Admin creates hint configurations
        api_client.force_authenticate(user=admin_user)

        hint_config = {
            "hints": [
                {
                    "type": "variable_fade",
                    "is_enabled": True,
                    "min_attempts": 2,
                    "content": {
                        "mappings": [
                            {"from": "a", "to": "first_number"},
                            {"from": "b", "to": "second_number"},
                        ]
                    },
                },
                {
                    "type": "subgoal_highlight",
                    "is_enabled": True,
                    "min_attempts": 3,
                    "content": {
                        "subgoals": [
                            {
                                "line_start": 1,
                                "line_end": 1,
                                "title": "Function definition",
                                "explanation": "Define function with two parameters",
                            },
                            {
                                "line_start": 2,
                                "line_end": 2,
                                "title": "Return sum",
                                "explanation": "Calculate and return the sum",
                            },
                        ]
                    },
                },
                {
                    "type": "suggested_trace",
                    "is_enabled": False,  # Disabled
                    "min_attempts": 1,
                    "content": {
                        "suggested_call": "add_numbers(3, 5)",
                        "explanation": "Try this function call",
                    },
                },
            ]
        }

        admin_url = reverse("admin_problem_hints", kwargs={"slug": problem_in_set.slug})
        response = api_client.put(admin_url, hint_config, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Verify hints were created
        hints = ProblemHint.objects.filter(problem=problem_in_set)
        assert hints.count() == 3
        assert hints.filter(is_enabled=True).count() == 2

        # Step 2: Student attempts to access hints before meeting requirements
        api_client.force_authenticate(user=enrolled_student)

        hint_availability_url = reverse(
            "problem_hint_availability", kwargs={"slug": problem_in_set.slug}
        )
        response = api_client.get(
            hint_availability_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should show 2 enabled hints, both locked
        assert len(data["available_hints"]) == 2
        assert data["current_attempts"] == 0

        for hint in data["available_hints"]:
            assert not hint["unlocked"]
            assert not hint["available"]

        # Step 3: Student makes submissions to unlock hints
        progress = UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=course,
            attempts=1,
        )

        # Still not enough attempts for any hints
        response = api_client.get(
            hint_availability_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        data = response.json()
        assert data["current_attempts"] == 1
        for hint in data["available_hints"]:
            assert not hint["unlocked"]

        # Make more attempts to unlock first hint (variable_fade requires 2)
        progress.attempts = 2
        progress.save()

        response = api_client.get(
            hint_availability_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        data = response.json()
        assert data["current_attempts"] == 2

        # Variable fade should be unlocked, subgoal highlight still locked
        variable_fade_hint = next(
            h for h in data["available_hints"] if h["type"] == "variable_fade"
        )
        subgoal_hint = next(
            h for h in data["available_hints"] if h["type"] == "subgoal_highlight"
        )

        assert variable_fade_hint["unlocked"]
        assert variable_fade_hint["available"]
        assert not subgoal_hint["unlocked"]
        assert not subgoal_hint["available"]

        # Step 4: Student accesses unlocked hint content
        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )

        response = api_client.get(
            hint_content_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        hint_data = response.json()

        assert hint_data["type"] == "variable_fade"
        assert hint_data["min_attempts"] == 2
        assert "mappings" in hint_data["content"]
        assert len(hint_data["content"]["mappings"]) == 2

        # Step 5: Student tries to access locked hint
        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "subgoal_highlight"},
        )

        response = api_client.get(
            hint_content_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "You need 1 more attempts" in response.json()["error"]

        # Step 6: Student makes more attempts and unlocks second hint
        progress.attempts = 4
        progress.save()

        response = api_client.get(
            hint_content_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        hint_data = response.json()

        assert hint_data["type"] == "subgoal_highlight"
        assert "subgoals" in hint_data["content"]
        assert len(hint_data["content"]["subgoals"]) == 2

        # Step 7: Verify disabled hint is not accessible
        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "suggested_trace"},
        )

        response = api_client.get(
            hint_content_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "This hint is not enabled" in response.json()["error"]


class TestHintConfigurationUpdates:
    """Tests for hint configuration updates with existing progress."""

    def test_hint_configuration_updates_with_existing_progress(
        self,
        api_client,
        admin_user,
        enrolled_student,
        problem_in_set,
        problem_set,
        course,
    ):
        """Test updating hint configuration when users already have progress."""
        # Create initial hint configuration
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=5,
            content={"mappings": []},
        )

        # Create user progress
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=course,
            attempts=3,
        )

        # Student cannot access hint yet
        api_client.force_authenticate(user=enrolled_student)

        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )

        response = api_client.get(
            hint_content_url, {"problem_set_slug": problem_set.slug}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin updates hint to require fewer attempts
        api_client.force_authenticate(user=admin_user)

        updated_config = {
            "hints": [
                {
                    "type": "variable_fade",
                    "is_enabled": True,
                    "min_attempts": 2,  # Reduced from 5 to 2
                    "content": {"mappings": [{"from": "x", "to": "value"}]},
                }
            ]
        }

        admin_url = reverse("admin_problem_hints", kwargs={"slug": problem_in_set.slug})
        response = api_client.put(admin_url, updated_config, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Now student should be able to access hint
        api_client.force_authenticate(user=enrolled_student)

        response = api_client.get(
            hint_content_url, {"problem_set_slug": problem_set.slug}
        )

        assert response.status_code == status.HTTP_200_OK
        hint_data = response.json()
        assert hint_data["min_attempts"] == 2


class TestCrossCourseIsolation:
    """Tests for hint progress isolation between courses."""

    def test_cross_course_hint_isolation(
        self,
        api_client,
        admin_user,
        enrolled_student,
        problem_in_set,
        problem_set,
        course,
    ):
        """Test that hint progress is isolated between different courses."""
        # Create another course and enroll the student
        other_course = Course.objects.create(
            course_id="CS102", name="Advanced Programming"
        )

        CourseEnrollment.objects.create(
            user=enrolled_student, course=other_course, is_active=True
        )

        # Create hint
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=2,
            content={"mappings": []},
        )

        # Create progress in first course
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=course,
            attempts=5,  # More than min_attempts
        )

        # Create progress in second course
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=other_course,
            attempts=1,  # Less than min_attempts
        )

        api_client.force_authenticate(user=enrolled_student)

        # Check hint availability in first course (should be available)
        hint_availability_url = reverse(
            "problem_hint_availability", kwargs={"slug": problem_in_set.slug}
        )

        response = api_client.get(
            hint_availability_url,
            {
                "course_id": course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        data = response.json()
        assert data["current_attempts"] == 5
        assert data["available_hints"][0]["unlocked"]

        # Check hint availability in second course (should not be available)
        response = api_client.get(
            hint_availability_url,
            {
                "course_id": other_course.course_id,
                "problem_set_slug": problem_set.slug,
            },
        )

        data = response.json()
        assert data["current_attempts"] == 1
        assert not data["available_hints"][0]["unlocked"]


class TestHintErrorHandling:
    """Tests for error handling throughout the hint system."""

    def test_hint_system_error_handling(
        self, api_client, enrolled_student, problem_in_set, admin_user
    ):
        """Test error handling throughout the hint system."""
        api_client.force_authenticate(user=enrolled_student)

        # Test accessing hints for non-existent problem
        hint_availability_url = reverse(
            "problem_hint_availability", kwargs={"slug": "non-existent"}
        )
        response = api_client.get(hint_availability_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test accessing hints with invalid course
        hint_availability_url = reverse(
            "problem_hint_availability", kwargs={"slug": problem_in_set.slug}
        )
        response = api_client.get(hint_availability_url, {"course_id": "INVALID123"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test accessing hints when not enrolled in course
        other_course = Course.objects.create(course_id="CS999", name="Not Enrolled")

        response = api_client.get(
            hint_availability_url, {"course_id": other_course.course_id}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test accessing hint content for invalid hint type
        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "invalid_type"},
        )

        response = api_client.get(hint_content_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid hint type" in response.json()["error"]


class TestConcurrentHintAccess:
    """Tests for concurrent hint access scenarios."""

    def test_concurrent_hint_access(
        self,
        api_client,
        enrolled_student,
        problem_in_set,
        problem_set,
        course,
    ):
        """Test hint access under concurrent conditions."""
        # Create hint
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=1,
            content={"mappings": []},
        )

        # Create progress
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=course,
            attempts=2,
        )

        results = []

        def access_hint():
            client = APIClient()
            client.force_authenticate(user=enrolled_student)

            hint_content_url = reverse(
                "problem_hint_detail",
                kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
            )

            try:
                response = client.get(
                    hint_content_url, {"problem_set_slug": problem_set.slug}
                )
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))

        # Create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_hint)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        for result in results:
            assert result == 200


class TestHintDataConsistency:
    """Tests for data consistency after updates."""

    def test_hint_data_consistency_after_multiple_updates(
        self, api_client, admin_user, problem_in_set
    ):
        """Test data consistency after multiple rapid hint updates."""
        api_client.force_authenticate(user=admin_user)
        admin_url = reverse("admin_problem_hints", kwargs={"slug": problem_in_set.slug})

        # Perform multiple rapid updates
        for i in range(10):
            hint_config = {
                "hints": [
                    {
                        "type": "variable_fade",
                        "is_enabled": True,
                        "min_attempts": i + 1,  # Different value each time
                        "content": {
                            "mappings": [{"from": f"var{i}", "to": f"variable_{i}"}]
                        },
                    }
                ]
            }

            response = api_client.put(admin_url, hint_config, format="json")
            assert response.status_code == status.HTTP_200_OK

        # Verify final state
        hint = ProblemHint.objects.get(
            problem=problem_in_set, hint_type="variable_fade"
        )
        assert hint.min_attempts == 10  # Should have the last value
        assert hint.content["mappings"][0]["from"] == "var9"


class TestHintWithoutCourseContext:
    """Tests for hint system without course context."""

    def test_hint_system_with_problem_set_without_course(
        self, api_client, enrolled_student, problem_in_set, problem_set
    ):
        """Test hint system works without course context."""
        # Create hint
        ProblemHint.objects.create(
            problem=problem_in_set,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=2,
            content={"mappings": []},
        )

        # Create progress without course context
        UserProgress.objects.create(
            user=enrolled_student,
            problem=problem_in_set,
            problem_set=problem_set,
            course=None,  # No course
            attempts=3,
        )

        api_client.force_authenticate(user=enrolled_student)

        # Access hints without course context
        hint_availability_url = reverse(
            "problem_hint_availability", kwargs={"slug": problem_in_set.slug}
        )
        response = api_client.get(
            hint_availability_url, {"problem_set_slug": problem_set.slug}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_attempts"] == 3
        assert data["available_hints"][0]["unlocked"]

        # Access hint content
        hint_content_url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem_in_set.slug, "hint_type": "variable_fade"},
        )

        response = api_client.get(
            hint_content_url, {"problem_set_slug": problem_set.slug}
        )

        assert response.status_code == status.HTTP_200_OK


class TestHintValidationEdgeCases:
    """Tests for hint validation with edge case data."""

    def test_hint_validation_edge_cases(self, api_client, admin_user, problem_in_set):
        """Test hint validation with edge case data."""
        api_client.force_authenticate(user=admin_user)
        admin_url = reverse("admin_problem_hints", kwargs={"slug": problem_in_set.slug})

        # Test with extremely large hint content
        large_mappings = []
        for i in range(1000):
            large_mappings.append(
                {"from": f"variable_{i}", "to": f"meaningful_name_{i}"}
            )

        hint_config = {
            "hints": [
                {
                    "type": "variable_fade",
                    "is_enabled": True,
                    "min_attempts": 1,
                    "content": {"mappings": large_mappings},
                }
            ]
        }

        response = api_client.put(admin_url, hint_config, format="json")
        assert response.status_code == status.HTTP_200_OK

        # Verify it was saved correctly
        hint = ProblemHint.objects.get(
            problem=problem_in_set, hint_type="variable_fade"
        )
        assert len(hint.content["mappings"]) == 1000

        # Test with Unicode content
        unicode_config = {
            "hints": [
                {
                    "type": "subgoal_highlight",
                    "is_enabled": True,
                    "min_attempts": 1,
                    "content": {
                        "subgoals": [
                            {
                                "line_start": 1,
                                "line_end": 1,
                                "title": "初期化",  # Japanese
                                "explanation": "Инициализация переменных",  # Russian
                            }
                        ]
                    },
                }
            ]
        }

        response = api_client.put(admin_url, unicode_config, format="json")
        assert response.status_code == status.HTTP_200_OK

        # Verify Unicode content is preserved
        hint = ProblemHint.objects.get(
            problem=problem_in_set, hint_type="subgoal_highlight"
        )
        assert hint.content["subgoals"][0]["title"] == "初期化"
        assert hint.content["subgoals"][0]["explanation"] == "Инициализация переменных"
