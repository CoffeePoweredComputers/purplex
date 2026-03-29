"""Integration tests for instructor analytics and export API endpoints.

Validates the HTTP contract for course analytics overview, student
list/detail, problem analytics, problem set activity, and CSV exports.
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
    SubmissionFactory,
    UserFactory,
    UserProfileFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from instructor_analytics_views.py inline dicts
# ---------------------------------------------------------------------------

# InstructorStudentListView response (instructor_analytics_views.py:129-135)
STUDENT_LIST_RESPONSE_FIELDS = {"course_id", "students", "total_students"}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def analytics_url(course_id):
    return f"/api/instructor/courses/{course_id}/analytics/"


def student_list_url(course_id):
    return f"/api/instructor/courses/{course_id}/analytics/students/"


def student_detail_url(course_id, user_id):
    return f"/api/instructor/courses/{course_id}/analytics/students/{user_id}/"


def problem_analytics_url(course_id, problem_slug):
    return f"/api/instructor/courses/{course_id}/analytics/problems/{problem_slug}/"


def ps_activity_url(course_id, ps_slug):
    return f"/api/instructor/courses/{course_id}/problem-sets/{ps_slug}/activity/"


def course_export_url(course_id):
    return f"/api/instructor/courses/{course_id}/export/"


def ps_export_url(course_id, ps_slug):
    return f"/api/instructor/courses/{course_id}/problem-sets/{ps_slug}/export/"


def problem_export_url(course_id, problem_slug):
    return f"/api/instructor/courses/{course_id}/problems/{problem_slug}/export/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def analytics_course(db, instructor):
    """Course with instructor, enrolled student, problem, and submission."""
    course = CourseFactory()
    CourseInstructorFactory(course=course, user=instructor, role="primary")
    student = UserFactory(username="analytics_student")
    UserProfileFactory(user=student)
    CourseEnrollmentFactory(user=student, course=course)
    ps = ProblemSetFactory(created_by=instructor)
    problem = EiplProblemFactory(created_by=instructor, is_active=True)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    CourseProblemSetFactory(course=course, problem_set=ps, order=0)
    submission = SubmissionFactory(
        user=student, problem=problem, problem_set=ps, course=course
    )
    UserProgressFactory(
        user=student,
        problem=problem,
        problem_set=ps,
        course=course,
        attempts=1,
        best_score=submission.score,
    )
    return {
        "course": course,
        "student": student,
        "problem_set": ps,
        "problem": problem,
    }


# ===========================================================================
# TestInstructorCourseAnalytics
# ===========================================================================
class TestInstructorCourseAnalytics:
    """GET /api/instructor/courses/{id}/analytics/"""

    def test_analytics_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(analytics_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_analytics_includes_my_role(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(analytics_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert "my_role" in resp.data
        assert resp.data["my_role"] == "primary"

    def test_analytics_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = authenticated_client.get(analytics_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_analytics_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(analytics_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# TestInstructorStudentList
# ===========================================================================
class TestInstructorStudentList:
    """GET /api/instructor/courses/{id}/analytics/students/"""

    def test_student_list_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(student_list_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_student_list_response_shape(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(student_list_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == STUDENT_LIST_RESPONSE_FIELDS
        assert resp.data["total_students"] >= 1
        assert isinstance(resp.data["students"], list)

    def test_student_list_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = authenticated_client.get(student_list_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_student_list_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(student_list_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# TestInstructorStudentDetail
# ===========================================================================
class TestInstructorStudentDetail:
    """GET /api/instructor/courses/{id}/analytics/students/{user_id}/"""

    def test_student_detail_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        student = analytics_course["student"]
        resp = instructor_client.get(student_detail_url(course.course_id, student.id))
        assert resp.status_code == status.HTTP_200_OK

    def test_student_detail_nonexistent_user_404(
        self, instructor_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = instructor_client.get(student_detail_url(course.course_id, 99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_student_detail_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        student = analytics_course["student"]
        resp = authenticated_client.get(
            student_detail_url(course.course_id, student.id)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorProblemAnalytics
# ===========================================================================
class TestInstructorProblemAnalytics:
    """GET /api/instructor/courses/{id}/analytics/problems/{slug}/"""

    def test_problem_analytics_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        problem = analytics_course["problem"]
        resp = instructor_client.get(
            problem_analytics_url(course.course_id, problem.slug)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_problem_analytics_nonexistent_problem_404(
        self, instructor_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = instructor_client.get(
            problem_analytics_url(course.course_id, "does-not-exist")
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_problem_analytics_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        problem = analytics_course["problem"]
        resp = authenticated_client.get(
            problem_analytics_url(course.course_id, problem.slug)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorProblemSetActivity
# ===========================================================================
class TestInstructorProblemSetActivity:
    """GET /api/instructor/courses/{id}/problem-sets/{slug}/activity/"""

    def test_activity_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        ps = analytics_course["problem_set"]
        resp = instructor_client.get(ps_activity_url(course.course_id, ps.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_activity_nonexistent_ps_404(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(
            ps_activity_url(course.course_id, "does-not-exist")
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_activity_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        ps = analytics_course["problem_set"]
        resp = authenticated_client.get(ps_activity_url(course.course_id, ps.slug))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorExports
# ===========================================================================
class TestInstructorExports:
    """GET /api/instructor/courses/{id}/export/ and sub-export endpoints."""

    def test_course_export_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        resp = instructor_client.get(course_export_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "text/csv"

    def test_ps_export_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        ps = analytics_course["problem_set"]
        resp = instructor_client.get(ps_export_url(course.course_id, ps.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "text/csv"

    def test_problem_export_success(self, instructor_client, analytics_course):
        course = analytics_course["course"]
        problem = analytics_course["problem"]
        resp = instructor_client.get(problem_export_url(course.course_id, problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "text/csv"

    def test_export_non_instructor_forbidden(
        self, authenticated_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = authenticated_client.get(course_export_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_export_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(course_export_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Admin accessing instructor endpoints
# ===========================================================================
class TestAdminAccessToInstructorAnalytics:
    """Admins navigate to the course overview page which calls instructor
    analytics endpoints. These use IsCourseInstructor permission which
    allows superusers. Verify admins can access them."""

    def test_admin_can_access_instructor_analytics(
        self, admin_client, analytics_course
    ):
        """Admin hits GET /api/instructor/courses/{id}/analytics/ — the same
        endpoint the InstructorCourseOverview.vue component calls."""
        course = analytics_course["course"]
        resp = admin_client.get(analytics_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_access_instructor_ps_activity(
        self, admin_client, analytics_course
    ):
        course = analytics_course["course"]
        ps = analytics_course["problem_set"]
        resp = admin_client.get(ps_activity_url(course.course_id, ps.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_access_instructor_export(self, admin_client, analytics_course):
        course = analytics_course["course"]
        resp = admin_client.get(course_export_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_access_instructor_student_list(
        self, admin_client, analytics_course
    ):
        course = analytics_course["course"]
        resp = admin_client.get(student_list_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
