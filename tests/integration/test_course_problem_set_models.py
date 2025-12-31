"""
Tests for CourseProblemSet model and deadline enforcement.

Tests:
- Field defaults and validation
- Deadline type behavior
- Due date handling
- Ordering constraints
- Unique constraints
"""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from purplex.problems_app.models import Course, CourseProblemSet, ProblemSet

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet Field Defaults
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetFieldDefaults:
    """Tests for CourseProblemSet field defaults."""

    def test_order_defaults_to_zero(self, course, problem_set):
        """Default order should be 0."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.order == 0

    def test_is_required_defaults_to_true(self, course, problem_set):
        """Default is_required should be True."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.is_required is True

    def test_due_date_defaults_to_null(self, course, problem_set):
        """Default due_date should be None."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.due_date is None

    def test_deadline_type_defaults_to_none(self, course, problem_set):
        """Default deadline_type should be 'none'."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.deadline_type == "none"

    def test_problem_set_version_defaults_to_one(self, course, problem_set):
        """Default problem_set_version should be 1."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.problem_set_version == 1

    def test_added_at_auto_populated(self, course, problem_set):
        """added_at should be auto-populated on creation."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
        )
        assert cps.added_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet Deadline Types
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetDeadlineTypes:
    """Tests for CourseProblemSet deadline_type choices."""

    @pytest.mark.parametrize("deadline_type", ["none", "soft", "hard"])
    def test_valid_deadline_types(self, course, problem_set, deadline_type):
        """Valid deadline types should be accepted."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            deadline_type=deadline_type,
        )
        cps.full_clean()  # Should not raise
        assert cps.deadline_type == deadline_type

    def test_soft_deadline_with_due_date(self, course, problem_set):
        """Soft deadline with due_date should be valid."""
        due = timezone.now() + timedelta(days=7)
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            deadline_type="soft",
            due_date=due,
        )
        assert cps.deadline_type == "soft"
        assert cps.due_date is not None

    def test_hard_deadline_with_due_date(self, course, problem_set):
        """Hard deadline with due_date should be valid."""
        due = timezone.now() + timedelta(days=14)
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            deadline_type="hard",
            due_date=due,
        )
        assert cps.deadline_type == "hard"
        assert cps.due_date is not None

    def test_deadline_without_due_date_allowed(self, course, problem_set):
        """Deadline type can be set without a due_date (might be a bug)."""
        # This tests if setting a deadline type without a due_date is allowed
        # If it should require a due_date, this test will reveal that gap
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            deadline_type="hard",
            due_date=None,  # No due_date with hard deadline
        )
        cps.full_clean()  # Check if validation catches this
        # If we get here, hard deadline without due_date is allowed
        assert cps.deadline_type == "hard"
        assert cps.due_date is None

    def test_past_due_date_allowed(self, course, problem_set):
        """Past due dates should be allowed (for historical data)."""
        past_date = timezone.now() - timedelta(days=30)
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            deadline_type="soft",
            due_date=past_date,
        )
        cps.full_clean()  # Should not raise
        assert cps.due_date < timezone.now()


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet Unique Constraints
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetConstraints:
    """Tests for CourseProblemSet constraints."""

    def test_unique_course_problem_set(self, course, problem_set):
        """Same problem set cannot be in same course twice."""
        CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            order=0,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CourseProblemSet.objects.create(
                    course=course,
                    problem_set=problem_set,
                    order=1,
                )

    def test_same_problem_set_different_courses_allowed(self, instructor):
        """Same problem set can be in different courses."""
        problem_set = ProblemSet.objects.create(title="Shared PS")
        course1 = Course.objects.create(
            course_id="COURSE-1",
            name="Course 1",
            instructor=instructor,
        )
        course2 = Course.objects.create(
            course_id="COURSE-2",
            name="Course 2",
            instructor=instructor,
        )

        CourseProblemSet.objects.create(
            course=course1,
            problem_set=problem_set,
            order=0,
        )
        # Should not raise
        cps2 = CourseProblemSet.objects.create(
            course=course2,
            problem_set=problem_set,
            order=0,
        )
        assert cps2.id is not None

    def test_different_problem_sets_same_course_allowed(self, course):
        """Different problem sets can be in same course."""
        ps1 = ProblemSet.objects.create(title="PS 1")
        ps2 = ProblemSet.objects.create(title="PS 2")

        CourseProblemSet.objects.create(course=course, problem_set=ps1, order=0)
        cps2 = CourseProblemSet.objects.create(course=course, problem_set=ps2, order=1)
        assert cps2.id is not None


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet Ordering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetOrdering:
    """Tests for CourseProblemSet ordering behavior."""

    def test_default_ordering_by_order_field(self, course):
        """Problem sets should be ordered by 'order' field."""
        ps1 = ProblemSet.objects.create(title="PS 1")
        ps2 = ProblemSet.objects.create(title="PS 2")
        ps3 = ProblemSet.objects.create(title="PS 3")

        # Create in random order
        CourseProblemSet.objects.create(course=course, problem_set=ps2, order=1)
        CourseProblemSet.objects.create(course=course, problem_set=ps3, order=2)
        CourseProblemSet.objects.create(course=course, problem_set=ps1, order=0)

        ordered = list(course.courseproblemset_set.all())
        assert ordered[0].problem_set.title == "PS 1"
        assert ordered[1].problem_set.title == "PS 2"
        assert ordered[2].problem_set.title == "PS 3"

    def test_reorder_problem_sets(self, course):
        """Problem sets can be reordered."""
        ps1 = ProblemSet.objects.create(title="PS 1")
        ps2 = ProblemSet.objects.create(title="PS 2")

        cps1 = CourseProblemSet.objects.create(course=course, problem_set=ps1, order=0)
        cps2 = CourseProblemSet.objects.create(course=course, problem_set=ps2, order=1)

        # Swap order
        cps1.order = 1
        cps1.save()
        cps2.order = 0
        cps2.save()

        ordered = list(course.courseproblemset_set.all())
        assert ordered[0].problem_set.title == "PS 2"
        assert ordered[1].problem_set.title == "PS 1"

    def test_non_contiguous_order_allowed(self, course):
        """Non-contiguous order values should be allowed."""
        ps1 = ProblemSet.objects.create(title="PS 1")
        ps2 = ProblemSet.objects.create(title="PS 2")

        CourseProblemSet.objects.create(course=course, problem_set=ps1, order=0)
        CourseProblemSet.objects.create(course=course, problem_set=ps2, order=10)

        ordered = list(course.courseproblemset_set.all())
        assert ordered[0].order == 0
        assert ordered[1].order == 10

    def test_duplicate_order_allowed(self, course):
        """Duplicate order values should be allowed (no unique constraint on order)."""
        ps1 = ProblemSet.objects.create(title="PS 1")
        ps2 = ProblemSet.objects.create(title="PS 2")

        CourseProblemSet.objects.create(course=course, problem_set=ps1, order=0)
        cps2 = CourseProblemSet.objects.create(course=course, problem_set=ps2, order=0)
        assert cps2.id is not None  # No error - duplicate order allowed


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet is_required Flag
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetIsRequired:
    """Tests for CourseProblemSet is_required field."""

    def test_is_required_true(self, course, problem_set):
        """is_required=True should be stored correctly."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            is_required=True,
        )
        cps.refresh_from_db()
        assert cps.is_required is True

    def test_is_required_false(self, course, problem_set):
        """is_required=False should be stored correctly."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            is_required=False,
        )
        cps.refresh_from_db()
        assert cps.is_required is False

    def test_filter_by_is_required(self, course):
        """Should be able to filter by is_required."""
        ps1 = ProblemSet.objects.create(title="Required PS")
        ps2 = ProblemSet.objects.create(title="Optional PS")

        CourseProblemSet.objects.create(
            course=course, problem_set=ps1, is_required=True
        )
        CourseProblemSet.objects.create(
            course=course, problem_set=ps2, is_required=False
        )

        required = course.courseproblemset_set.filter(is_required=True)
        optional = course.courseproblemset_set.filter(is_required=False)

        assert required.count() == 1
        assert optional.count() == 1
        assert required.first().problem_set.title == "Required PS"
        assert optional.first().problem_set.title == "Optional PS"


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet String Representation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetStr:
    """Tests for CourseProblemSet.__str__()."""

    def test_str_format(self, course, problem_set):
        """__str__ should include course_id, problem_set title, and order."""
        cps = CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            order=5,
        )
        result = str(cps)
        assert course.course_id in result
        assert problem_set.title in result
        assert "5" in result


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet Cascade Deletion
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetCascade:
    """Tests for CourseProblemSet cascade deletion behavior."""

    def test_deleting_course_deletes_course_problem_set(self, instructor):
        """Deleting a course should cascade delete CourseProblemSet entries."""
        course = Course.objects.create(
            course_id="DELETE-TEST",
            name="Delete Test Course",
            instructor=instructor,
        )
        ps = ProblemSet.objects.create(title="Test PS")
        cps = CourseProblemSet.objects.create(course=course, problem_set=ps)
        cps_id = cps.id

        course.delete()

        assert not CourseProblemSet.objects.filter(id=cps_id).exists()

    def test_deleting_problem_set_deletes_course_problem_set(self, course):
        """Deleting a problem set should cascade delete CourseProblemSet entries."""
        ps = ProblemSet.objects.create(title="Delete PS")
        cps = CourseProblemSet.objects.create(course=course, problem_set=ps)
        cps_id = cps.id

        ps.delete()

        assert not CourseProblemSet.objects.filter(id=cps_id).exists()

    def test_problem_set_still_exists_after_cps_deleted(self, course, problem_set):
        """Deleting CourseProblemSet should NOT delete the ProblemSet."""
        ps_id = problem_set.id
        cps = CourseProblemSet.objects.create(course=course, problem_set=problem_set)

        cps.delete()

        assert ProblemSet.objects.filter(id=ps_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# CourseProblemSet with Course fixture
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseProblemSetWithCourseFixture:
    """Tests using the course_with_due_dates fixture."""

    def test_course_with_due_dates_has_three_problem_sets(self, course_with_due_dates):
        """course_with_due_dates fixture should have 3 problem sets."""
        cps_list = list(course_with_due_dates.courseproblemset_set.all())
        assert len(cps_list) == 3

    def test_course_with_due_dates_has_correct_deadline_types(
        self, course_with_due_dates
    ):
        """course_with_due_dates fixture should have none, soft, hard deadline types."""
        cps_list = list(
            course_with_due_dates.courseproblemset_set.order_by("order").all()
        )
        assert cps_list[0].deadline_type == "none"
        assert cps_list[1].deadline_type == "soft"
        assert cps_list[2].deadline_type == "hard"

    def test_soft_and_hard_have_due_dates(self, course_with_due_dates):
        """Soft and hard deadline types should have due_dates set."""
        cps_list = list(
            course_with_due_dates.courseproblemset_set.order_by("order").all()
        )
        assert cps_list[0].due_date is None  # none
        assert cps_list[1].due_date is not None  # soft
        assert cps_list[2].due_date is not None  # hard
