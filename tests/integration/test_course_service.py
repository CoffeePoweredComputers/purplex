"""
Tests for CourseService business logic.

Tests:
- Course creation and management
- Problem set management (add, remove, update, reorder)
- Course enrollment and validation
- Student management
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from purplex.problems_app.models import Course, CourseEnrollment, CourseProblemSet
from purplex.problems_app.services.course_service import CourseService

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Course Creation and Management
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceCreateCourse:
    """Tests for CourseService.create_course()."""

    def test_create_course_basic(self, instructor):
        """Create a course with required fields."""
        course = CourseService.create_course(
            instructor=instructor,
            course_id="CS101-TEST",
            name="Test Course",
        )
        assert course.course_id == "CS101-TEST"
        assert course.name == "Test Course"
        assert course.is_instructor(instructor)
        assert course.is_active is True

    def test_create_course_with_description(self, instructor):
        """Create a course with description."""
        course = CourseService.create_course(
            instructor=instructor,
            course_id="CS102-TEST",
            name="Course With Description",
            description="A detailed course description",
        )
        assert course.description == "A detailed course description"

    def test_create_course_inactive(self, instructor):
        """Create an inactive course."""
        course = CourseService.create_course(
            instructor=instructor,
            course_id="CS103-TEST",
            name="Inactive Course",
            is_active=False,
        )
        assert course.is_active is False

    def test_create_course_enrollment_closed(self, instructor):
        """Create a course with enrollment closed."""
        course = CourseService.create_course(
            instructor=instructor,
            course_id="CS104-TEST",
            name="Closed Course",
            enrollment_open=False,
        )
        assert course.enrollment_open is False

    def test_create_course_auto_generates_slug(self, instructor):
        """Slug should be auto-generated from course_id."""
        course = CourseService.create_course(
            instructor=instructor,
            course_id="CS-105-FALL-2024",
            name="Auto Slug Course",
        )
        assert course.slug == "cs-105-fall-2024"


@pytest.mark.django_db
class TestCourseServiceUpdateCourse:
    """Tests for CourseService.update_course()."""

    def test_update_course_name(self, course):
        """Update course name."""
        updated = CourseService.update_course(course, name="Updated Course Name")
        assert updated.name == "Updated Course Name"

    def test_update_course_description(self, course):
        """Update course description."""
        updated = CourseService.update_course(
            course, description="New description text"
        )
        assert updated.description == "New description text"

    def test_update_course_is_active(self, course):
        """Update course is_active status."""
        updated = CourseService.update_course(course, is_active=False)
        assert updated.is_active is False

    def test_update_course_enrollment_open(self, course):
        """Update course enrollment_open status."""
        updated = CourseService.update_course(course, enrollment_open=False)
        assert updated.enrollment_open is False

    def test_update_course_multiple_fields(self, course):
        """Update multiple fields at once."""
        updated = CourseService.update_course(
            course,
            name="Multi-Update Course",
            description="Multi-update description",
            is_active=False,
        )
        assert updated.name == "Multi-Update Course"
        assert updated.description == "Multi-update description"
        assert updated.is_active is False


@pytest.mark.django_db
class TestCourseServiceSoftDelete:
    """Tests for CourseService.soft_delete_course()."""

    def test_soft_delete_course_success(self, course):
        """Soft delete should set is_deleted and deactivate course."""
        course_id = course.id
        result = CourseService.soft_delete_course(course)

        assert result is True

        # Refresh from database
        deleted_course = Course.objects.get(id=course_id)
        assert deleted_course.is_deleted is True
        assert deleted_course.is_active is False
        assert deleted_course.enrollment_open is False
        assert deleted_course.deleted_at is not None

    def test_soft_delete_does_not_hard_delete(self, course):
        """Soft delete should not remove record from database."""
        course_id = course.id
        CourseService.soft_delete_course(course)

        # Course should still exist
        assert Course.objects.filter(id=course_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Course Lookup Methods
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceGetCourse:
    """Tests for course lookup methods."""

    def test_get_course_by_id_active(self, course):
        """Get active course by course_id."""
        result = CourseService.get_course_by_id(course.course_id)
        assert result.id == course.id

    def test_get_course_by_id_not_found(self):
        """Get non-existent course returns None."""
        result = CourseService.get_course_by_id("NONEXISTENT-COURSE")
        assert result is None

    def test_get_course_by_id_inactive_excluded(self, course):
        """Inactive courses excluded by default."""
        course.is_active = False
        course.save()

        result = CourseService.get_course_by_id(course.course_id)
        assert result is None

    def test_get_course_by_id_inactive_included(self, course):
        """Inactive courses included when require_active=False."""
        course.is_active = False
        course.save()

        result = CourseService.get_course_by_id(course.course_id, require_active=False)
        assert result.id == course.id

    def test_get_course_by_pk(self, course):
        """Get course by primary key."""
        result = CourseService.get_course_by_pk(course.id)
        assert result.course_id == course.course_id


# ─────────────────────────────────────────────────────────────────────────────
# Add Problem Set to Course
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceAddProblemSet:
    """Tests for CourseService.add_problem_set_to_course()."""

    def test_add_problem_set_success(self, course, problem_set):
        """Add problem set to course successfully."""
        result = CourseService.add_problem_set_to_course(
            course, problem_set.slug, is_required=True
        )
        assert result["success"] is True
        assert result["course_problem_set"] is not None
        assert result["problem_set"].slug == problem_set.slug

    def test_add_problem_set_auto_order(self, course, problem_set):
        """Auto-assign order when not specified.

        First problem set should get order 0 (0-indexed).
        """
        result = CourseService.add_problem_set_to_course(course, problem_set.slug)
        assert result["success"] is True
        assert result["course_problem_set"].order == 0

    def test_add_problem_set_auto_order_increments(self, course):
        """Auto-order increments for subsequent problem sets.

        Orders should be 0, 1, 2 (0-indexed).
        """
        from tests.factories import ProblemSetFactory

        ps1 = ProblemSetFactory(title="PS 1", slug="ps-1")
        ps2 = ProblemSetFactory(title="PS 2", slug="ps-2")
        ps3 = ProblemSetFactory(title="PS 3", slug="ps-3")

        r1 = CourseService.add_problem_set_to_course(course, ps1.slug)
        r2 = CourseService.add_problem_set_to_course(course, ps2.slug)
        r3 = CourseService.add_problem_set_to_course(course, ps3.slug)

        assert r1["course_problem_set"].order == 0
        assert r2["course_problem_set"].order == 1
        assert r3["course_problem_set"].order == 2

    def test_add_problem_set_custom_order(self, course, problem_set):
        """Add problem set with custom order."""
        result = CourseService.add_problem_set_to_course(
            course, problem_set.slug, order=10
        )
        assert result["success"] is True
        assert result["course_problem_set"].order == 10

    def test_add_problem_set_is_required_true(self, course, problem_set):
        """Add required problem set."""
        result = CourseService.add_problem_set_to_course(
            course, problem_set.slug, is_required=True
        )
        assert result["course_problem_set"].is_required is True

    def test_add_problem_set_is_required_false(self, course, problem_set):
        """Add optional problem set."""
        result = CourseService.add_problem_set_to_course(
            course, problem_set.slug, is_required=False
        )
        assert result["course_problem_set"].is_required is False

    def test_add_problem_set_duplicate_fails(self, course, problem_set):
        """Adding duplicate problem set should fail."""
        CourseService.add_problem_set_to_course(course, problem_set.slug)
        result = CourseService.add_problem_set_to_course(course, problem_set.slug)

        assert result["success"] is False
        assert "already in this course" in result["error"]

    def test_add_problem_set_not_found(self, course):
        """Adding non-existent problem set should fail."""
        result = CourseService.add_problem_set_to_course(
            course, "nonexistent-problem-set"
        )
        assert result["success"] is False
        assert "not found" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Remove Problem Set from Course
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceRemoveProblemSet:
    """Tests for CourseService.remove_problem_set_from_course()."""

    def test_remove_problem_set_success(self, course, problem_set):
        """Remove problem set from course successfully."""
        # First add it
        CourseService.add_problem_set_to_course(course, problem_set.slug)

        # Then remove it
        result = CourseService.remove_problem_set_from_course(course, problem_set.slug)
        assert result["success"] is True

        # Verify it's gone
        assert not CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).exists()

    def test_remove_problem_set_not_in_course(self, course, problem_set):
        """Removing problem set not in course should fail."""
        result = CourseService.remove_problem_set_from_course(course, problem_set.slug)
        assert result["success"] is False
        assert "not found in this course" in result["error"]

    def test_remove_problem_set_preserves_problem_set(self, course, problem_set):
        """Removing from course should not delete the problem set itself."""
        ps_id = problem_set.id
        CourseService.add_problem_set_to_course(course, problem_set.slug)
        CourseService.remove_problem_set_from_course(course, problem_set.slug)

        # Problem set should still exist
        from purplex.problems_app.models import ProblemSet

        assert ProblemSet.objects.filter(id=ps_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Update Problem Set in Course
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceUpdateProblemSet:
    """Tests for CourseService.update_course_problem_set()."""

    def test_update_problem_set_is_required(self, course, problem_set):
        """Update is_required field."""
        CourseService.add_problem_set_to_course(
            course, problem_set.slug, is_required=True
        )

        result = CourseService.update_course_problem_set(
            course, problem_set.slug, is_required=False
        )

        assert result["success"] is True
        assert result["course_problem_set"].is_required is False

    def test_update_problem_set_order(self, course, problem_set):
        """Update order field."""
        CourseService.add_problem_set_to_course(course, problem_set.slug, order=0)

        result = CourseService.update_course_problem_set(
            course, problem_set.slug, order=5
        )

        assert result["success"] is True
        assert result["course_problem_set"].order == 5

    def test_update_problem_set_due_date(self, course, problem_set):
        """Update due_date field."""
        CourseService.add_problem_set_to_course(course, problem_set.slug)
        due = timezone.now() + timedelta(days=7)

        result = CourseService.update_course_problem_set(
            course, problem_set.slug, due_date=due
        )

        assert result["success"] is True
        assert result["course_problem_set"].due_date is not None

    def test_update_problem_set_deadline_type(self, course, problem_set):
        """Update deadline_type field."""
        CourseService.add_problem_set_to_course(course, problem_set.slug)

        result = CourseService.update_course_problem_set(
            course, problem_set.slug, deadline_type="hard"
        )

        assert result["success"] is True
        assert result["course_problem_set"].deadline_type == "hard"

    def test_update_problem_set_multiple_fields(self, course, problem_set):
        """Update multiple fields at once."""
        CourseService.add_problem_set_to_course(course, problem_set.slug)
        due = timezone.now() + timedelta(days=14)

        result = CourseService.update_course_problem_set(
            course,
            problem_set.slug,
            is_required=False,
            deadline_type="soft",
            due_date=due,
        )

        assert result["success"] is True
        cps = result["course_problem_set"]
        assert cps.is_required is False
        assert cps.deadline_type == "soft"
        assert cps.due_date is not None

    def test_update_problem_set_not_in_course(self, course, problem_set):
        """Update problem set not in course should fail."""
        result = CourseService.update_course_problem_set(
            course, problem_set.slug, is_required=False
        )
        assert result["success"] is False
        assert "not found in this course" in result["error"]

    def test_update_problem_set_not_found(self, course):
        """Update non-existent problem set should fail."""
        result = CourseService.update_course_problem_set(
            course, "nonexistent-slug", is_required=False
        )
        assert result["success"] is False
        assert "not found" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Reorder Problem Sets
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceReorderProblemSets:
    """Tests for CourseService.reorder_course_problem_sets()."""

    def test_reorder_problem_sets_success(self, course):
        """Reorder problem sets in a course."""
        from tests.factories import ProblemSetFactory

        ps1 = ProblemSetFactory(title="PS 1", slug="reorder-ps-1")
        ps2 = ProblemSetFactory(title="PS 2", slug="reorder-ps-2")
        ps3 = ProblemSetFactory(title="PS 3", slug="reorder-ps-3")

        CourseService.add_problem_set_to_course(course, ps1.slug, order=0)
        CourseService.add_problem_set_to_course(course, ps2.slug, order=1)
        CourseService.add_problem_set_to_course(course, ps3.slug, order=2)

        # Reorder: swap ps1 and ps3
        ordering_data = [
            {"problem_set_id": ps1.id, "order": 2},
            {"problem_set_id": ps2.id, "order": 1},
            {"problem_set_id": ps3.id, "order": 0},
        ]

        result = CourseService.reorder_course_problem_sets(course, ordering_data)
        assert result is True

        # Verify new order
        ordered = list(course.courseproblemset_set.order_by("order"))
        assert ordered[0].problem_set.slug == "reorder-ps-3"
        assert ordered[1].problem_set.slug == "reorder-ps-2"
        assert ordered[2].problem_set.slug == "reorder-ps-1"

    def test_reorder_preserves_other_fields(self, course, problem_set):
        """Reordering should not affect other fields."""
        due = timezone.now() + timedelta(days=7)
        CourseService.add_problem_set_to_course(course, problem_set.slug, order=0)
        CourseService.update_course_problem_set(
            course,
            problem_set.slug,
            is_required=False,
            deadline_type="soft",
            due_date=due,
        )

        # Reorder
        ordering_data = [{"problem_set_id": problem_set.id, "order": 5}]
        CourseService.reorder_course_problem_sets(course, ordering_data)

        # Verify other fields unchanged
        cps = CourseProblemSet.objects.get(course=course, problem_set=problem_set)
        assert cps.order == 5
        assert cps.is_required is False
        assert cps.deadline_type == "soft"


# ─────────────────────────────────────────────────────────────────────────────
# Course Enrollment Validation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceValidateEnrollment:
    """Tests for CourseService.validate_course_enrollment()."""

    def test_validate_enrollment_success(self, course, user):
        """Enrolled user passes validation."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        result = CourseService.validate_course_enrollment(user, course.course_id)
        assert result["success"] is True
        assert result["course"].id == course.id

    def test_validate_enrollment_not_enrolled(self, course, user):
        """Non-enrolled user fails validation."""
        result = CourseService.validate_course_enrollment(user, course.course_id)
        assert result["success"] is False
        assert "not enrolled" in result["error"]
        assert result["status_code"] == 403

    def test_validate_enrollment_course_not_found(self, user):
        """Non-existent course fails validation."""
        result = CourseService.validate_course_enrollment(user, "NONEXISTENT-COURSE")
        assert result["success"] is False
        assert "not found" in result["error"]
        assert result["status_code"] == 404

    def test_validate_enrollment_inactive_enrollment(self, course, user):
        """Inactive enrollment fails validation."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=False)

        result = CourseService.validate_course_enrollment(user, course.course_id)
        assert result["success"] is False
        assert "not enrolled" in result["error"]

    def test_validate_enrollment_empty_course_id_raises(self, user):
        """Empty course_id should raise ValueError."""
        with pytest.raises(ValueError):
            CourseService.validate_course_enrollment(user, "")


@pytest.mark.django_db
class TestCourseServiceAuthorizeAccess:
    """Tests for CourseService.authorize_user_course_access()."""

    def test_authorize_access_success(self, course, user):
        """Enrolled user is authorized."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        authorized, course_obj, error = CourseService.authorize_user_course_access(
            user, course.course_id
        )
        assert authorized is True
        assert course_obj.id == course.id
        assert error is None

    def test_authorize_access_not_enrolled(self, course, user):
        """Non-enrolled user is not authorized."""
        authorized, course_obj, error = CourseService.authorize_user_course_access(
            user, course.course_id
        )
        assert authorized is False
        assert course_obj is None
        assert "not enrolled" in error

    def test_authorize_access_course_not_found(self, user):
        """Non-existent course returns not authorized."""
        authorized, course_obj, error = CourseService.authorize_user_course_access(
            user, "NONEXISTENT"
        )
        assert authorized is False
        assert course_obj is None
        assert "not found" in error


# ─────────────────────────────────────────────────────────────────────────────
# Enroll User in Course
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceEnrollUser:
    """Tests for CourseService.enroll_user_in_course()."""

    def test_enroll_user_success(self, course, user):
        """Enroll user in course successfully."""
        result = CourseService.enroll_user_in_course(user, course.course_id)

        assert result["success"] is True
        assert result["course"].id == course.id
        assert result["enrollment"] is not None
        assert result["created"] is True

    def test_enroll_user_already_enrolled(self, course, user):
        """Re-enrolling already enrolled user fails."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        result = CourseService.enroll_user_in_course(user, course.course_id)
        assert result["success"] is False
        assert "already enrolled" in result["error"]

    def test_enroll_user_reactivate_inactive(self, course, user):
        """Reactivating an inactive enrollment should succeed."""
        enrollment = CourseEnrollment.objects.create(
            user=user, course=course, is_active=False
        )

        result = CourseService.enroll_user_in_course(user, course.course_id)

        # Should succeed - reactivating an inactive enrollment
        assert result["success"] is True

        # Enrollment should be active in the database
        enrollment.refresh_from_db()
        assert enrollment.is_active is True

    def test_enroll_user_course_not_found(self, user):
        """Enrolling in non-existent course fails."""
        result = CourseService.enroll_user_in_course(user, "NONEXISTENT")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_enroll_user_enrollment_closed(self, course, user):
        """Enrolling when enrollment is closed fails."""
        course.enrollment_open = False
        course.save()

        result = CourseService.enroll_user_in_course(user, course.course_id)
        assert result["success"] is False
        assert "closed" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Lookup Course for Enrollment
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceLookupCourse:
    """Tests for CourseService.lookup_course_for_enrollment()."""

    def test_lookup_course_success(self, course, user):
        """Lookup active course with open enrollment."""
        result = CourseService.lookup_course_for_enrollment(course.course_id, user)

        assert result["success"] is True
        assert result["course"].id == course.id
        assert result["already_enrolled"] is False

    def test_lookup_course_already_enrolled(self, course, user):
        """Lookup shows already_enrolled flag."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        result = CourseService.lookup_course_for_enrollment(course.course_id, user)

        assert result["success"] is True
        assert result["already_enrolled"] is True

    def test_lookup_course_not_found(self, user):
        """Lookup non-existent course fails."""
        result = CourseService.lookup_course_for_enrollment("NONEXISTENT", user)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_lookup_course_enrollment_closed(self, course, user):
        """Lookup course with closed enrollment fails."""
        course.enrollment_open = False
        course.save()

        result = CourseService.lookup_course_for_enrollment(course.course_id, user)
        assert result["success"] is False
        assert "closed" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Check User Enrollment
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceIsUserEnrolled:
    """Tests for CourseService.is_user_enrolled()."""

    def test_is_user_enrolled_true(self, course, user):
        """Enrolled user returns True."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        result = CourseService.is_user_enrolled(user, course.course_id)
        assert result is True

    def test_is_user_enrolled_false(self, course, user):
        """Non-enrolled user returns False."""
        result = CourseService.is_user_enrolled(user, course.course_id)
        assert result is False

    def test_is_user_enrolled_inactive(self, course, user):
        """Inactive enrollment returns False."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=False)

        result = CourseService.is_user_enrolled(user, course.course_id)
        assert result is False

    def test_is_user_enrolled_course_not_found(self, user):
        """Non-existent course returns False."""
        result = CourseService.is_user_enrolled(user, "NONEXISTENT")
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Get User Courses
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseServiceGetUserCourses:
    """Tests for CourseService.get_user_courses()."""

    def test_get_user_courses_enrolled(self, user, course):
        """Get courses user is enrolled in."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=True)

        result = CourseService.get_user_courses(user)

        assert len(result) >= 1
        course_ids = [c["course"]["course_id"] for c in result]
        assert course.course_id in course_ids

    def test_get_user_courses_no_enrollments(self, user):
        """User with no enrollments returns empty list."""
        result = CourseService.get_user_courses(user)
        assert result == []

    def test_get_user_courses_excludes_inactive(self, user, course):
        """Inactive enrollments are excluded."""
        CourseEnrollment.objects.create(user=user, course=course, is_active=False)

        result = CourseService.get_user_courses(user)
        course_ids = [c["course"]["course_id"] for c in result]
        assert course.course_id not in course_ids
