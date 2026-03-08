"""
Tests for TestCase order uniqueness constraint (Change 5, P2).

The current unique_together = ["problem", "order"] makes reordering painful.
After the fix, only ordering = ["order", "id"] remains (no uniqueness on order).
"""

import pytest

from purplex.problems_app.models import TestCase
from tests.factories import EiplProblemFactory, TestCaseFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestTestCaseOrderConstraint:
    def test_same_order_different_problems_allowed(self):
        """Regression: same order on different problems is always fine."""
        p1 = EiplProblemFactory()
        p2 = EiplProblemFactory()
        tc1 = TestCaseFactory(problem=p1, order=0)
        tc2 = TestCaseFactory(problem=p2, order=0)
        assert tc1.order == tc2.order == 0

    def test_same_order_same_problem_allowed(self):
        """Post-fix: after removing constraint, same order on same problem is OK."""
        problem = EiplProblemFactory()
        TestCaseFactory(problem=problem, order=0, inputs=[1], expected_output=1)
        # This currently raises IntegrityError due to unique_together
        TestCaseFactory(problem=problem, order=0, inputs=[2], expected_output=2)

    def test_ordering_by_order_then_id(self):
        """Regression: default ordering is ['order', 'id']."""
        problem = EiplProblemFactory()
        tc2 = TestCaseFactory(problem=problem, order=2, inputs=[2], expected_output=4)
        tc1 = TestCaseFactory(problem=problem, order=1, inputs=[1], expected_output=2)
        tc3 = TestCaseFactory(problem=problem, order=3, inputs=[3], expected_output=6)

        ordered = list(TestCase.objects.filter(problem=problem))
        assert ordered == [tc1, tc2, tc3]
