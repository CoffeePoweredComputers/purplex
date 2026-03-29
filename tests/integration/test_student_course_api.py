"""Integration tests for student course enrollment API endpoints.

Validates the HTTP contract for course lookup, enrollment, detail,
and progress — the core student course workflow.
"""

import pytest
from rest_framework import status

from tests.factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    CourseInstructorFactory,
    CourseProblemSetFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from inline dicts in course_views.py and frontend types
# ---------------------------------------------------------------------------

# CourseLookupView response (course_views.py:297-308)
LOOKUP_FIELDS = {"course", "already_enrolled"}
LOOKUP_COURSE_FIELDS = {
    "course_id",
    "name",
    "description",
    "instructor",
    "problem_sets_count",
    "enrollment_open",
}

# CourseEnrollView response (course_views.py:336-343)
ENROLL_FIELDS = {"success", "course", "enrolled_at"}

# CourseDetailSerializer (serializers.py:1445-1467)
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
def enrolled_url():
    return "/api/courses/enrolled/"


def lookup_url():
    return "/api/courses/lookup/"


def enroll_url():
    return "/api/courses/enroll/"


def course_detail_url(course_id):
    return f"/api/courses/{course_id}/"


def course_progress_url(course_id):
    return f"/api/courses/{course_id}/progress/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def enrollable_course(db):
    """Active course with enrollment open, problem set, and instructor."""
    instructor_user = UserFactory(username="enroll_instructor")
    UserProfileFactory(user=instructor_user, role="instructor")
    course = CourseFactory(is_active=True, enrollment_open=True)
    CourseInstructorFactory(course=course, user=instructor_user, role="primary")
    ps = ProblemSetFactory(created_by=instructor_user)
    problem = EiplProblemFactory(created_by=instructor_user, is_active=True)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    CourseProblemSetFactory(course=course, problem_set=ps, order=0)
    return course


@pytest.fixture
def enrolled_user_course(db, user, enrollable_course):
    """User already enrolled in a course."""
    CourseEnrollmentFactory(user=user, course=enrollable_course)
    return enrollable_course


@pytest.fixture
def closed_course(db):
    """Course with enrollment closed."""
    instructor_user = UserFactory(username="closed_instructor")
    UserProfileFactory(user=instructor_user, role="instructor")
    course = CourseFactory(is_active=True, enrollment_open=False)
    CourseInstructorFactory(course=course, user=instructor_user, role="primary")
    return course


# ===========================================================================
# TestStudentEnrolledCourses
# ===========================================================================
class TestStudentEnrolledCourses:
    """GET /api/courses/enrolled/"""

    def test_list_enrolled_courses(self, authenticated_client, enrolled_user_course):
        resp = authenticated_client.get(enrolled_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_list_empty_when_not_enrolled(self, authenticated_client):
        resp = authenticated_client.get(enrolled_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_unauthenticated_forbidden(self, api_client):
        resp = api_client.get(enrolled_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestCourseLookup
# ===========================================================================
class TestCourseLookup:
    """POST /api/courses/lookup/"""

    def test_lookup_success(self, authenticated_client, enrollable_course):
        resp = authenticated_client.post(
            lookup_url(), {"course_id": enrollable_course.course_id}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_lookup_response_shape(self, authenticated_client, enrollable_course):
        resp = authenticated_client.post(
            lookup_url(), {"course_id": enrollable_course.course_id}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == LOOKUP_FIELDS
        assert set(resp.data["course"].keys()) == LOOKUP_COURSE_FIELDS

    def test_lookup_shows_not_enrolled(self, authenticated_client, enrollable_course):
        resp = authenticated_client.post(
            lookup_url(), {"course_id": enrollable_course.course_id}, format="json"
        )
        assert resp.data["already_enrolled"] is False

    def test_lookup_shows_already_enrolled(
        self, authenticated_client, enrolled_user_course
    ):
        resp = authenticated_client.post(
            lookup_url(),
            {"course_id": enrolled_user_course.course_id},
            format="json",
        )
        assert resp.data["already_enrolled"] is True

    def test_lookup_nonexistent_course_404(self, authenticated_client):
        resp = authenticated_client.post(
            lookup_url(), {"course_id": "DOES-NOT-EXIST"}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_lookup_missing_course_id_400(self, authenticated_client):
        resp = authenticated_client.post(lookup_url(), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_lookup_unauthenticated(self, api_client):
        resp = api_client.post(lookup_url(), {"course_id": "ANY"}, format="json")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestCourseEnroll
# ===========================================================================
class TestCourseEnroll:
    """POST /api/courses/enroll/"""

    def test_enroll_success(self, authenticated_client, enrollable_course):
        resp = authenticated_client.post(
            enroll_url(), {"course_id": enrollable_course.course_id}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_enroll_response_shape(self, authenticated_client, enrollable_course):
        resp = authenticated_client.post(
            enroll_url(), {"course_id": enrollable_course.course_id}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert set(resp.data.keys()) == ENROLL_FIELDS
        assert resp.data["success"] is True
        # course should be a CourseDetailSerializer response
        assert set(resp.data["course"].keys()) == COURSE_DETAIL_FIELDS

    @pytest.mark.xfail(
        reason=(
            "CourseService.enroll_user_in_course() returns success=False with "
            "'already enrolled' error when user is already enrolled, causing "
            "the view to return 400. The frontend expects a graceful 200 response "
            "for idempotent re-enrollment attempts."
        ),
        strict=True,
    )
    def test_enroll_already_enrolled_200(
        self, authenticated_client, enrolled_user_course
    ):
        resp = authenticated_client.post(
            enroll_url(),
            {"course_id": enrolled_user_course.course_id},
            format="json",
        )
        # Should return 200 (not 201) since already enrolled
        assert resp.status_code == status.HTTP_200_OK

    def test_enroll_nonexistent_course(self, authenticated_client):
        resp = authenticated_client.post(
            enroll_url(), {"course_id": "DOES-NOT-EXIST"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_enroll_missing_course_id(self, authenticated_client):
        resp = authenticated_client.post(enroll_url(), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_enroll_unauthenticated(self, api_client):
        resp = api_client.post(enroll_url(), {"course_id": "ANY"}, format="json")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestStudentCourseDetail
# ===========================================================================
class TestStudentCourseDetail:
    """GET /api/courses/{course_id}/"""

    def test_get_enrolled_course(self, authenticated_client, enrolled_user_course):
        resp = authenticated_client.get(
            course_detail_url(enrolled_user_course.course_id)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_get_enrolled_course_response_shape(
        self, authenticated_client, enrolled_user_course
    ):
        resp = authenticated_client.get(
            course_detail_url(enrolled_user_course.course_id)
        )
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == COURSE_DETAIL_FIELDS

    def test_get_not_enrolled_forbidden(self, authenticated_client, enrollable_course):
        resp = authenticated_client.get(course_detail_url(enrollable_course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_nonexistent_course_404(self, authenticated_client):
        resp = authenticated_client.get(course_detail_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_forbidden(self, api_client, enrollable_course):
        resp = api_client.get(course_detail_url(enrollable_course.course_id))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestStudentCourseProgress
# ===========================================================================
class TestStudentCourseProgress:
    """GET /api/courses/{course_id}/progress/"""

    @pytest.mark.xfail(
        reason=(
            "CourseService.get_student_course_progress() calls "
            "CourseRepository.get_course_problem_sets() which doesn't exist — "
            "the actual method is get_course_problem_sets_with_data(). "
            "This causes an AttributeError → 500 on every request."
        ),
        strict=True,
    )
    def test_progress_success(self, authenticated_client, enrolled_user_course):
        resp = authenticated_client.get(
            course_progress_url(enrolled_user_course.course_id)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_progress_not_enrolled_forbidden(
        self, authenticated_client, enrollable_course
    ):
        resp = authenticated_client.get(
            course_progress_url(enrollable_course.course_id)
        )
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_progress_nonexistent_course_404(self, authenticated_client):
        resp = authenticated_client.get(course_progress_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_progress_unauthenticated(self, api_client, enrollable_course):
        resp = api_client.get(course_progress_url(enrollable_course.course_id))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
