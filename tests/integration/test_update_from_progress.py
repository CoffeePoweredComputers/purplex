"""
Regression tests for UserProblemSetProgress.update_from_progress().

This is the most complex model method in the system — it aggregates
across UserProgress records using Count/Avg/Min/Max, does update_or_create,
and tracks completed_at. A data model refactor (especially Change 1's
field renames) could easily break it.

Critically, this method already uses the CORRECT field name (best_score),
so it must survive the fix unchanged. These tests lock that down.
"""

import pytest

from purplex.problems_app.models import UserProblemSetProgress, UserProgress
from tests.factories import (
    CourseFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestUpdateFromProgress:
    """Tests for UserProblemSetProgress.update_from_progress()."""

    def _make_problem_set_with_problems(self, n=3):
        """Helper: create a problem_set with n problems linked via membership."""
        ps = ProblemSetFactory()
        problems = []
        for i in range(n):
            p = EiplProblemFactory()
            ProblemSetMembershipFactory(problem_set=ps, problem=p, order=i)
            problems.append(p)
        return ps, problems

    def test_basic_aggregation(self):
        """Single UserProgress record → correct rollup."""
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(3)

        progress = UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            best_score=80,
            status="in_progress",
            attempts=2,
        )

        UserProblemSetProgress.update_from_progress(progress)

        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        assert psp.total_problems == 3
        assert psp.completed_problems == 0
        assert psp.in_progress_problems == 1
        assert psp.average_score == 80.0
        assert psp.completion_percentage == 0
        assert psp.is_completed is False

    def test_multiple_progress_records(self):
        """Multiple UserProgress records → correct aggregation across all."""
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(3)

        p1 = UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            best_score=100,
            status="completed",
            is_completed=True,
        )
        UserProgressFactory(
            user=user,
            problem=problems[1],
            problem_set=ps,
            best_score=60,
            status="in_progress",
        )
        UserProgressFactory(
            user=user,
            problem=problems[2],
            problem_set=ps,
            best_score=0,
            status="not_started",
        )

        UserProblemSetProgress.update_from_progress(p1)

        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        assert psp.total_problems == 3
        assert psp.completed_problems == 1
        assert psp.in_progress_problems == 1
        # avg of best_score across all 3: (100 + 60 + 0) / 3
        assert abs(psp.average_score - 53.33) < 0.5
        assert psp.completion_percentage == 33  # 1/3

    def test_completed_at_set_on_first_completion(self):
        """completed_at is set when all problems are completed for the first time."""
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(2)

        UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            best_score=100,
            status="completed",
            is_completed=True,
        )
        p2 = UserProgressFactory(
            user=user,
            problem=problems[1],
            problem_set=ps,
            best_score=90,
            status="completed",
            is_completed=True,
        )

        UserProblemSetProgress.update_from_progress(p2)

        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        assert psp.is_completed is True
        assert psp.completed_at is not None

    def test_completed_at_preserved_on_subsequent_updates(self):
        """completed_at is NOT overwritten by later update_from_progress calls."""
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(1)

        progress = UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            best_score=100,
            status="completed",
            is_completed=True,
        )

        UserProblemSetProgress.update_from_progress(progress)
        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        original_completed_at = psp.completed_at
        assert original_completed_at is not None

        # Update again — completed_at must not change
        progress.best_score = 95
        progress.save()
        UserProblemSetProgress.update_from_progress(progress)

        psp.refresh_from_db()
        assert psp.completed_at == original_completed_at

    def test_uses_best_score_not_score(self):
        """Regression guard: aggregation uses best_score (not score).

        The repository bugs (Change 1) reference 'score' which doesn't exist.
        update_from_progress correctly uses 'best_score' via Avg("best_score").
        This test ensures a field rename refactor doesn't break this method.
        """
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(2)

        UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            best_score=100,
            average_score=50.0,
        )
        UserProgressFactory(
            user=user,
            problem=problems[1],
            problem_set=ps,
            best_score=80,
            average_score=40.0,
        )

        p = UserProgress.objects.filter(user=user, problem_set=ps).first()
        UserProblemSetProgress.update_from_progress(p)

        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        # avg of best_score: (100 + 80) / 2 = 90, NOT avg of average_score
        assert psp.average_score == 90.0

    def test_zero_problems_edge_case(self):
        """Problem set with no problems → 0% completion, not completed."""
        user = UserFactory()
        ps = ProblemSetFactory()  # No problems added

        # Create a UserProgress that references this empty problem set
        # (shouldn't happen in practice, but guards against division by zero)
        problem = EiplProblemFactory()
        progress = UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=ps,
            best_score=100,
            status="completed",
            is_completed=True,
        )

        UserProblemSetProgress.update_from_progress(progress)

        psp = UserProblemSetProgress.objects.get(user=user, problem_set=ps)
        assert psp.completion_percentage == 0
        assert psp.is_completed is False

    def test_course_context_isolation(self):
        """Progress in different courses doesn't cross-contaminate."""
        user = UserFactory()
        ps, problems = self._make_problem_set_with_problems(2)
        course_a = CourseFactory()
        course_b = CourseFactory()

        # Complete problem 0 in course A
        p_a = UserProgressFactory(
            user=user,
            problem=problems[0],
            problem_set=ps,
            course=course_a,
            best_score=100,
            status="completed",
            is_completed=True,
        )
        # Complete problem 1 in course B
        UserProgressFactory(
            user=user,
            problem=problems[1],
            problem_set=ps,
            course=course_b,
            best_score=90,
            status="completed",
            is_completed=True,
        )

        UserProblemSetProgress.update_from_progress(p_a)

        psp_a = UserProblemSetProgress.objects.get(
            user=user, problem_set=ps, course=course_a
        )
        # Only 1 problem completed in course A context (out of 2 total)
        assert psp_a.completed_problems == 1
        assert psp_a.completion_percentage == 50
        assert psp_a.is_completed is False
