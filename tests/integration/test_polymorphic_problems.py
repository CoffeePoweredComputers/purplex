"""
Integration tests for django-polymorphic Problem model behavior.

Tests that ForeignKey traversal returns correct subclass instances,
not base Problem class. This is critical for accessing subclass-specific
fields like function_name (EiPL), options (MCQ), image_url (Prompt).

Reference: https://django-polymorphic.readthedocs.io/en/stable/advanced.html
Issue: select_related('problem') bypasses polymorphic resolution
"""

import pytest
from django.contrib.auth import get_user_model

from purplex.problems_app.models import (
    EiplProblem,
    McqProblem,
    Problem,
    ProblemSet,
    PromptProblem,
)
from purplex.submissions.models import Submission
from purplex.users_app.models import UserProfile

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def test_user(db):
    """Create a test user for submissions."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    # Create associated UserProfile with firebase_uid
    UserProfile.objects.create(user=user, firebase_uid="test-firebase-uid")
    return user


@pytest.fixture
def problem_set(db):
    """Create a test problem set for submissions."""
    return ProblemSet.objects.create(
        slug="test-problem-set",
        title="Test Problem Set",
    )


@pytest.fixture
def eipl_problem(db):
    """Create a real EiplProblem instance."""
    return EiplProblem.objects.create(
        slug="test-eipl-problem",
        title="Test EiPL Problem",
        reference_solution="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        function_signature="def fibonacci(n: int) -> int",
        function_name="fibonacci",
        segmentation_threshold=2,
        requires_highlevel_comprehension=True,
    )


@pytest.fixture
def mcq_problem(db):
    """Create a real McqProblem instance."""
    return McqProblem.objects.create(
        slug="test-mcq-problem",
        title="Test MCQ Problem",
        question_text="What is the time complexity of binary search?",
        options=[
            {"id": "opt1", "text": "O(n)", "is_correct": False},
            {"id": "opt2", "text": "O(log n)", "is_correct": True},
            {"id": "opt3", "text": "O(n^2)", "is_correct": False},
        ],
        allow_multiple=False,
    )


@pytest.fixture
def prompt_problem(db):
    """Create a real PromptProblem instance."""
    return PromptProblem.objects.create(
        slug="test-prompt-problem",
        title="Test Prompt Problem",
        reference_solution='def analyze_flowchart():\n    return "process_data"',
        function_signature="def analyze_flowchart() -> str",
        function_name="analyze_flowchart",
        image_url="https://example.com/flowchart.png",
        image_alt_text="A flowchart showing data processing",
        requires_highlevel_comprehension=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test Polymorphic Model Resolution
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPolymorphicQueryResolution:
    """
    Tests that querying Problem.objects returns correct subclass instances.

    This is the baseline test - if django-polymorphic is configured correctly,
    Problem.objects.all() should return EiplProblem, McqProblem, etc.
    """

    def test_problem_objects_returns_eipl_subclass(self, eipl_problem):
        """Problem.objects.get() should return EiplProblem instance."""
        problem = Problem.objects.get(pk=eipl_problem.pk)
        assert isinstance(problem, EiplProblem)
        assert problem.function_name == "fibonacci"

    def test_problem_objects_returns_mcq_subclass(self, mcq_problem):
        """Problem.objects.get() should return McqProblem instance."""
        problem = Problem.objects.get(pk=mcq_problem.pk)
        assert isinstance(problem, McqProblem)
        assert len(problem.options) == 3

    def test_problem_objects_returns_prompt_subclass(self, prompt_problem):
        """Problem.objects.get() should return PromptProblem instance."""
        problem = Problem.objects.get(pk=prompt_problem.pk)
        assert isinstance(problem, PromptProblem)
        assert problem.image_url == "https://example.com/flowchart.png"

    def test_polymorphic_type_property(self, eipl_problem, mcq_problem, prompt_problem):
        """Each subclass should return correct polymorphic_type."""
        assert eipl_problem.polymorphic_type == "eipl"
        assert mcq_problem.polymorphic_type == "mcq"
        assert prompt_problem.polymorphic_type == "prompt"


@pytest.mark.django_db
class TestSubmissionProblemForeignKey:
    """
    Tests that submission.problem returns correct subclass instance.

    This is the critical test - ForeignKey traversal must return the
    actual subclass, not base Problem, to access subclass fields.
    """

    def test_submission_problem_returns_eipl_subclass(
        self, test_user, eipl_problem, problem_set
    ):
        """submission.problem should be EiplProblem instance."""
        submission = Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="The fibonacci function calculates fibonacci numbers",
            submission_type="eipl",
        )

        # Reload from database to test FK traversal
        submission = Submission.objects.get(pk=submission.pk)

        assert isinstance(submission.problem, EiplProblem)
        assert submission.problem.function_name == "fibonacci"
        assert submission.problem.segmentation_enabled is True

    def test_submission_problem_returns_mcq_subclass(
        self, test_user, mcq_problem, problem_set
    ):
        """submission.problem should be McqProblem instance."""
        submission = Submission.objects.create(
            user=test_user,
            problem=mcq_problem,
            problem_set=problem_set,
            raw_input="opt2",
            submission_type="mcq",
        )

        # Reload from database
        submission = Submission.objects.get(pk=submission.pk)

        assert isinstance(submission.problem, McqProblem)
        assert len(submission.problem.options) == 3
        assert submission.problem.allow_multiple is False

    def test_submission_problem_returns_prompt_subclass(
        self, test_user, prompt_problem, problem_set
    ):
        """submission.problem should be PromptProblem instance."""
        submission = Submission.objects.create(
            user=test_user,
            problem=prompt_problem,
            problem_set=problem_set,
            raw_input="The flowchart shows data processing steps",
            submission_type="prompt",
        )

        # Reload from database
        submission = Submission.objects.get(pk=submission.pk)

        assert isinstance(submission.problem, PromptProblem)
        assert submission.problem.image_url == "https://example.com/flowchart.png"
        assert (
            submission.problem.image_alt_text == "A flowchart showing data processing"
        )


@pytest.mark.django_db
class TestSubmissionQuerySets:
    """
    Tests that various queryset operations preserve polymorphic resolution.

    Critical: select_related('problem') bypasses polymorphism.
    These tests verify the fix is working.
    """

    def test_submission_filter_preserves_polymorphism(
        self, test_user, eipl_problem, problem_set
    ):
        """Filtering submissions should preserve polymorphic problem resolution."""
        Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="Test input",
            submission_type="eipl",
        )

        submissions = Submission.objects.filter(user=test_user)

        for sub in submissions:
            assert isinstance(sub.problem, EiplProblem)
            # This would fail if select_related('problem') was used
            assert hasattr(sub.problem, "function_name")
            assert sub.problem.function_name == "fibonacci"

    def test_submission_select_related_user_preserves_polymorphism(
        self, test_user, eipl_problem, problem_set
    ):
        """select_related on other fields should not affect problem polymorphism."""
        Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="Test input",
            submission_type="eipl",
        )

        # select_related('user') is fine, but NOT 'problem'
        submissions = Submission.objects.filter(user=test_user).select_related("user")

        for sub in submissions:
            assert isinstance(sub.problem, EiplProblem)
            assert sub.problem.function_name == "fibonacci"

    def test_multiple_problem_types_in_queryset(
        self, test_user, eipl_problem, mcq_problem, prompt_problem, problem_set
    ):
        """Queryset with mixed problem types should resolve each correctly."""
        Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="EiPL input",
            submission_type="eipl",
        )
        Submission.objects.create(
            user=test_user,
            problem=mcq_problem,
            problem_set=problem_set,
            raw_input="opt1",
            submission_type="mcq",
        )
        Submission.objects.create(
            user=test_user,
            problem=prompt_problem,
            problem_set=problem_set,
            raw_input="Prompt input",
            submission_type="prompt",
        )

        submissions = list(Submission.objects.filter(user=test_user).order_by("pk"))

        # Each should resolve to correct subclass
        assert isinstance(submissions[0].problem, EiplProblem)
        assert isinstance(submissions[1].problem, McqProblem)
        assert isinstance(submissions[2].problem, PromptProblem)

        # Subclass-specific fields should be accessible
        assert submissions[0].problem.function_name == "fibonacci"
        assert len(submissions[1].problem.options) == 3
        assert submissions[2].problem.image_url == "https://example.com/flowchart.png"


@pytest.mark.django_db
class TestSubclassFieldAccess:
    """
    Tests that subclass-specific fields are accessible after FK traversal.

    These tests will fail if select_related('problem') bypasses polymorphism
    and returns base Problem instances.
    """

    def test_eipl_function_name_accessible(self, test_user, eipl_problem, problem_set):
        """function_name field should be accessible on EiplProblem."""
        submission = Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="Test",
            submission_type="eipl",
        )

        submission = Submission.objects.get(pk=submission.pk)

        # This would raise AttributeError if problem was base Problem class
        assert submission.problem.function_name == "fibonacci"

    def test_eipl_segmentation_enabled_accessible(
        self, test_user, eipl_problem, problem_set
    ):
        """segmentation_enabled property should be accessible."""
        submission = Submission.objects.create(
            user=test_user,
            problem=eipl_problem,
            problem_set=problem_set,
            raw_input="Test",
            submission_type="eipl",
        )

        submission = Submission.objects.get(pk=submission.pk)

        # segmentation_enabled is a property on SpecProblem
        assert submission.problem.segmentation_enabled is True

    def test_mcq_options_accessible(self, test_user, mcq_problem, problem_set):
        """options field should be accessible on McqProblem."""
        submission = Submission.objects.create(
            user=test_user,
            problem=mcq_problem,
            problem_set=problem_set,
            raw_input="opt1",
            submission_type="mcq",
        )

        submission = Submission.objects.get(pk=submission.pk)

        assert len(submission.problem.options) == 3
        assert submission.problem.options[1]["is_correct"] is True

    def test_prompt_image_url_accessible(self, test_user, prompt_problem, problem_set):
        """image_url field should be accessible on PromptProblem."""
        submission = Submission.objects.create(
            user=test_user,
            problem=prompt_problem,
            problem_set=problem_set,
            raw_input="Test",
            submission_type="prompt",
        )

        submission = Submission.objects.get(pk=submission.pk)

        assert submission.problem.image_url == "https://example.com/flowchart.png"
        assert (
            submission.problem.image_alt_text == "A flowchart showing data processing"
        )


@pytest.mark.django_db
class TestGetRealInstance:
    """
    Tests for get_real_instance() fallback mechanism.

    If polymorphism is bypassed, get_real_instance() can recover
    the actual subclass. This is the backup strategy.
    """

    def test_get_real_instance_returns_same_for_subclass(self, eipl_problem):
        """get_real_instance() on subclass should return self."""
        real = eipl_problem.get_real_instance()
        assert real is eipl_problem

    def test_get_real_instance_on_base_problem_query(self, eipl_problem):
        """
        If we somehow get a base Problem, get_real_instance() recovers it.

        This tests the fallback path that handlers can use if polymorphism
        is accidentally bypassed.
        """
        # Query using non_polymorphic() to force base class
        problem = Problem.objects.non_polymorphic().get(pk=eipl_problem.pk)

        # problem is now base Problem class
        assert type(problem).__name__ == "Problem"

        # get_real_instance() should recover the subclass
        real = problem.get_real_instance()
        assert isinstance(real, EiplProblem)
        assert real.function_name == "fibonacci"
