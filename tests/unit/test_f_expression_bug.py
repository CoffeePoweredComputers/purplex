"""
Regression tests for UserProblemSetProgress.update_from_progress().

Previously, F("completed_at") in the defaults dict of update_or_create() caused:
  Bug 1: ValueError on every first-time rollup (INSERT path).
  Bug 2: In-memory F() object was truthy, making completed_at assignment dead code.

Fixed by removing F("completed_at") from defaults (omitted fields are preserved
on UPDATE automatically) and dropping the `not created` guard so completed_at
is set on both INSERT and UPDATE paths.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from purplex.problems_app.models.progress import UserProblemSetProgress
from tests.factories import (
    CourseFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestInsertPath:
    """Tests for first-time rollup (no pre-existing UserProblemSetProgress row)."""

    @pytest.fixture
    def rollup_setup(self, db):
        """Single-problem set with one in-progress UserProgress row.

        No UserProblemSetProgress row exists — forces the INSERT path.
        """
        user = UserFactory()
        problem_set = ProblemSetFactory()
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        return UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=None,
            status="in_progress",
            is_completed=False,
        )

    def test_first_rollup_creates_row(self, rollup_setup):
        """First-time rollup creates a UserProblemSetProgress row."""
        up = rollup_setup
        UserProblemSetProgress.update_from_progress(up)

        row = UserProblemSetProgress.objects.get(
            user=up.user, problem_set=up.problem_set, course=up.course
        )
        assert row.total_problems == 1
        assert row.completed_problems == 0
        assert row.in_progress_problems == 1
        assert row.completion_percentage == 0
        assert row.is_completed is False
        assert row.completed_at is None

    def test_first_rollup_with_completed_problem(self, rollup_setup):
        """First-time rollup with all problems completed sets completed_at."""
        up = rollup_setup
        up.is_completed = True
        up.status = "completed"
        up.save()

        UserProblemSetProgress.update_from_progress(up)

        row = UserProblemSetProgress.objects.get(
            user=up.user, problem_set=up.problem_set, course=up.course
        )
        assert row.total_problems == 1
        assert row.completed_problems == 1
        assert row.is_completed is True
        assert row.completed_at is not None

    def test_first_rollup_with_real_course(self, db):
        """First-time rollup with a non-null course (the production-common path)."""
        user = UserFactory()
        course = CourseFactory()
        problem_set = ProblemSetFactory()
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        user_progress = UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            status="in_progress",
            is_completed=False,
        )

        UserProblemSetProgress.update_from_progress(user_progress)

        row = UserProblemSetProgress.objects.get(
            user=user, problem_set=problem_set, course=course
        )
        assert row.total_problems == 1
        assert row.completed_problems == 0
        assert row.in_progress_problems == 1


class TestUpdatePath:
    """Tests for subsequent rollups (UserProblemSetProgress row already exists)."""

    @pytest.fixture
    def rollup_setup(self, db):
        """Single-problem set with one in-progress UserProgress row
        and a pre-existing UserProblemSetProgress row (UPDATE path).
        """
        user = UserFactory()
        problem_set = ProblemSetFactory()
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        user_progress = UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=None,
            status="in_progress",
            is_completed=False,
        )

        UserProblemSetProgress.objects.create(
            user=user,
            problem_set=problem_set,
            course=None,
        )

        return user_progress

    def test_update_aggregates_correctly(self, rollup_setup):
        """UPDATE path recalculates aggregation fields from UserProgress."""
        up = rollup_setup
        UserProblemSetProgress.update_from_progress(up)

        row = UserProblemSetProgress.objects.get(
            user=up.user, problem_set=up.problem_set, course=up.course
        )
        assert row.total_problems == 1
        assert row.completed_problems == 0
        assert row.in_progress_problems == 1
        assert row.completion_percentage == 0
        assert row.is_completed is False

    def test_update_preserves_existing_completed_at(self, rollup_setup):
        """UPDATE preserves an existing completed_at timestamp."""
        up = rollup_setup
        original_ts = timezone.now() - timedelta(days=7)

        UserProblemSetProgress.objects.filter(
            user=up.user, problem_set=up.problem_set, course=up.course
        ).update(completed_at=original_ts)

        UserProblemSetProgress.update_from_progress(up)

        row = UserProblemSetProgress.objects.get(
            user=up.user, problem_set=up.problem_set, course=up.course
        )
        assert row.completed_at == original_ts

    def test_completed_at_set_on_completion(self, rollup_setup):
        """When all problems complete on UPDATE, completed_at is set."""
        up = rollup_setup
        up.is_completed = True
        up.status = "completed"
        up.save()

        UserProblemSetProgress.update_from_progress(up)

        row = UserProblemSetProgress.objects.get(
            user=up.user, problem_set=up.problem_set, course=up.course
        )
        assert row.completed_at is not None

    def test_partial_completion_aggregation(self, db):
        """Aggregation math with multiple problems (2 of 3 completed)."""
        user = UserFactory()
        problem_set = ProblemSetFactory()
        problems = [EiplProblemFactory() for _ in range(3)]
        for p in problems:
            ProblemSetMembershipFactory(problem_set=problem_set, problem=p)

        UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=problem_set,
            course=None,
            status="completed",
            is_completed=True,
            best_score=90,
        )
        UserProgressFactory(
            user=user,
            problem=problems[1],
            problem_set=problem_set,
            course=None,
            status="completed",
            is_completed=True,
            best_score=80,
        )
        up_in_progress = UserProgressFactory(
            user=user,
            problem=problems[2],
            problem_set=problem_set,
            course=None,
            status="in_progress",
            is_completed=False,
            best_score=0,
        )

        UserProblemSetProgress.objects.create(
            user=user,
            problem_set=problem_set,
            course=None,
        )

        UserProblemSetProgress.update_from_progress(up_in_progress)

        row = UserProblemSetProgress.objects.get(
            user=user,
            problem_set=problem_set,
            course=None,
        )
        assert row.total_problems == 3
        assert row.completed_problems == 2
        assert row.in_progress_problems == 1
        assert row.completion_percentage == 66  # int(2/3 * 100) = 66
        assert row.is_completed is False
        # average_score across 3 UserProgress rows: (90 + 80 + 0) / 3
        assert abs(row.average_score - 56.67) < 0.01
