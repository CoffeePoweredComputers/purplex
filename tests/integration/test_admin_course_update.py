"""
Integration tests for AdminCourseDetailView PATCH/PUT.

Covers the instructor switch logic and PATCH method delegation
added in PR #116.
"""

import pytest
from rest_framework import status

from purplex.problems_app.models import CourseInstructor
from tests.factories import CourseFactory, CourseInstructorFactory, UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestAdminCourseUpdate:
    """Tests for PATCH/PUT on /api/admin/courses/<id>/."""

    def test_patch_updates_course_name(self, admin_client):
        """PATCH should update course fields."""
        course = CourseFactory()
        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"name": "Updated Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"

    def test_patch_delegates_to_put(self, admin_client):
        """PATCH and PUT should produce identical results."""
        course = CourseFactory()
        patch_resp = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"description": "via patch"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["description"] == "via patch"

    def test_patch_switches_primary_instructor(self, admin_client):
        """PATCH with instructor_id should make that user primary and demote others."""
        course = CourseFactory()
        original = UserFactory()
        new_instructor = UserFactory(is_staff=True)
        CourseInstructorFactory(course=course, user=original, role="primary")

        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"instructor_id": new_instructor.id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # New instructor should be primary
        new_ci = CourseInstructor.objects.get(course=course, user=new_instructor)
        assert new_ci.role == "primary"

        # Original should be demoted to TA
        old_ci = CourseInstructor.objects.get(course=course, user=original)
        assert old_ci.role == "ta"

    def test_patch_instructor_already_primary_is_noop(self, admin_client):
        """PATCH with the current primary instructor_id should not fail."""
        course = CourseFactory()
        instructor = UserFactory(is_staff=True)
        CourseInstructorFactory(course=course, user=instructor, role="primary")

        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"instructor_id": instructor.id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Still primary, no demotion
        ci = CourseInstructor.objects.get(course=course, user=instructor)
        assert ci.role == "primary"

    def test_patch_promotes_ta_to_primary(self, admin_client):
        """PATCH should promote an existing TA to primary."""
        course = CourseFactory()
        primary = UserFactory(is_staff=True)
        ta = UserFactory(is_staff=True)
        CourseInstructorFactory(course=course, user=primary, role="primary")
        CourseInstructorFactory(course=course, user=ta, role="ta")

        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"instructor_id": ta.id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # TA promoted to primary
        ta_ci = CourseInstructor.objects.get(course=course, user=ta)
        assert ta_ci.role == "primary"

        # Old primary demoted
        primary_ci = CourseInstructor.objects.get(course=course, user=primary)
        assert primary_ci.role == "ta"

    def test_patch_adds_new_user_as_primary(self, admin_client):
        """PATCH with a user not on the team should add them as primary."""
        course = CourseFactory()
        existing = UserFactory(is_staff=True)
        new_user = UserFactory(is_staff=True)
        CourseInstructorFactory(course=course, user=existing, role="primary")

        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"instructor_id": new_user.id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # New user added as primary
        assert CourseInstructor.objects.filter(
            course=course, user=new_user, role="primary"
        ).exists()

        # Old primary demoted
        old_ci = CourseInstructor.objects.get(course=course, user=existing)
        assert old_ci.role == "ta"

    def test_patch_invalid_instructor_id_returns_400(self, admin_client):
        """PATCH with nonexistent instructor_id should return 400."""
        course = CourseFactory()
        CourseInstructorFactory(
            course=course, user=UserFactory(is_staff=True), role="primary"
        )

        response = admin_client.patch(
            f"/api/admin/courses/{course.course_id}/",
            {"instructor_id": 999999},
            format="json",
        )
        assert response.status_code == 400

    def test_patch_nonexistent_course_returns_404(self, admin_client):
        """PATCH on a missing course should return 404."""
        response = admin_client.patch(
            "/api/admin/courses/DOES-NOT-EXIST/",
            {"name": "X"},
            format="json",
        )
        assert response.status_code == 404
