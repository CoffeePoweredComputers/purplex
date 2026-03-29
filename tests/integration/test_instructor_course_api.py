"""Integration tests for instructor course API endpoints.

Validates the HTTP contract between the Vue frontend and Django backend
for course creation, listing, and detail views. Field sets are derived
from the frontend TypeScript types in purplex/client/src/types/index.ts.
"""

import pytest
from rest_framework import status

from tests.factories import (
    CourseFactory,
    CourseInstructorFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — derived from frontend types/index.ts (Course, lines 702-718)
# and InstructorCourseListSerializer (serializers.py:1426-1442)
# ---------------------------------------------------------------------------

# InstructorCourseListSerializer fields
COURSE_LIST_FIELDS = {
    "id",
    "course_id",
    "name",
    "description",
    "instructor_name",
    "is_active",
    "enrollment_open",
    "problem_sets_count",
    "enrolled_students_count",
    "created_at",
    "my_role",
}

# CourseDetailSerializer fields (serializers.py:1445-1467)
COURSE_DETAIL_FIELDS = {
    "id",
    "course_id",
    "slug",
    "name",
    "description",
    "instructors",
    "problem_sets",
    "enrolled_students_count",
    "is_active",
    "enrollment_open",
    "created_at",
    "updated_at",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def course_create_url():
    return "/api/instructor/courses/create/"


def course_list_url():
    return "/api/instructor/courses/"


def course_detail_url(course_id):
    return f"/api/instructor/courses/{course_id}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def other_instructor(db):
    """A second instructor who owns different courses."""
    u = UserFactory(username="other_instructor")
    UserProfileFactory(user=u, role="instructor")
    return u


@pytest.fixture
def other_instructor_course(db, other_instructor):
    """Course owned by the other instructor."""
    c = CourseFactory(course_id="OTHER-101")
    CourseInstructorFactory(course=c, user=other_instructor, role="primary")
    return c


# ===========================================================================
# TestInstructorCourseCreate
# ===========================================================================
class TestInstructorCourseCreate:
    """POST /api/instructor/courses/create/"""

    def test_create_course_success(self, instructor_client):
        data = {
            "course_id": "CS-101",
            "name": "Intro to CS",
            "description": "An introductory course",
        }
        resp = instructor_client.post(course_create_url(), data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["course_id"] == "CS-101"
        assert resp.data["name"] == "Intro to CS"

    def test_create_course_response_shape(self, instructor_client):
        data = {"course_id": "CS-102", "name": "Data Structures"}
        resp = instructor_client.post(course_create_url(), data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert set(resp.data.keys()) == COURSE_DETAIL_FIELDS

    def test_create_course_unauthenticated(self, api_client):
        data = {"course_id": "CS-103", "name": "Fail"}
        resp = api_client.post(course_create_url(), data, format="json")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_course_student_forbidden(self, authenticated_client):
        data = {"course_id": "CS-104", "name": "Fail"}
        resp = authenticated_client.post(course_create_url(), data, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_course_missing_required_fields(self, instructor_client):
        resp = instructor_client.post(course_create_url(), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# TestInstructorCourseList
# ===========================================================================
class TestInstructorCourseList:
    """GET /api/instructor/courses/"""

    def test_list_courses_success(self, instructor_client, course):
        resp = instructor_client.get(course_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_list_courses_response_shape(self, instructor_client, course):
        resp = instructor_client.get(course_list_url())
        assert resp.status_code == status.HTTP_200_OK
        item = resp.data[0]
        assert set(item.keys()) == COURSE_LIST_FIELDS

    def test_list_only_own_courses(
        self, instructor_client, course, other_instructor_course
    ):
        resp = instructor_client.get(course_list_url())
        course_ids = [c["course_id"] for c in resp.data]
        assert course.course_id in course_ids
        assert "OTHER-101" not in course_ids

    def test_list_courses_unauthenticated(self, api_client):
        resp = api_client.get(course_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_courses_student_forbidden(self, authenticated_client):
        resp = authenticated_client.get(course_list_url())
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_includes_instructor_name(self, instructor_client, course):
        """Frontend expects instructor_name on every Course object."""
        resp = instructor_client.get(course_list_url())
        item = resp.data[0]
        assert "instructor_name" in item
        assert item["instructor_name"] != "Unknown Instructor"


# ===========================================================================
# TestInstructorCourseDetail
# ===========================================================================
class TestInstructorCourseDetail:
    """GET /api/instructor/courses/{course_id}/"""

    def test_get_course_success(self, instructor_client, course):
        resp = instructor_client.get(course_detail_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["course_id"] == course.course_id

    def test_get_course_response_shape(self, instructor_client, course):
        resp = instructor_client.get(course_detail_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == COURSE_DETAIL_FIELDS

    def test_get_course_includes_instructors(self, instructor_client, course_with_team):
        resp = instructor_client.get(course_detail_url(course_with_team.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data["instructors"], list)
        assert len(resp.data["instructors"]) == 2

    def test_get_course_includes_problem_sets(
        self, instructor_client, course, course_problem_set
    ):
        resp = instructor_client.get(course_detail_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data["problem_sets"], list)
        assert len(resp.data["problem_sets"]) >= 1

    def test_get_course_unauthenticated(self, api_client, course):
        resp = api_client.get(course_detail_url(course.course_id))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_course_non_instructor_forbidden(self, authenticated_client, course):
        resp = authenticated_client.get(course_detail_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_course_nonexistent_404(self, instructor_client):
        resp = instructor_client.get(course_detail_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
