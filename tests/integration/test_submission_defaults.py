"""
Regression tests for Submission model database defaults.

Bug Prevention:
- Bug 3: is_late field had Python-level default=False but no db_default,
  causing NOT NULL constraint violation when is_late wasn't explicitly set
  or when None was passed explicitly.

The fix added db_default=False to ensure database-level defaults work
even when the field is not explicitly set at Python level.

These tests verify:
1. ORM-level default works (omitting is_late)
2. Explicit True/False values are respected
3. Database-level default works via raw SQL
"""

import pytest
from django.db import connection

from purplex.submissions.models import Submission
from tests.factories import (
    EiplProblemFactory,
    ProblemSetFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


@pytest.mark.django_db
class TestSubmissionIsLateDefault:
    """
    Regression tests for Bug 3: is_late NOT NULL violation.

    The fix added db_default=False to the is_late field to ensure
    database-level defaults work correctly.
    """

    def test_submission_without_is_late_uses_default(self):
        """
        Creating submission without is_late should use Python default (False).

        This tests the ORM-level default behavior.
        """
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        # Create submission without explicitly setting is_late
        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type="eipl",
            raw_input="test input",
            processed_code="def test(): pass",
        )

        # Refresh from database to get actual stored value
        submission.refresh_from_db()

        assert submission.is_late is False

    def test_submission_with_explicit_is_late_true(self):
        """Explicit is_late=True should be respected."""
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type="eipl",
            raw_input="test input",
            processed_code="def test(): pass",
            is_late=True,
        )

        submission.refresh_from_db()
        assert submission.is_late is True

    def test_submission_with_explicit_is_late_false(self):
        """Explicit is_late=False should be respected."""
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type="eipl",
            raw_input="test input",
            processed_code="def test(): pass",
            is_late=False,
        )

        submission.refresh_from_db()
        assert submission.is_late is False

    def test_raw_sql_insert_without_is_late(self):
        """
        Raw SQL INSERT without is_late column should use database default.

        This tests the actual database-level default behavior, bypassing
        Django ORM. This is the scenario that caused Bug 3.
        """
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        with connection.cursor() as cursor:
            # Insert via raw SQL, omitting is_late column entirely
            cursor.execute(
                """
                INSERT INTO submissions_submission
                (submission_id, user_id, problem_id, problem_set_id,
                 submission_type, raw_input, processed_code,
                 execution_status, score, passed_all_tests, completion_status,
                 is_correct, comprehension_level, submitted_at)
                VALUES
                (gen_random_uuid(), %s, %s, %s,
                 'eipl', 'test raw input', 'def t(): pass',
                 'pending', 0, false, 'incomplete',
                 false, 'not_evaluated', NOW())
                RETURNING id
                """,
                [user.id, problem.id, problem_set.id],
            )
            result = cursor.fetchone()
            submission_id = result[0]

        # Fetch via ORM and verify is_late defaulted to False
        submission = Submission.objects.get(id=submission_id)
        assert submission.is_late is False

    def test_bulk_create_without_is_late(self):
        """
        Bulk create without is_late should use default.

        This tests that bulk_create also respects the default.
        """
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        submissions = [
            Submission(
                user=user,
                problem=problem,
                problem_set=problem_set,
                submission_type="eipl",
                raw_input=f"test input {i}",
                processed_code="def test(): pass",
                # Note: is_late is NOT set
            )
            for i in range(3)
        ]

        created = Submission.objects.bulk_create(submissions)

        # Verify all have is_late=False
        for sub in created:
            sub.refresh_from_db()
            assert sub.is_late is False


@pytest.mark.django_db
class TestSubmissionIsLateIndexed:
    """
    Tests that verify is_late is properly indexed for query performance.
    """

    def test_is_late_filter_query(self):
        """Filtering by is_late should use index (basic query test)."""
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        # Create some submissions with different is_late values
        Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type="eipl",
            raw_input="on time",
            processed_code="def test(): pass",
            is_late=False,
        )
        Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            submission_type="eipl",
            raw_input="late",
            processed_code="def test(): pass",
            is_late=True,
        )

        # Query should work (index verification is more for EXPLAIN analysis)
        on_time = Submission.objects.filter(is_late=False)
        late = Submission.objects.filter(is_late=True)

        assert on_time.count() >= 1
        assert late.count() >= 1
