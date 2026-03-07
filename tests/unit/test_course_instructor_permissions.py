"""Unit tests for IsCourseInstructor and IsPrimaryCourseInstructor permissions."""

from unittest.mock import MagicMock

import pytest

from purplex.users_app.permissions import IsCourseInstructor, IsPrimaryCourseInstructor
from tests.factories import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_request(user):
    """Build a minimal mock request."""
    request = MagicMock()
    request.user = user
    return request


class TestIsCourseInstructorPermission:
    def test_superuser_passes(self, course):
        user = UserFactory(is_superuser=True)
        request = _make_request(user)
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, course) is True

    def test_primary_passes(self, course, instructor):
        request = _make_request(instructor)
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, course) is True

    def test_ta_passes(self, course_with_team, ta_user):
        request = _make_request(ta_user)
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, course_with_team) is True

    def test_non_instructor_fails(self, course):
        stranger = UserFactory()
        request = _make_request(stranger)
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, course) is False

    def test_unauthenticated_fails(self, course):
        request = MagicMock()
        request.user = None
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, course) is False

    def test_no_legacy_fallback(self, db):
        """Legacy FK fallback was removed — objects without course_instructors are denied."""
        user = UserFactory()
        obj = MagicMock(spec=[])
        del obj.course_instructors
        del obj.is_instructor

        request = _make_request(user)
        perm = IsCourseInstructor()
        assert perm.has_object_permission(request, None, obj) is False


class TestIsPrimaryCourseInstructorPermission:
    def test_superuser_passes(self, course):
        user = UserFactory(is_superuser=True)
        request = _make_request(user)
        perm = IsPrimaryCourseInstructor()
        assert perm.has_object_permission(request, None, course) is True

    def test_primary_passes(self, course, instructor):
        request = _make_request(instructor)
        perm = IsPrimaryCourseInstructor()
        assert perm.has_object_permission(request, None, course) is True

    def test_ta_fails(self, course_with_team, ta_user):
        request = _make_request(ta_user)
        perm = IsPrimaryCourseInstructor()
        assert perm.has_object_permission(request, None, course_with_team) is False

    def test_non_instructor_fails(self, course):
        stranger = UserFactory()
        request = _make_request(stranger)
        perm = IsPrimaryCourseInstructor()
        assert perm.has_object_permission(request, None, course) is False
