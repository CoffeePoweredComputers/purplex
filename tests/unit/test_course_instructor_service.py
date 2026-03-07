"""Unit tests for CourseService multi-instructor methods."""

import pytest

from purplex.problems_app.services.course_service import CourseService
from tests.factories import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestAddCourseInstructor:
    def test_delegates_to_repo(self, course):
        new_user = UserFactory()
        ci = CourseService.add_course_instructor(course, new_user, role="ta")
        assert ci.user == new_user
        assert ci.role == "ta"

    def test_passes_added_by(self, course, instructor):
        new_user = UserFactory()
        ci = CourseService.add_course_instructor(
            course, new_user, role="ta", added_by=instructor
        )
        assert ci.added_by == instructor


class TestRemoveCourseInstructor:
    def test_success_dict(self, course_with_team, ta_user):
        result = CourseService.remove_course_instructor(course_with_team, ta_user)
        assert result["success"] is True

    def test_not_found_error(self, course):
        stranger = UserFactory()
        result = CourseService.remove_course_instructor(course, stranger)
        assert result["success"] is False
        assert "not an instructor" in result["error"]

    def test_last_primary_error(self, course, instructor):
        result = CourseService.remove_course_instructor(course, instructor)
        assert result["success"] is False
        assert "last primary" in result["error"]


class TestUpdateCourseInstructorRole:
    def test_success(self, course_with_team, ta_user):
        result = CourseService.update_course_instructor_role(
            course_with_team, ta_user, "primary"
        )
        assert result["success"] is True
        assert result["course_instructor"].role == "primary"

    def test_not_found(self, course):
        stranger = UserFactory()
        result = CourseService.update_course_instructor_role(course, stranger, "ta")
        assert result["success"] is False

    def test_last_primary_demotion(self, course, instructor):
        result = CourseService.update_course_instructor_role(course, instructor, "ta")
        assert result["success"] is False
        assert "last primary" in result["error"]


class TestGetCourseInstructors:
    def test_returns_list(self, course_with_team):
        result = CourseService.get_course_instructors(course_with_team)
        assert len(result) == 2
