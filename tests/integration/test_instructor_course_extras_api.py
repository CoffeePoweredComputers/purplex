"""Integration tests for instructor course management extras.

Covers: students list, course progress, problem set reorder,
available problem sets, and admin course-PS management.
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
# URL helpers
# ---------------------------------------------------------------------------
def students_url(course_id):
    return f"/api/instructor/courses/{course_id}/students/"


def progress_url(course_id):
    return f"/api/instructor/courses/{course_id}/progress/"


def reorder_url(course_id):
    return f"/api/instructor/courses/{course_id}/problem-sets/reorder/"


def available_ps_url(course_id):
    return f"/api/instructor/courses/{course_id}/available-problem-sets/"


def admin_course_ps_url(course_id):
    return f"/api/admin/courses/{course_id}/problem-sets/"


def admin_course_ps_detail_url(course_id, ps_slug):
    return f"/api/admin/courses/{course_id}/problem-sets/{ps_slug}/"


def admin_course_students_url(course_id):
    return f"/api/admin/courses/{course_id}/students/"


def admin_course_student_url(course_id, user_id):
    return f"/api/admin/courses/{course_id}/students/{user_id}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def course_with_student(db, instructor):
    """Course with enrolled student and problem set."""
    course = CourseFactory()
    CourseInstructorFactory(course=course, user=instructor, role="primary")
    student = UserFactory(username="course_extras_student")
    UserProfileFactory(user=student)
    CourseEnrollmentFactory(user=student, course=course)
    ps = ProblemSetFactory(created_by=instructor)
    problem = EiplProblemFactory(created_by=instructor, is_active=True)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    CourseProblemSetFactory(course=course, problem_set=ps, order=0)
    return {
        "course": course,
        "student": student,
        "problem_set": ps,
        "problem": problem,
    }


@pytest.fixture
def unassigned_problem_set(db, instructor):
    """Problem set not assigned to any course."""
    return ProblemSetFactory(created_by=instructor, title="Unassigned PS")


# ===========================================================================
# TestInstructorCourseStudents
# ===========================================================================
class TestInstructorCourseStudents:
    """GET /api/instructor/courses/{id}/students/"""

    def test_list_students_success(self, instructor_client, course_with_student):
        course = course_with_student["course"]
        resp = instructor_client.get(students_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_list_students_non_instructor_forbidden(
        self, authenticated_client, course_with_student
    ):
        course = course_with_student["course"]
        resp = authenticated_client.get(students_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_students_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(students_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# TestInstructorCourseProgress
# ===========================================================================
class TestInstructorCourseProgress:
    """GET /api/instructor/courses/{id}/progress/"""

    def test_progress_success(self, instructor_client, course_with_student):
        course = course_with_student["course"]
        resp = instructor_client.get(progress_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_progress_non_instructor_forbidden(
        self, authenticated_client, course_with_student
    ):
        course = course_with_student["course"]
        resp = authenticated_client.get(progress_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_progress_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(progress_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# TestInstructorReorder
# ===========================================================================
class TestInstructorReorder:
    """PUT /api/instructor/courses/{id}/problem-sets/reorder/"""

    def test_reorder_success(self, instructor_client, course_with_student):
        course = course_with_student["course"]
        # Get the existing CPS to build ordering data
        from purplex.problems_app.models import CourseProblemSet

        cps_list = CourseProblemSet.objects.filter(course=course)
        ordering = [
            {"problem_set_id": cps.id, "order": i} for i, cps in enumerate(cps_list)
        ]
        resp = instructor_client.put(
            reorder_url(course.course_id),
            {"ordering": ordering},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_reorder_non_instructor_forbidden(
        self, authenticated_client, course_with_student
    ):
        course = course_with_student["course"]
        resp = authenticated_client.put(
            reorder_url(course.course_id), {"ordering": []}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorAvailableProblemSets
# ===========================================================================
class TestInstructorAvailableProblemSets:
    """GET /api/instructor/courses/{id}/available-problem-sets/"""

    def test_available_ps_success(
        self, instructor_client, course_with_student, unassigned_problem_set
    ):
        course = course_with_student["course"]
        resp = instructor_client.get(available_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_available_ps_non_instructor_forbidden(
        self, authenticated_client, course_with_student
    ):
        course = course_with_student["course"]
        resp = authenticated_client.get(available_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestAdminCourseProblemSets
# ===========================================================================
class TestAdminCourseProblemSets:
    """GET/POST /api/admin/courses/{id}/problem-sets/"""

    def test_list_success(self, admin_client, course_with_student):
        course = course_with_student["course"]
        resp = admin_client.get(admin_course_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_add_ps_to_course(
        self, admin_client, course_with_student, unassigned_problem_set
    ):
        course = course_with_student["course"]
        resp = admin_client.post(
            admin_course_ps_url(course.course_id),
            {"problem_set_slug": unassigned_problem_set.slug},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_add_nonexistent_ps_404(self, admin_client, course_with_student):
        course = course_with_student["course"]
        resp = admin_client.post(
            admin_course_ps_url(course.course_id),
            {"problem_set_slug": "does-not-exist"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_non_admin_forbidden(self, authenticated_client, course_with_student):
        course = course_with_student["course"]
        resp = authenticated_client.get(admin_course_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestAdminCourseStudents
# ===========================================================================
class TestAdminCourseStudents:
    """GET/DELETE /api/admin/courses/{id}/students/"""

    def test_list_students_success(self, admin_client, course_with_student):
        course = course_with_student["course"]
        resp = admin_client.get(admin_course_students_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_remove_student(self, admin_client, course_with_student):
        course = course_with_student["course"]
        student = course_with_student["student"]
        resp = admin_client.delete(
            admin_course_student_url(course.course_id, student.id)
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_remove_nonexistent_student(self, admin_client, course_with_student):
        course = course_with_student["course"]
        resp = admin_client.delete(admin_course_student_url(course.course_id, 99999))
        assert resp.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_list_non_admin_forbidden(self, authenticated_client, course_with_student):
        course = course_with_student["course"]
        resp = authenticated_client.get(admin_course_students_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
