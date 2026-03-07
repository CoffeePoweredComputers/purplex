"""Unit tests for CourseInstructorRepository."""

import pytest
from django.db import IntegrityError

from purplex.problems_app.repositories.course_instructor_repository import (
    CourseInstructorRepository,
)
from tests.factories import (
    CourseFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestGetCourseInstructors:
    def test_returns_all_for_course(self, course_with_team, instructor, ta_user):
        result = CourseInstructorRepository.get_course_instructors(course_with_team)
        users = [ci.user for ci in result]
        assert instructor in users
        assert ta_user in users

    def test_filters_by_role(self, course_with_team, instructor, ta_user):
        primaries = CourseInstructorRepository.get_course_instructors(
            course_with_team, role="primary"
        )
        assert len(primaries) == 1
        assert primaries[0].user == instructor

        tas = CourseInstructorRepository.get_course_instructors(
            course_with_team, role="ta"
        )
        assert len(tas) == 1
        assert tas[0].user == ta_user

    def test_empty_returns_empty(self, db):
        course = CourseFactory()
        result = CourseInstructorRepository.get_course_instructors(course)
        assert result == []

    def test_ordering_by_role_then_added_at(self, course_with_team):
        result = CourseInstructorRepository.get_course_instructors(course_with_team)
        roles = [ci.role for ci in result]
        # "primary" < "ta" alphabetically
        assert roles == sorted(roles)


class TestIsCourseInstructor:
    def test_true_for_primary(self, instructor, course):
        assert (
            CourseInstructorRepository.is_course_instructor(instructor, course) is True
        )

    def test_true_for_ta(self, ta_user, course_with_team):
        assert (
            CourseInstructorRepository.is_course_instructor(ta_user, course_with_team)
            is True
        )

    def test_false_for_non_instructor(self, course):
        stranger = UserFactory()
        assert (
            CourseInstructorRepository.is_course_instructor(stranger, course) is False
        )


class TestGetRole:
    def test_returns_primary(self, instructor, course):
        assert CourseInstructorRepository.get_role(instructor, course) == "primary"

    def test_returns_ta(self, ta_user, course_with_team):
        assert CourseInstructorRepository.get_role(ta_user, course_with_team) == "ta"

    def test_returns_none(self, course):
        stranger = UserFactory()
        assert CourseInstructorRepository.get_role(stranger, course) is None


class TestAddInstructor:
    def test_creates_row(self, course):
        new_user = UserFactory()
        ci = CourseInstructorRepository.add_instructor(course, new_user, role="ta")
        assert ci.course == course
        assert ci.user == new_user
        assert ci.role == "ta"

    def test_sets_added_by(self, course, instructor):
        new_user = UserFactory()
        ci = CourseInstructorRepository.add_instructor(
            course, new_user, role="ta", added_by=instructor
        )
        assert ci.added_by == instructor

    def test_duplicate_raises_integrity_error(self, course, instructor):
        with pytest.raises(IntegrityError):
            CourseInstructorRepository.add_instructor(
                course, instructor, role="primary"
            )


class TestRemoveInstructor:
    def test_removes_successfully(self, course_with_team, ta_user):
        assert (
            CourseInstructorRepository.remove_instructor(course_with_team, ta_user)
            is True
        )
        assert (
            CourseInstructorRepository.is_course_instructor(ta_user, course_with_team)
            is False
        )

    def test_false_for_nonexistent(self, course):
        stranger = UserFactory()
        assert CourseInstructorRepository.remove_instructor(course, stranger) is False

    def test_raises_on_last_primary(self, course, instructor):
        with pytest.raises(ValueError, match="last primary"):
            CourseInstructorRepository.remove_instructor(course, instructor)

    def test_allows_removing_ta_with_one_primary(self, course_with_team, ta_user):
        assert (
            CourseInstructorRepository.remove_instructor(course_with_team, ta_user)
            is True
        )

    def test_allows_removing_primary_when_multiple(self, course_with_team, instructor):
        # Add a second primary
        second_primary = UserFactory()
        CourseInstructorRepository.add_instructor(
            course_with_team, second_primary, role="primary"
        )
        assert (
            CourseInstructorRepository.remove_instructor(course_with_team, instructor)
            is True
        )


class TestUpdateRole:
    def test_promotes_ta(self, course_with_team, ta_user):
        ci = CourseInstructorRepository.update_role(
            course_with_team, ta_user, "primary"
        )
        assert ci.role == "primary"

    def test_demotes_primary_when_multiple(self, course_with_team, instructor):
        # Add second primary so demotion is allowed
        second = UserFactory()
        CourseInstructorRepository.add_instructor(
            course_with_team, second, role="primary"
        )
        ci = CourseInstructorRepository.update_role(course_with_team, instructor, "ta")
        assert ci.role == "ta"

    def test_raises_on_demoting_last_primary(self, course, instructor):
        with pytest.raises(ValueError, match="last primary"):
            CourseInstructorRepository.update_role(course, instructor, "ta")

    def test_none_for_nonexistent(self, course):
        stranger = UserFactory()
        assert CourseInstructorRepository.update_role(course, stranger, "ta") is None


class TestGetCoursesForUser:
    def test_returns_courses(self, instructor, course):
        result = CourseInstructorRepository.get_courses_for_user(instructor.id)
        assert len(result) == 1
        assert result[0]["course__course_id"] == course.course_id

    def test_filters_by_role(self, ta_user, course_with_team):
        as_primary = CourseInstructorRepository.get_courses_for_user(
            ta_user.id, role="primary"
        )
        assert len(as_primary) == 0
        as_ta = CourseInstructorRepository.get_courses_for_user(ta_user.id, role="ta")
        assert len(as_ta) == 1

    def test_excludes_deleted(self, instructor, course):
        course.is_deleted = True
        course.save()
        result = CourseInstructorRepository.get_courses_for_user(instructor.id)
        assert len(result) == 0


class TestGetPrimaryInstructorNames:
    def test_single(self, instructor, course):
        instructor.first_name = "Jane"
        instructor.last_name = "Doe"
        instructor.save()
        result = CourseInstructorRepository.get_primary_instructor_names(course)
        assert result == "Jane Doe"

    def test_multiple_comma_joined(self, course):
        second = UserFactory(first_name="Bob", last_name="Smith")
        CourseInstructorRepository.add_instructor(course, second, role="primary")
        result = CourseInstructorRepository.get_primary_instructor_names(course)
        assert "," in result

    def test_empty_returns_empty(self, db):
        course = CourseFactory()
        result = CourseInstructorRepository.get_primary_instructor_names(course)
        assert result == ""

    def test_uses_full_name_or_username(self, course, instructor):
        # No first/last name set, should fall back to username
        instructor.first_name = ""
        instructor.last_name = ""
        instructor.save()
        result = CourseInstructorRepository.get_primary_instructor_names(course)
        assert result == instructor.username
