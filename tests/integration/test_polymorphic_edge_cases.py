"""
Edge case and stress tests for polymorphic models.

Tests cover:
- Cascade deletion behavior
- Concurrent access patterns
- Transaction handling
- Model validation with polymorphism
- Orphaned record handling
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from purplex.problems_app.models import (
    Course,
    EiplProblem,
    McqProblem,
    Problem,
    ProblemSet,
    ProblemSetMembership,
    PromptProblem,
    UserProgress,
)
from purplex.submissions.models import Submission
from purplex.users_app.models import UserProfile

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def edge_user(db):
    """User for edge case tests."""
    user = User.objects.create_user(
        username="edge_test_user",
        email="edge_test@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="edge-test-uid")
    return user


@pytest.fixture
def edge_instructor(db):
    """Instructor for edge case tests."""
    user = User.objects.create_user(
        username="edge_instructor",
        email="edge_instructor@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="edge-instructor-uid")
    return user


@pytest.fixture
def edge_problem_set(db):
    """Problem set for edge case tests."""
    return ProblemSet.objects.create(
        slug="edge-test-ps",
        title="Edge Test Set",
    )


@pytest.fixture
def edge_course(db, edge_instructor, edge_problem_set):
    """Course for edge case tests."""
    course = Course.objects.create(
        course_id="EDGE-TEST-101",
        name="Edge Test Course",
        instructor=edge_instructor,
    )
    course.problem_sets.add(edge_problem_set)
    return course


# ─────────────────────────────────────────────────────────────────────────────
# Cascade Delete Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCascadeDeletePolymorphic:
    """
    Tests for cascade deletion with polymorphic models.

    Deleting a Problem should cascade to:
    - ProblemSetMembership
    - Submission (on_delete=CASCADE)
    - UserProgress (on_delete=CASCADE)
    """

    def test_delete_eipl_cascades_to_memberships(self, edge_problem_set):
        """Deleting EiplProblem should delete memberships."""
        eipl = EiplProblem.objects.create(
            slug="delete-eipl",
            title="Delete EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        ProblemSetMembership.objects.create(
            problem_set=edge_problem_set,
            problem=eipl,
            order=0,
        )

        assert ProblemSetMembership.objects.filter(problem=eipl).exists()

        eipl.delete()

        assert not ProblemSetMembership.objects.filter(problem_id=eipl.id).exists()

    def test_delete_mcq_protected_by_submissions(self, edge_user, edge_problem_set):
        """
        Deleting McqProblem with submissions should raise ProtectedError.

        This is defensive design - prevents accidental data loss.
        Submissions must be deleted first before deleting the problem.
        """
        from django.db.models.deletion import ProtectedError

        mcq = McqProblem.objects.create(
            slug="delete-mcq",
            title="Delete MCQ",
            question_text="Test?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        Submission.objects.create(
            user=edge_user,
            problem=mcq,
            problem_set=edge_problem_set,
            raw_input="a",
            submission_type="mcq",
        )

        # Should raise ProtectedError - FK is PROTECTED not CASCADE
        with pytest.raises(ProtectedError):
            mcq.delete()

    def test_delete_problem_protected_by_progress(
        self, edge_user, edge_problem_set, edge_course
    ):
        """
        Deleting Problem with progress should raise ProtectedError.

        This is defensive design - prevents accidental data loss.
        Progress must be deleted first before deleting the problem.
        """
        from django.db.models.deletion import ProtectedError

        prompt = PromptProblem.objects.create(
            slug="delete-prompt",
            title="Delete Prompt",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        UserProgress.objects.create(
            user=edge_user,
            problem=prompt,
            problem_set=edge_problem_set,
            course=edge_course,
        )

        # Should raise ProtectedError - FK is PROTECTED not CASCADE
        with pytest.raises(ProtectedError):
            prompt.delete()

    def test_delete_base_problem_deletes_subclass(self, db):
        """
        Deleting via Problem.objects should delete the subclass instance.

        This tests that polymorphic delete works correctly.
        """
        eipl = EiplProblem.objects.create(
            slug="base-delete-eipl",
            title="Base Delete EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        pk = eipl.pk

        # Delete via base manager
        Problem.objects.filter(pk=pk).delete()

        # Should be gone from both
        assert not Problem.objects.filter(pk=pk).exists()
        assert not EiplProblem.objects.filter(pk=pk).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Model Validation Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicValidation:
    """Tests for model validation with polymorphic models."""

    def test_eipl_requires_reference_solution(self, db):
        """EiplProblem should require reference_solution."""
        from django.core.exceptions import ValidationError

        eipl = EiplProblem(
            slug="invalid-eipl",
            title="Invalid EiPL",
            function_signature="def x() -> None",
            # Missing reference_solution
        )

        with pytest.raises(ValidationError):
            eipl.full_clean()

    def test_mcq_requires_at_least_two_options(self, db):
        """McqProblem should require at least 2 options."""
        from django.core.exceptions import ValidationError

        mcq = McqProblem(
            slug="invalid-mcq",
            title="Invalid MCQ",
            question_text="Test?",
            options=[{"id": "a", "text": "A", "is_correct": True}],  # Only 1
        )

        with pytest.raises(ValidationError):
            mcq.full_clean()

    def test_mcq_requires_correct_answer(self, db):
        """McqProblem should require at least one correct answer."""
        from django.core.exceptions import ValidationError

        mcq = McqProblem(
            slug="no-correct-mcq",
            title="No Correct MCQ",
            question_text="Test?",
            options=[
                {"id": "a", "text": "A", "is_correct": False},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )

        with pytest.raises(ValidationError):
            mcq.full_clean()

    def test_prompt_requires_image_url(self, db):
        """PromptProblem should require image_url."""
        from django.core.exceptions import ValidationError

        prompt = PromptProblem(
            slug="invalid-prompt",
            title="Invalid Prompt",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            # Missing image_url
        )

        with pytest.raises(ValidationError):
            prompt.full_clean()


# ─────────────────────────────────────────────────────────────────────────────
# Unique Constraint Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicUniqueConstraints:
    """Tests for unique constraints across polymorphic models."""

    def test_slug_unique_across_problem_types(self, db):
        """Slug should be unique across all problem types."""
        EiplProblem.objects.create(
            slug="unique-slug",
            title="EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        # Should fail - slug already exists on EiplProblem
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                McqProblem.objects.create(
                    slug="unique-slug",  # Duplicate
                    title="MCQ",
                    question_text="Test?",
                    options=[
                        {"id": "a", "text": "A", "is_correct": True},
                        {"id": "b", "text": "B", "is_correct": False},
                    ],
                )

    def test_problem_set_membership_unique_together(self, edge_problem_set):
        """Same problem cannot be in same problem set twice."""
        eipl = EiplProblem.objects.create(
            slug="membership-eipl",
            title="Membership EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        ProblemSetMembership.objects.create(
            problem_set=edge_problem_set,
            problem=eipl,
            order=0,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemSetMembership.objects.create(
                    problem_set=edge_problem_set,
                    problem=eipl,
                    order=1,
                )


# ─────────────────────────────────────────────────────────────────────────────
# Transaction Handling Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
class TestPolymorphicTransactions:
    """Tests for transaction handling with polymorphic models."""

    def test_atomic_create_rollback(self, db):
        """Failed transaction should rollback polymorphic creates."""
        initial_count = Problem.objects.count()

        try:
            with transaction.atomic():
                EiplProblem.objects.create(
                    slug="atomic-eipl",
                    title="Atomic EiPL",
                    reference_solution="def x(): pass",
                    function_signature="def x() -> None",
                )
                # Force failure
                raise ValueError("Intentional failure")
        except ValueError:
            pass

        # Should have rolled back
        assert Problem.objects.count() == initial_count

    def test_atomic_update_rollback(self, db):
        """Failed transaction should rollback polymorphic updates."""
        eipl = EiplProblem.objects.create(
            slug="atomic-update-eipl",
            title="Original Title",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        try:
            with transaction.atomic():
                eipl.title = "Modified Title"
                eipl.save()
                raise ValueError("Intentional failure")
        except ValueError:
            pass

        # Refetch - should have original title
        eipl.refresh_from_db()
        assert eipl.title == "Original Title"


# ─────────────────────────────────────────────────────────────────────────────
# Polymorphic Type Coercion Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicTypeCoercion:
    """
    Tests for type consistency in polymorphic models.

    Ensures that Problem instances are always correctly typed.
    """

    def test_create_returns_correct_subclass(self, db):
        """objects.create() should return subclass instance."""
        eipl = EiplProblem.objects.create(
            slug="coerce-eipl",
            title="Coerce EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        assert isinstance(eipl, EiplProblem)
        assert type(eipl).__name__ == "EiplProblem"

    def test_get_returns_correct_subclass(self, db):
        """Problem.objects.get() should return correct subclass."""
        eipl = EiplProblem.objects.create(
            slug="get-eipl",
            title="Get EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        fetched = Problem.objects.get(pk=eipl.pk)

        assert isinstance(fetched, EiplProblem)

    def test_filter_returns_correct_subclasses(self, db):
        """Problem.objects.filter() should return correct subclasses."""
        EiplProblem.objects.create(
            slug="filter-eipl",
            title="Filter EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        McqProblem.objects.create(
            slug="filter-mcq",
            title="Filter MCQ",
            question_text="Test?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )

        problems = list(Problem.objects.filter(slug__startswith="filter-"))

        types = {type(p).__name__ for p in problems}
        assert types == {"EiplProblem", "McqProblem"}


# ─────────────────────────────────────────────────────────────────────────────
# Query Efficiency Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicQueryEfficiency:
    """
    Tests for query efficiency with polymorphic models.

    These tests verify that common operations don't cause unexpected
    query explosions.
    """

    def test_count_does_not_resolve_polymorphism(self, db):
        """count() should not need polymorphic resolution."""
        EiplProblem.objects.create(
            slug="count-eipl",
            title="Count EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            count = Problem.objects.count()

        # count() should be a single query
        assert count >= 1
        assert len(ctx.captured_queries) == 1

    def test_exists_does_not_resolve_polymorphism(self, db):
        """exists() should not need polymorphic resolution."""
        EiplProblem.objects.create(
            slug="exists-eipl",
            title="Exists EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            exists = Problem.objects.filter(slug="exists-eipl").exists()

        assert exists is True
        # exists() should be a single query
        assert len(ctx.captured_queries) == 1
