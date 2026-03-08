"""
Tests for Course soft-delete manager (Change 4, P2).

Mixed: the soft_delete() method already exists (regression),
but the custom default manager that filters is_deleted=False
does not exist yet (xfail / post-fix).
"""

import pytest

from purplex.problems_app.models import Course
from tests.factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    CourseInstructorFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestCourseSoftDeleteManager:
    """Tests for ActiveCourseManager as default objects manager."""

    def test_soft_delete_method_works(self):
        """Regression: soft_delete() sets is_deleted=True and is_active=False."""
        course = CourseFactory()
        CourseInstructorFactory(course=course, user=UserFactory(), role="primary")
        course.soft_delete()
        course.refresh_from_db()
        assert course.is_deleted is True
        assert course.is_active is False
        assert course.enrollment_open is False
        assert course.deleted_at is not None

    def test_default_manager_excludes_soft_deleted(self):
        """Post-fix: Course.objects should hide soft-deleted courses."""
        active = CourseFactory()
        CourseInstructorFactory(course=active, user=UserFactory(), role="primary")
        deleted = CourseFactory()
        CourseInstructorFactory(course=deleted, user=UserFactory(), role="primary")
        deleted.soft_delete()

        # Default manager should only return active courses
        courses = Course.objects.all()
        course_ids = [c.id for c in courses]
        assert active.id in course_ids
        assert deleted.id not in course_ids

    def test_all_objects_includes_soft_deleted(self):
        """Post-fix: Course.all_objects should include soft-deleted courses."""
        active = CourseFactory()
        CourseInstructorFactory(course=active, user=UserFactory(), role="primary")
        deleted = CourseFactory()
        CourseInstructorFactory(course=deleted, user=UserFactory(), role="primary")
        deleted.soft_delete()

        courses = Course.all_objects.all()
        course_ids = [c.id for c in courses]
        assert active.id in course_ids
        assert deleted.id in course_ids

    def test_filter_still_works_with_manager(self):
        """Post-fix: .filter() on default manager auto-excludes soft-deleted.

        Without the custom manager, Course.objects.filter(name__icontains=...)
        includes soft-deleted courses. After fix, it should auto-exclude them.
        """
        active = CourseFactory(name="Filterable Course A")
        CourseInstructorFactory(course=active, user=UserFactory(), role="primary")
        deleted = CourseFactory(name="Filterable Course B")
        CourseInstructorFactory(course=deleted, user=UserFactory(), role="primary")
        deleted.soft_delete()

        # Without custom manager, both appear when filtering by name
        results = Course.objects.filter(name__icontains="Filterable Course")
        course_ids = [c.id for c in results]
        assert active.id in course_ids
        assert deleted.id not in course_ids  # Should be excluded by manager

    def test_soft_deleted_excluded_from_enrollment_query(self):
        """Post-fix: enrollment queries through Course.objects exclude soft-deleted."""
        user = UserFactory()
        active_course = CourseFactory()
        CourseInstructorFactory(
            course=active_course, user=UserFactory(), role="primary"
        )
        deleted_course = CourseFactory()
        CourseInstructorFactory(
            course=deleted_course, user=UserFactory(), role="primary"
        )
        CourseEnrollmentFactory(user=user, course=active_course)
        CourseEnrollmentFactory(user=user, course=deleted_course)
        deleted_course.soft_delete()

        # Query via default manager should exclude soft-deleted
        visible_courses = Course.objects.filter(enrollments__user=user)
        assert active_course in visible_courses
        assert deleted_course not in visible_courses
