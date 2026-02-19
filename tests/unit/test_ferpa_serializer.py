"""
Tests for CourseEnrollmentSerializer — FERPA directory info masking.

Covers: visible directory info, opted-out masking, default behavior
when no profile exists, and field presence.
"""

import pytest

from purplex.problems_app.serializers import CourseEnrollmentSerializer
from tests.factories import (
    CourseEnrollmentFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestCourseEnrollmentSerializer:
    """Tests for FERPA directory info opt-out in CourseEnrollmentSerializer."""

    def test_visible_user_shows_email(self):
        user = UserFactory(
            email="visible@example.com", first_name="Alice", last_name="Smith"
        )
        UserProfileFactory(user=user, directory_info_visible=True)
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        data = serializer.data
        assert data["email"] == "visible@example.com"
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Smith"

    def test_opted_out_user_hides_email(self):
        user = UserFactory(
            email="hidden@example.com", first_name="Bob", last_name="Jones"
        )
        UserProfileFactory(user=user, directory_info_visible=False)
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        data = serializer.data
        assert data["email"] is None
        assert data["first_name"] is None
        assert data["last_name"] is None

    def test_username_always_visible(self):
        user = UserFactory()
        UserProfileFactory(user=user, directory_info_visible=False)
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        data = serializer.data
        assert data["username"] == user.username

    def test_user_id_always_visible(self):
        user = UserFactory()
        UserProfileFactory(user=user, directory_info_visible=False)
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        data = serializer.data
        assert data["user_id"] == user.id

    def test_no_profile_defaults_to_visible(self):
        """User without a UserProfile — should show email/name (default visible)."""
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="noprofile_user",
            email="noprofile@example.com",
            password="test123",
            first_name="Charlie",
            last_name="Brown",
        )
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        data = serializer.data
        assert data["email"] == "noprofile@example.com"
        assert data["first_name"] == "Charlie"

    def test_serializer_includes_expected_fields(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        enrollment = CourseEnrollmentFactory(user=user)
        serializer = CourseEnrollmentSerializer(enrollment)
        expected_fields = {
            "id",
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "enrolled_at",
            "is_active",
        }
        assert set(serializer.data.keys()) == expected_fields
