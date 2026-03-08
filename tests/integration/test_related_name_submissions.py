"""
Tests for Submission related_name cleanup (Change 7, P2).

The Submission model's FKs all use related_name="new_submissions" (a migration
artifact). After cleanup, they should use related_name="submissions".

- Filter-based access is unaffected by related_name (regression, always passes)
- Reverse-relation accessor tests are xfail before rename, pass after
"""

import pytest

from purplex.submissions.models import Submission
from tests.factories import (
    CourseFactory,
    CourseInstructorFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    SubmissionFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestRelatedNameSubmissions:
    def test_filter_based_access_unaffected(self):
        """Regression: Submission.objects.filter(user=...) works regardless of related_name."""
        user = UserFactory()
        sub = SubmissionFactory(user=user)
        result = Submission.objects.filter(user=user)
        assert sub in result

    def test_problem_reverse_relation(self):
        """Post-fix: problem.submissions should return related submissions."""
        problem = EiplProblemFactory()
        sub = SubmissionFactory(problem=problem)
        assert sub in problem.submissions.all()

    def test_user_reverse_relation(self):
        """Post-fix: user.submissions should return related submissions."""
        user = UserFactory()
        sub = SubmissionFactory(user=user)
        assert sub in user.submissions.all()

    def test_problem_set_reverse_relation(self):
        """Post-fix: problem_set.submissions should return related submissions."""
        ps = ProblemSetFactory()
        sub = SubmissionFactory(problem_set=ps)
        assert sub in ps.submissions.all()

    def test_course_reverse_relation(self):
        """Post-fix: course.submissions should return related submissions."""
        course = CourseFactory()
        CourseInstructorFactory(course=course, user=UserFactory(), role="primary")
        sub = SubmissionFactory(course=course)
        assert sub in course.submissions.all()
