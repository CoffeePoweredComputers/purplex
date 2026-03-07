"""Unit tests for Course model multi-instructor methods."""

import pytest

from tests.factories import (
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestCourseIsInstructor:
    """Tests for Course.is_instructor()."""

    def test_true_for_primary(self, instructor, course):
        assert course.is_instructor(instructor) is True

    def test_true_for_ta(self, course_with_team, ta_user):
        assert course_with_team.is_instructor(ta_user) is True

    def test_false_for_stranger(self, course):
        stranger = UserFactory(username="stranger")
        assert course.is_instructor(stranger) is False


class TestCourseIsPrimaryInstructor:
    """Tests for Course.is_primary_instructor()."""

    def test_true_for_primary(self, instructor, course):
        assert course.is_primary_instructor(instructor) is True

    def test_false_for_ta(self, course_with_team, ta_user):
        assert course_with_team.is_primary_instructor(ta_user) is False


class TestGetPrimaryInstructors:
    """Tests for Course.get_primary_instructors()."""

    def test_returns_queryset_of_primaries_only(
        self, course_with_team, instructor, ta_user
    ):
        primaries = course_with_team.get_primary_instructors()
        users = [ci.user for ci in primaries]
        assert instructor in users
        assert ta_user not in users
