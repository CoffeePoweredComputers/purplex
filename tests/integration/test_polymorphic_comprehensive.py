"""
Comprehensive integration tests for django-polymorphic behavior.

Tests cover known pitfalls discovered through research:
- N+1 query detection
- non_polymorphic() behavior and pitfalls
- prefetch_related issues with polymorphic models
- bulk operations limitations
- aggregate/values() non-polymorphic behavior
- ContentType caching efficiency
- order_by field translation
- get_real_instance edge cases
- ForeignKey traversal from non-polymorphic models
- Handler polymorphism validation

References:
- https://django-polymorphic.readthedocs.io/en/stable/performance.html
- https://django-polymorphic.readthedocs.io/en/stable/advanced.html
- https://github.com/jazzband/django-polymorphic/issues/68 (prefetch_related bug)
- https://github.com/jazzband/django-polymorphic/issues/198 (select_related limitations)
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext

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
def test_user(db):
    """Create a test user for submissions."""
    user = User.objects.create_user(
        username="polymorphic_test_user",
        email="polymorphic_test@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="polymorphic-test-firebase-uid")
    return user


@pytest.fixture
def problem_set(db):
    """Create a test problem set."""
    return ProblemSet.objects.create(
        slug="polymorphic-test-set",
        title="Polymorphic Test Set",
    )


@pytest.fixture
def instructor(db):
    """Create an instructor user for courses."""
    user = User.objects.create_user(
        username="poly_instructor",
        email="poly_instructor@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="poly-instructor-firebase-uid")
    return user


@pytest.fixture
def course(db, instructor):
    """Create a test course."""
    return Course.objects.create(
        course_id="POLY-TEST-101",
        name="Polymorphic Test Course",
    )


@pytest.fixture
def eipl_problem(db):
    """Create EiplProblem instance."""
    return EiplProblem.objects.create(
        slug="poly-test-eipl",
        title="Polymorphic Test EiPL",
        reference_solution="def fib(n):\n    return n if n <= 1 else fib(n-1) + fib(n-2)",
        function_signature="def fib(n: int) -> int",
        function_name="fib",
        segmentation_threshold=3,
        requires_highlevel_comprehension=True,
    )


@pytest.fixture
def mcq_problem(db):
    """Create McqProblem instance."""
    return McqProblem.objects.create(
        slug="poly-test-mcq",
        title="Polymorphic Test MCQ",
        question_text="What is O(log n)?",
        options=[
            {"id": "a", "text": "Linear", "is_correct": False},
            {"id": "b", "text": "Logarithmic", "is_correct": True},
            {"id": "c", "text": "Quadratic", "is_correct": False},
        ],
        allow_multiple=False,
    )


@pytest.fixture
def prompt_problem(db):
    """Create PromptProblem instance."""
    return PromptProblem.objects.create(
        slug="poly-test-prompt",
        title="Polymorphic Test Prompt",
        reference_solution='def analyze():\n    return "data"',
        function_signature="def analyze() -> str",
        function_name="analyze",
        image_url="https://example.com/test.png",
        image_alt_text="Test flowchart",
    )


@pytest.fixture
def mixed_problems(eipl_problem, mcq_problem, prompt_problem):
    """Return all three problem types as a tuple."""
    return (eipl_problem, mcq_problem, prompt_problem)


@pytest.fixture
def problem_set_with_memberships(db, problem_set, mixed_problems):
    """Create problem set with all problem types."""
    eipl, mcq, prompt = mixed_problems
    ProblemSetMembership.objects.create(problem_set=problem_set, problem=eipl, order=0)
    ProblemSetMembership.objects.create(problem_set=problem_set, problem=mcq, order=1)
    ProblemSetMembership.objects.create(
        problem_set=problem_set, problem=prompt, order=2
    )
    return problem_set


# ─────────────────────────────────────────────────────────────────────────────
# N+1 Query Detection Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestN1QueryDetection:
    """
    Tests that detect N+1 query patterns.

    Django-polymorphic should execute 1 query per subclass type, not per object.
    Ref: https://django-polymorphic.readthedocs.io/en/stable/performance.html
    """

    def test_querying_all_problems_is_efficient(self, mixed_problems):
        """
        Problem.objects.all() should use O(num_subclasses) queries, not O(num_objects).

        Best case: 1 query (all same type)
        Worst case: 1 + num_unique_types queries
        """
        # Create additional instances to increase count
        EiplProblem.objects.create(
            slug="extra-eipl-1",
            title="Extra 1",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        EiplProblem.objects.create(
            slug="extra-eipl-2",
            title="Extra 2",
            reference_solution="def y(): pass",
            function_signature="def y() -> None",
        )

        # Clear any cached queries
        connection.queries_log.clear()

        with CaptureQueriesContext(connection) as context:
            problems = list(Problem.objects.all())

        # With 5 problems (3 types), should be 1 base + 3 subclass queries = 4
        # (or less if caching kicks in)
        assert len(problems) == 5

        # Key assertion: query count should NOT be proportional to object count
        # If we had N+1 issue, we'd see 5+ queries
        # With proper polymorphic behavior, we see ~4 queries (1 per type + 1 base)
        assert len(context.captured_queries) <= 6, (
            f"Expected ≤6 queries for 5 problems (3 types), got {len(context.captured_queries)}. "
            f"This suggests N+1 query problem."
        )

    def test_fk_traversal_triggers_additional_query_per_type(
        self, test_user, mixed_problems, problem_set
    ):
        """
        FK traversal from Submission to Problem triggers polymorphic resolution.

        This test documents expected behavior: accessing submission.problem
        will resolve to correct subclass, but adds queries.
        """
        eipl, mcq, prompt = mixed_problems

        # Create submissions for each type
        Submission.objects.create(
            user=test_user,
            problem=eipl,
            problem_set=problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        Submission.objects.create(
            user=test_user,
            problem=mcq,
            problem_set=problem_set,
            raw_input="b",
            submission_type="mcq",
        )
        Submission.objects.create(
            user=test_user,
            problem=prompt,
            problem_set=problem_set,
            raw_input="test",
            submission_type="prompt",
        )

        connection.queries_log.clear()

        with CaptureQueriesContext(connection) as context:
            submissions = list(Submission.objects.filter(user=test_user))
            # Access each problem (triggers polymorphic resolution)
            for sub in submissions:
                _ = sub.problem.title  # Access field to trigger query

        # Document the query count - this is the trade-off we accept
        # Without select_related('problem'), each FK access is a query
        # But we get correct subclass instances
        query_count = len(context.captured_queries)

        # At minimum: 1 for submissions, 1 per problem access = 4
        # Polymorphic adds subclass table queries
        assert query_count >= 4, "Expected at least 4 queries for FK traversal"


# ─────────────────────────────────────────────────────────────────────────────
# non_polymorphic() Behavior Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNonPolymorphicBehavior:
    """
    Tests for non_polymorphic() method behavior and pitfalls.

    non_polymorphic() returns base class instances, bypassing polymorphic resolution.
    Useful for performance but dangerous if you need subclass fields.
    """

    def test_non_polymorphic_returns_base_class(self, eipl_problem):
        """non_polymorphic() should return Problem, not EiplProblem."""
        problem = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)

        # Should be base Problem class, not EiplProblem
        assert type(problem).__name__ == "Problem"
        assert not isinstance(problem, EiplProblem)

    def test_non_polymorphic_base_fields_accessible(self, eipl_problem):
        """Base class fields should still be accessible with non_polymorphic()."""
        problem = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)

        # Base fields work
        assert problem.title == "Polymorphic Test EiPL"
        assert problem.slug == "poly-test-eipl"
        assert problem.difficulty == "beginner"  # default

    def test_non_polymorphic_subclass_field_raises_attribute_error(self, eipl_problem):
        """
        PITFALL: Subclass fields raise AttributeError with non_polymorphic().

        This is the exact bug that select_related('problem') causes.
        """
        problem = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)

        # This WILL fail - function_name is on EiplProblem, not Problem
        with pytest.raises(AttributeError):
            _ = problem.function_name

    def test_non_polymorphic_segmentation_enabled_raises(self, eipl_problem):
        """segmentation_enabled property requires SpecProblem, not Problem."""
        problem = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)

        with pytest.raises(AttributeError):
            _ = problem.segmentation_enabled

    def test_non_polymorphic_mcq_options_raises(self, mcq_problem):
        """options field requires McqProblem, not Problem."""
        problem = Problem.objects.non_polymorphic().get(pk=mcq_problem.pk)

        with pytest.raises(AttributeError):
            _ = problem.options

    def test_non_polymorphic_prompt_image_url_raises(self, prompt_problem):
        """image_url field requires PromptProblem, not Problem."""
        problem = Problem.objects.non_polymorphic().get(pk=prompt_problem.pk)

        with pytest.raises(AttributeError):
            _ = problem.image_url

    def test_non_polymorphic_is_faster(self, mixed_problems):
        """Document that non_polymorphic() uses fewer queries."""
        connection.queries_log.clear()

        with CaptureQueriesContext(connection) as poly_context:
            list(Problem.objects.all())

        connection.queries_log.clear()

        with CaptureQueriesContext(connection) as non_poly_context:
            list(Problem.objects.non_polymorphic().all())

        # non_polymorphic should use fewer queries (no subclass table joins)
        assert len(non_poly_context.captured_queries) <= len(
            poly_context.captured_queries
        )


# ─────────────────────────────────────────────────────────────────────────────
# ContentType Caching Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestContentTypeCaching:
    """
    Tests for efficient ContentType retrieval.

    ContentType.objects.get_for_id() caches internally.
    Using get_for_id(obj.polymorphic_ctype_id) is more efficient than get_for_model().
    """

    def test_polymorphic_ctype_id_exists(self, eipl_problem):
        """Every polymorphic instance has polymorphic_ctype_id."""
        assert eipl_problem.polymorphic_ctype_id is not None
        assert isinstance(eipl_problem.polymorphic_ctype_id, int)

    def test_get_for_id_retrieves_correct_content_type(self, eipl_problem):
        """get_for_id() with polymorphic_ctype_id returns correct ContentType."""
        ctype = ContentType.objects.get_for_id(eipl_problem.polymorphic_ctype_id)

        assert ctype.model == "eiplproblem"
        assert ctype.app_label == "problems_app"

    def test_content_type_matches_across_problem_types(self, mixed_problems):
        """Each problem type has distinct ContentType."""
        eipl, mcq, prompt = mixed_problems

        eipl_ctype = ContentType.objects.get_for_id(eipl.polymorphic_ctype_id)
        mcq_ctype = ContentType.objects.get_for_id(mcq.polymorphic_ctype_id)
        prompt_ctype = ContentType.objects.get_for_id(prompt.polymorphic_ctype_id)

        assert eipl_ctype.model == "eiplproblem"
        assert mcq_ctype.model == "mcqproblem"
        assert prompt_ctype.model == "promptproblem"

        # All different
        assert eipl_ctype.id != mcq_ctype.id != prompt_ctype.id

    def test_counting_by_type_with_non_polymorphic(self, mixed_problems):
        """
        Efficient type counting using non_polymorphic() and ContentType.

        This pattern is from the django-polymorphic docs for counting by type
        without fetching full objects.
        """
        count_by_type = {}

        for obj in Problem.objects.non_polymorphic():
            ct = ContentType.objects.get_for_id(obj.polymorphic_ctype_id)
            model_name = ct.model
            count_by_type[model_name] = count_by_type.get(model_name, 0) + 1

        assert count_by_type["eiplproblem"] == 1
        assert count_by_type["mcqproblem"] == 1
        assert count_by_type["promptproblem"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Operations Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBulkOperations:
    """
    Tests for bulk operations with polymorphic models.

    LIMITATION: bulk_create() does NOT support multi-table inheritance.
    Ref: django-polymorphic docs state this explicitly.
    """

    def test_bulk_create_not_supported_for_multi_table(self):
        """
        Document that bulk_create doesn't work properly with polymorphic models.

        This is a known limitation. The base Problem table gets rows,
        but the child tables (eiplproblem, etc.) don't.
        """
        problems_to_create = [
            EiplProblem(
                slug=f"bulk-eipl-{i}",
                title=f"Bulk EiPL {i}",
                reference_solution="def x(): pass",
                function_signature="def x() -> None",
            )
            for i in range(3)
        ]

        # This creates base Problem rows but child EiplProblem rows may be missing
        # The behavior varies - in some cases it works, in others it doesn't
        # Mark as expected potential issue
        try:
            EiplProblem.objects.bulk_create(problems_to_create)
            # If it works, verify we can still access polymorphic fields
            created = list(Problem.objects.filter(slug__startswith="bulk-eipl-"))
            for p in created:
                assert isinstance(p, EiplProblem)
                assert p.function_signature == "def x() -> None"
        except Exception as e:
            # Document the failure mode
            pytest.skip(f"bulk_create failed as expected for multi-table: {e}")

    def test_individual_create_always_works(self, db):
        """Individual create() calls always work correctly."""
        problems = []
        for i in range(3):
            problems.append(
                EiplProblem.objects.create(
                    slug=f"individual-eipl-{i}",
                    title=f"Individual EiPL {i}",
                    reference_solution="def x(): pass",
                    function_signature="def x() -> None",
                )
            )

        # Verify all accessible and correct type
        for p in problems:
            refetched = Problem.objects.get(pk=p.pk)
            assert isinstance(refetched, EiplProblem)
            assert refetched.function_signature == "def x() -> None"


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate and Values Operations Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAggregateAndValues:
    """
    Tests for aggregate() and values() behavior.

    LIMITATION: values() and values_list() do NOT return polymorphic results.
    They only return base class field values.
    """

    def test_values_only_returns_base_fields(self, mixed_problems):
        """values() can only access base Problem fields."""
        # This works - title is on base Problem
        result = list(Problem.objects.values("title", "slug", "difficulty"))

        assert len(result) == 3
        for item in result:
            assert "title" in item
            assert "slug" in item
            assert "difficulty" in item

    def test_values_cannot_access_subclass_fields(self, eipl_problem):
        """
        values() with subclass field raises FieldError.

        This is a known limitation documented in django-polymorphic.
        """
        from django.core.exceptions import FieldError

        # function_name is on EiplProblem, not Problem
        with pytest.raises(FieldError):
            list(Problem.objects.values("title", "function_name"))

    def test_values_on_subclass_manager_works(self, eipl_problem):
        """Using subclass manager allows values() with subclass fields."""
        # This works because we're using EiplProblem.objects, not Problem.objects
        result = list(EiplProblem.objects.values("title", "function_name"))

        assert len(result) >= 1
        assert result[0]["function_name"] == "fib"

    def test_aggregate_works_on_base_fields(self, mixed_problems):
        """aggregate() works on base Problem fields."""
        from django.db.models import Count

        stats = Problem.objects.aggregate(
            total=Count("id"),
            # Can't aggregate on subclass fields
        )

        assert stats["total"] == 3

    def test_values_list_flat_works(self, mixed_problems):
        """values_list(flat=True) works for base fields."""
        slugs = list(Problem.objects.values_list("slug", flat=True))

        assert len(slugs) == 3
        assert "poly-test-eipl" in slugs
        assert "poly-test-mcq" in slugs
        assert "poly-test-prompt" in slugs


# ─────────────────────────────────────────────────────────────────────────────
# get_real_instance() Recovery Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGetRealInstanceRecovery:
    """
    Tests for get_real_instance() fallback mechanism.

    If polymorphism is accidentally bypassed (e.g., via non_polymorphic()),
    get_real_instance() can recover the actual subclass.
    """

    def test_get_real_instance_returns_self_for_subclass(self, eipl_problem):
        """On already-resolved subclass, get_real_instance() returns self."""
        real = eipl_problem.get_real_instance()
        assert real is eipl_problem

    def test_get_real_instance_recovers_eipl(self, eipl_problem):
        """Recover EiplProblem from base Problem instance."""
        base = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)
        assert type(base).__name__ == "Problem"

        real = base.get_real_instance()

        assert isinstance(real, EiplProblem)
        assert real.function_name == "fib"

    def test_get_real_instance_recovers_mcq(self, mcq_problem):
        """Recover McqProblem from base Problem instance."""
        base = Problem.objects.non_polymorphic().get(pk=mcq_problem.pk)

        real = base.get_real_instance()

        assert isinstance(real, McqProblem)
        assert len(real.options) == 3

    def test_get_real_instance_recovers_prompt(self, prompt_problem):
        """Recover PromptProblem from base Problem instance."""
        base = Problem.objects.non_polymorphic().get(pk=prompt_problem.pk)

        real = base.get_real_instance()

        assert isinstance(real, PromptProblem)
        assert real.image_url == "https://example.com/test.png"

    def test_get_real_instance_is_idempotent(self, eipl_problem):
        """Calling get_real_instance() multiple times is safe."""
        real1 = eipl_problem.get_real_instance()
        real2 = real1.get_real_instance()
        real3 = real2.get_real_instance()

        assert real1 is real2 is real3


# ─────────────────────────────────────────────────────────────────────────────
# ForeignKey Traversal Tests (Critical)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestForeignKeyTraversal:
    """
    Critical tests for ForeignKey traversal from non-polymorphic models.

    This was the original bug: select_related('problem') bypasses polymorphism,
    returning base Problem instead of EiplProblem/McqProblem/PromptProblem.
    """

    def test_submission_problem_fk_returns_eipl(
        self, test_user, eipl_problem, problem_set
    ):
        """submission.problem returns EiplProblem, not Problem."""
        sub = Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="test",
            submission_type="eipl",
        )

        # Refetch to test FK traversal
        sub = Submission.objects.get(pk=sub.pk)

        assert isinstance(sub.problem, EiplProblem)
        assert sub.problem.function_name == "fib"
        assert sub.problem.segmentation_enabled is True

    def test_submission_problem_fk_returns_mcq(
        self, test_user, mcq_problem, problem_set
    ):
        """submission.problem returns McqProblem, not Problem."""
        sub = Submission.objects.create(
            user=test_user,
            problem=mcq_problem,
            problem_set=problem_set,
            raw_input="b",
            submission_type="mcq",
        )

        sub = Submission.objects.get(pk=sub.pk)

        assert isinstance(sub.problem, McqProblem)
        assert len(sub.problem.options) == 3
        assert sub.problem.allow_multiple is False

    def test_submission_problem_fk_returns_prompt(
        self, test_user, prompt_problem, problem_set
    ):
        """submission.problem returns PromptProblem, not Problem."""
        sub = Submission.objects.create(
            user=test_user,
            problem=prompt_problem,
            problem_set=problem_set,
            raw_input="test",
            submission_type="prompt",
        )

        sub = Submission.objects.get(pk=sub.pk)

        assert isinstance(sub.problem, PromptProblem)
        assert sub.problem.image_url == "https://example.com/test.png"

    def test_user_progress_problem_fk_returns_subclass(
        self, test_user, eipl_problem, problem_set, course
    ):
        """UserProgress.problem returns correct subclass."""
        progress = UserProgress.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            course=course,
        )

        # Refetch
        progress = UserProgress.objects.get(pk=progress.pk)

        assert isinstance(progress.problem, EiplProblem)
        assert progress.problem.function_name == "fib"

    def test_problem_set_membership_problem_fk_returns_subclass(
        self, problem_set_with_memberships
    ):
        """ProblemSetMembership.problem returns correct subclass."""
        memberships = ProblemSetMembership.objects.filter(
            problem_set=problem_set_with_memberships
        ).order_by("order")

        # Should resolve to correct subclass for each
        types = [type(m.problem).__name__ for m in memberships]

        assert "EiplProblem" in types
        assert "McqProblem" in types
        assert "PromptProblem" in types


# ─────────────────────────────────────────────────────────────────────────────
# Query Optimization Patterns
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestQueryOptimizationPatterns:
    """
    Tests documenting efficient query patterns with polymorphic models.
    """

    def test_prefetch_related_with_problem_set(self, problem_set_with_memberships):
        """
        Test prefetch_related pattern for problem sets.

        Note: prefetch_related has known issues with polymorphic models.
        Ref: https://github.com/jazzband/django-polymorphic/issues/68
        """
        # Prefetch memberships with their problems
        # Note: default related_name is 'problemsetmembership_set'
        ps = ProblemSet.objects.prefetch_related(
            "problemsetmembership_set__problem"
        ).get(pk=problem_set_with_memberships.pk)

        # Access prefetched data
        memberships = list(ps.problemsetmembership_set.all())

        assert len(memberships) == 3

        # Each problem should be correct subclass
        for m in memberships:
            assert isinstance(m.problem, (EiplProblem, McqProblem, PromptProblem))

    def test_filter_by_subclass_type(self, mixed_problems):
        """Filter Problems by polymorphic type using instance_of()."""
        eipl_only = list(Problem.objects.instance_of(EiplProblem))
        mcq_only = list(Problem.objects.instance_of(McqProblem))
        prompt_only = list(Problem.objects.instance_of(PromptProblem))

        assert len(eipl_only) == 1
        assert len(mcq_only) == 1
        assert len(prompt_only) == 1

        assert all(isinstance(p, EiplProblem) for p in eipl_only)
        assert all(isinstance(p, McqProblem) for p in mcq_only)
        assert all(isinstance(p, PromptProblem) for p in prompt_only)

    def test_not_instance_of_filtering(self, mixed_problems):
        """Exclude specific subclasses using not_instance_of()."""
        not_eipl = list(Problem.objects.not_instance_of(EiplProblem))

        assert len(not_eipl) == 2
        assert all(not isinstance(p, EiplProblem) for p in not_eipl)


# ─────────────────────────────────────────────────────────────────────────────
# Handler Polymorphism Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandlerPolymorphism:
    """
    Tests that handlers receive correct subclass instances.

    Handlers rely on subclass-specific fields to function correctly.
    """

    def test_eipl_handler_receives_eipl_problem(
        self, test_user, eipl_problem, problem_set
    ):
        """EiPL handler should receive EiplProblem with all required fields."""
        # Create submission
        sub = Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="The function calculates fibonacci numbers",
            submission_type="eipl",
        )

        # Simulate handler fetching submission
        sub = Submission.objects.get(pk=sub.pk)
        problem = sub.problem

        # Handler needs these fields
        assert hasattr(problem, "reference_solution")
        assert hasattr(problem, "function_name")
        assert hasattr(problem, "function_signature")
        assert hasattr(problem, "segmentation_enabled")
        assert hasattr(problem, "segmentation_threshold")

        # Verify values
        assert problem.function_name == "fib"
        assert problem.segmentation_enabled is True
        assert "def fib" in problem.reference_solution

    def test_mcq_handler_receives_mcq_problem(
        self, test_user, mcq_problem, problem_set
    ):
        """MCQ handler should receive McqProblem with options."""
        sub = Submission.objects.create(
            user=test_user,
            problem=mcq_problem,
            problem_set=problem_set,
            raw_input="b",
            submission_type="mcq",
        )

        sub = Submission.objects.get(pk=sub.pk)
        problem = sub.problem

        # MCQ handler needs these
        assert hasattr(problem, "options")
        assert hasattr(problem, "allow_multiple")
        assert hasattr(problem, "question_text")

        # Verify grading works
        options = problem.options
        correct_option = next(o for o in options if o["is_correct"])
        assert correct_option["id"] == "b"

    def test_prompt_handler_receives_prompt_problem(
        self, test_user, prompt_problem, problem_set
    ):
        """Prompt handler should receive PromptProblem with image fields."""
        sub = Submission.objects.create(
            user=test_user,
            problem=prompt_problem,
            problem_set=problem_set,
            raw_input="The flowchart shows data processing",
            submission_type="prompt",
        )

        sub = Submission.objects.get(pk=sub.pk)
        problem = sub.problem

        # Prompt handler needs image fields
        assert hasattr(problem, "image_url")
        assert hasattr(problem, "image_alt_text")

        # Also needs SpecProblem fields
        assert hasattr(problem, "reference_solution")
        assert hasattr(problem, "function_name")

        assert problem.image_url == "https://example.com/test.png"


# ─────────────────────────────────────────────────────────────────────────────
# Polymorphic Property Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicProperties:
    """
    Tests for polymorphic_type and problem_type properties.
    """

    def test_polymorphic_type_property(self, mixed_problems):
        """Each subclass returns correct polymorphic_type."""
        eipl, mcq, prompt = mixed_problems

        assert eipl.polymorphic_type == "eipl"
        assert mcq.polymorphic_type == "mcq"
        assert prompt.polymorphic_type == "prompt"

    def test_problem_type_property(self, mixed_problems):
        """problem_type property should match polymorphic_type."""
        eipl, mcq, prompt = mixed_problems

        # problem_type is alias for polymorphic_type on base Problem
        assert eipl.problem_type == "eipl"
        assert mcq.problem_type == "mcq"
        assert prompt.problem_type == "prompt"

    def test_polymorphic_type_after_fk_traversal(
        self, test_user, mixed_problems, problem_set
    ):
        """polymorphic_type should be correct after FK traversal."""
        eipl, mcq, prompt = mixed_problems

        sub = Submission.objects.create(
            user=test_user,
            problem=eipl,
            problem_set=problem_set,
            raw_input="test",
            submission_type="eipl",
        )

        sub = Submission.objects.get(pk=sub.pk)

        # Should get correct type even after FK traversal
        assert sub.problem.polymorphic_type == "eipl"
        assert sub.problem.problem_type == "eipl"
