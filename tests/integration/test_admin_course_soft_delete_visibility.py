"""Integration tests for admin API visibility of soft-deleted courses.

Verifies that AdminCourseListCreateView.get() at /api/admin/courses/
correctly handles soft-deleted courses: they appear in the default listing
but are excluded when ?active_only=true is passed.
"""

import pytest

from tests.factories import CourseFactory, CourseInstructorFactory, UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

ADMIN_COURSES_URL = "/api/admin/courses/"


class TestAdminCourseListSoftDeleteVisibility:
    """GET /api/admin/courses/ should respect soft-delete filtering."""

    def test_soft_deleted_course_visible_without_active_only(self, admin_client):
        """Soft-deleted courses appear in the default admin listing."""
        instructor = UserFactory()

        active_course = CourseFactory(name="Active Course")
        CourseInstructorFactory(course=active_course, user=instructor, role="primary")

        deleted_course = CourseFactory(name="Deleted Course")
        CourseInstructorFactory(course=deleted_course, user=instructor, role="primary")
        deleted_course.soft_delete()

        resp = admin_client.get(ADMIN_COURSES_URL)

        assert resp.status_code == 200
        course_ids = [c["course_id"] for c in resp.data]
        assert active_course.course_id in course_ids
        assert deleted_course.course_id in course_ids

    def test_soft_deleted_course_hidden_with_active_only(self, admin_client):
        """Soft-deleted courses are excluded when ?active_only=true."""
        instructor = UserFactory()

        active_course = CourseFactory(name="Active Course")
        CourseInstructorFactory(course=active_course, user=instructor, role="primary")

        deleted_course = CourseFactory(name="Deleted Course")
        CourseInstructorFactory(course=deleted_course, user=instructor, role="primary")
        deleted_course.soft_delete()

        resp = admin_client.get(ADMIN_COURSES_URL, {"active_only": "true"})

        assert resp.status_code == 200
        course_ids = [c["course_id"] for c in resp.data]
        assert active_course.course_id in course_ids
        assert deleted_course.course_id not in course_ids
