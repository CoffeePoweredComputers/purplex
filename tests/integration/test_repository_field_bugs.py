"""
Bug-proving tests for repository field-name bugs (Change 1, P0).

Every test here calls a repository method that references a wrong field name.
These are xfail before fix (the methods raise FieldError/AttributeError/TypeError)
and should pass after the field names are corrected.
"""

import pytest

from purplex.problems_app.repositories.problem_set_repository import (
    ProblemSetRepository,
)
from purplex.problems_app.repositories.progress_repository import ProgressRepository
from tests.factories import (
    CourseFactory,
    CourseInstructorFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProblemSetProgressFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# ProblemSetRepository bugs
# ─────────────────────────────────────────────────────────────────────────────


class TestProblemSetRepositoryFieldBugs:
    """Bug-proving tests for ProblemSetRepository field-name mismatches.

    The ProblemSet model uses ``is_public`` but the repository references
    ``is_published`` in filters, attribute access, and create() calls.
    """

    def test_get_active_problem_sets(self):
        ProblemSetFactory(is_public=True)
        result = ProblemSetRepository.get_active_problem_sets()
        assert len(result) >= 1

    def test_get_all_public_problem_sets(self):
        ProblemSetFactory(is_public=True)
        result = ProblemSetRepository.get_all_public_problem_sets()
        assert len(result) >= 1

    def test_search_problem_sets(self):
        ProblemSetFactory(title="Searchable Set", is_public=True)
        result = ProblemSetRepository.search_problem_sets("Searchable")
        assert len(result) >= 1

    def test_get_problems_in_set_ordered(self):
        ps = ProblemSetFactory()
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
        result = ProblemSetRepository.get_problems_in_set_ordered(ps)
        assert len(result) == 1

    def test_clone_problem_set(self):
        user = UserFactory()
        ps = ProblemSetFactory()
        problem = EiplProblemFactory()
        ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
        result = ProblemSetRepository.clone_problem_set(
            ps, user, "Cloned Set", "cloned-set"
        )
        assert result.title == "Cloned Set"

    def test_publish_problem_set(self):
        ps = ProblemSetFactory(is_public=False)
        ProblemSetRepository.publish_problem_set(ps)
        ps.refresh_from_db()
        assert ps.is_public is True

    def test_unpublish_problem_set(self):
        ps = ProblemSetFactory(is_public=True)
        ProblemSetRepository.unpublish_problem_set(ps)
        ps.refresh_from_db()
        assert ps.is_public is False


# ─────────────────────────────────────────────────────────────────────────────
# ProgressRepository bugs
# ─────────────────────────────────────────────────────────────────────────────


class TestProgressRepositoryFieldBugs:
    """Bug-proving tests for ProgressRepository field-name mismatches.

    UserProgress uses ``best_score`` and ``last_attempt``;
    UserProblemSetProgress uses ``last_activity``.
    The repository references ``score``, ``last_submission_at``, and ``last_updated``.
    """

    def test_get_user_problem_set_progresses(self):
        user = UserFactory()
        UserProblemSetProgressFactory(user=user)
        result = ProgressRepository.get_user_problem_set_progresses(user)
        assert len(result) >= 1

    def test_get_course_progress_summary(self):
        user = UserFactory()
        course = CourseFactory()
        CourseInstructorFactory(course=course, user=UserFactory(), role="primary")
        problem = EiplProblemFactory()
        ps = ProblemSetFactory()
        UserProgressFactory(
            user=user, problem=problem, problem_set=ps, course=course, best_score=80
        )
        result = ProgressRepository.get_course_progress_summary(user, course)
        assert "avg_score" in result

    def test_get_problem_statistics(self):
        problem = EiplProblemFactory()
        user = UserFactory()
        ps = ProblemSetFactory()
        UserProgressFactory(user=user, problem=problem, problem_set=ps, best_score=90)
        result = ProgressRepository.get_problem_statistics(problem)
        assert "avg_score" in result

    def test_get_user_statistics(self):
        user = UserFactory()
        problem = EiplProblemFactory()
        ps = ProblemSetFactory()
        UserProgressFactory(user=user, problem=problem, problem_set=ps, best_score=75)
        result = ProgressRepository.get_user_statistics(user)
        assert "avg_score" in result

    def test_get_user_course_progress_by_id(self):
        user = UserFactory()
        course = CourseFactory()
        CourseInstructorFactory(course=course, user=UserFactory(), role="primary")
        problem = EiplProblemFactory()
        ps = ProblemSetFactory()
        UserProgressFactory(user=user, problem=problem, problem_set=ps, course=course)
        result = ProgressRepository.get_user_course_progress_by_id(user.id, course.id)
        assert len(result) >= 1
