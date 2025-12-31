"""
Integration tests for polymorphic behavior in grading pipeline.

The grading pipeline is the most critical path where polymorphism must work:
1. Submission created with Problem FK
2. GradingService accesses submission.problem.problem_type
3. Handler dispatched based on problem_type
4. Handler accesses subclass-specific fields

If polymorphism fails anywhere in this chain, grading breaks.
"""

import pytest
from django.contrib.auth import get_user_model

from purplex.problems_app.handlers import get_handler, is_registered
from purplex.problems_app.models import (
    EiplProblem,
    McqProblem,
    ProblemSet,
    PromptProblem,
)
from purplex.submissions.grading_service import GradingService
from purplex.submissions.models import Submission
from purplex.users_app.models import UserProfile

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def grading_user(db):
    """User for grading tests."""
    user = User.objects.create_user(
        username="grading_test_user",
        email="grading_test@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="grading-test-uid")
    return user


@pytest.fixture
def grading_problem_set(db):
    """Problem set for grading tests."""
    return ProblemSet.objects.create(
        slug="grading-test-ps",
        title="Grading Test Set",
    )


@pytest.fixture
def grading_eipl(db):
    """EiPL problem for grading."""
    return EiplProblem.objects.create(
        slug="grading-eipl",
        title="Grading EiPL",
        reference_solution="def add(a, b):\n    return a + b",
        function_signature="def add(a: int, b: int) -> int",
        function_name="add",
        segmentation_threshold=2,
        requires_highlevel_comprehension=True,
    )


@pytest.fixture
def grading_mcq(db):
    """MCQ problem for grading."""
    return McqProblem.objects.create(
        slug="grading-mcq",
        title="Grading MCQ",
        question_text="What is 2+2?",
        options=[
            {"id": "a", "text": "3", "is_correct": False},
            {"id": "b", "text": "4", "is_correct": True},
        ],
    )


@pytest.fixture
def grading_prompt(db):
    """Prompt problem for grading."""
    return PromptProblem.objects.create(
        slug="grading-prompt",
        title="Grading Prompt",
        reference_solution='def analyze():\n    return "data"',
        function_signature="def analyze() -> str",
        function_name="analyze",
        image_url="https://example.com/test.png",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Handler Registry Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandlerRegistryPolymorphism:
    """
    Tests for handler dispatch based on polymorphic problem_type.
    """

    def test_eipl_type_is_registered(self):
        """eipl type should be registered in handler registry."""
        assert is_registered("eipl")

    def test_mcq_type_is_registered(self):
        """mcq type should be registered in handler registry."""
        assert is_registered("mcq")

    def test_prompt_type_is_registered(self):
        """prompt type should be registered in handler registry."""
        assert is_registered("prompt")

    def test_get_handler_for_eipl(self, grading_eipl):
        """Handler lookup with problem_type should work."""
        handler = get_handler(grading_eipl.problem_type)
        assert handler is not None
        assert handler.type_name == "eipl"

    def test_get_handler_for_mcq(self, grading_mcq):
        """Handler lookup with problem_type should work."""
        handler = get_handler(grading_mcq.problem_type)
        assert handler is not None
        assert handler.type_name == "mcq"

    def test_get_handler_for_prompt(self, grading_prompt):
        """Handler lookup with problem_type should work."""
        handler = get_handler(grading_prompt.problem_type)
        assert handler is not None
        assert handler.type_name == "prompt"

    def test_handler_dispatch_after_fk_traversal(
        self, grading_user, grading_eipl, grading_problem_set
    ):
        """
        Handler should be correctly dispatched after FK traversal.

        This is the critical test - simulates grading pipeline.
        """
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="test",
            submission_type="eipl",
        )

        # Refetch to test FK traversal
        submission = Submission.objects.get(pk=submission.pk)

        # This is what GradingService does
        problem_type = submission.problem.problem_type
        handler = get_handler(problem_type)

        assert handler is not None
        assert handler.type_name == "eipl"


# ─────────────────────────────────────────────────────────────────────────────
# Grading Service Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestGradingServicePolymorphism:
    """
    Tests for GradingService with polymorphic problems.

    GradingService.calculate_grade() accesses submission.problem.problem_type
    to dispatch to the correct handler.
    """

    def test_calculate_grade_eipl_correct_submission(
        self, grading_user, grading_eipl, grading_problem_set
    ):
        """GradingService should correctly grade EiPL submission."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="The add function adds two numbers",
            submission_type="eipl",
            passed_all_tests=True,
            is_correct=True,
        )

        # Refetch
        submission = Submission.objects.get(pk=submission.pk)

        # GradingService should dispatch to EiPL handler
        grade = GradingService.calculate_grade(submission)

        assert grade in ["complete", "partial", "incomplete"]

    def test_calculate_grade_mcq_correct_answer(
        self, grading_user, grading_mcq, grading_problem_set
    ):
        """GradingService should correctly grade MCQ submission."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_mcq,
            problem_set=grading_problem_set,
            raw_input="b",  # Correct answer
            submission_type="mcq",
            passed_all_tests=True,
            is_correct=True,
        )

        submission = Submission.objects.get(pk=submission.pk)

        grade = GradingService.calculate_grade(submission)
        assert grade == "complete"

    def test_calculate_grade_mcq_incorrect_answer(
        self, grading_user, grading_mcq, grading_problem_set
    ):
        """Incorrect MCQ submission should be incomplete."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_mcq,
            problem_set=grading_problem_set,
            raw_input="a",  # Wrong answer
            submission_type="mcq",
            passed_all_tests=False,
            is_correct=False,
        )

        submission = Submission.objects.get(pk=submission.pk)

        grade = GradingService.calculate_grade(submission)
        assert grade == "incomplete"

    def test_is_correct_eipl(self, grading_user, grading_eipl, grading_problem_set):
        """is_correct should work with EiPL submissions."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="test",
            submission_type="eipl",
            passed_all_tests=True,
            is_correct=True,
        )

        submission = Submission.objects.get(pk=submission.pk)

        result = GradingService.is_correct(submission)
        assert result is True

    def test_is_correct_mcq(self, grading_user, grading_mcq, grading_problem_set):
        """is_correct should work with MCQ submissions."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_mcq,
            problem_set=grading_problem_set,
            raw_input="b",
            submission_type="mcq",
            passed_all_tests=True,
            is_correct=True,
        )

        submission = Submission.objects.get(pk=submission.pk)

        result = GradingService.is_correct(submission)
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Handler Field Access Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandlerFieldAccessAfterDispatch:
    """
    Tests that handlers can access subclass-specific fields after dispatch.

    This verifies the complete chain:
    FK traversal -> problem_type -> handler -> subclass field access
    """

    def test_eipl_handler_can_access_function_name(
        self, grading_user, grading_eipl, grading_problem_set
    ):
        """EiPL handler should access function_name for code generation."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="test",
            submission_type="eipl",
        )

        submission = Submission.objects.get(pk=submission.pk)
        problem = submission.problem

        # Handler would access these
        assert problem.function_name == "add"
        assert problem.function_signature == "def add(a: int, b: int) -> int"

    def test_eipl_handler_can_access_segmentation_config(
        self, grading_user, grading_eipl, grading_problem_set
    ):
        """EiPL handler should access segmentation config."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="test",
            submission_type="eipl",
        )

        submission = Submission.objects.get(pk=submission.pk)
        problem = submission.problem

        # Handler needs these for segmentation analysis
        assert problem.segmentation_enabled is True
        assert problem.segmentation_threshold == 2
        assert problem.requires_highlevel_comprehension is True

    def test_mcq_handler_can_access_options(
        self, grading_user, grading_mcq, grading_problem_set
    ):
        """MCQ handler should access options for grading."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_mcq,
            problem_set=grading_problem_set,
            raw_input="b",
            submission_type="mcq",
        )

        submission = Submission.objects.get(pk=submission.pk)
        problem = submission.problem

        # Handler needs options to grade
        assert len(problem.options) == 2
        correct = next(o for o in problem.options if o["is_correct"])
        assert correct["id"] == "b"

    def test_prompt_handler_can_access_image_url(
        self, grading_user, grading_prompt, grading_problem_set
    ):
        """Prompt handler should access image_url."""
        submission = Submission.objects.create(
            user=grading_user,
            problem=grading_prompt,
            problem_set=grading_problem_set,
            raw_input="test",
            submission_type="prompt",
        )

        submission = Submission.objects.get(pk=submission.pk)
        problem = submission.problem

        # Handler might include image in response
        assert problem.image_url == "https://example.com/test.png"


# ─────────────────────────────────────────────────────────────────────────────
# Mixed Problem Type Pipeline Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMixedProblemTypeGrading:
    """
    Tests for grading submissions of mixed problem types.

    Simulates a problem set with EiPL, MCQ, and Prompt problems
    being graded in sequence.
    """

    def test_grade_mixed_submissions_in_sequence(
        self,
        grading_user,
        grading_problem_set,
        grading_eipl,
        grading_mcq,
        grading_prompt,
    ):
        """
        Grade submissions for different problem types sequentially.

        This simulates a student working through a mixed problem set.
        """
        # Create submissions for each type
        submissions = [
            Submission.objects.create(
                user=grading_user,
                problem=grading_eipl,
                problem_set=grading_problem_set,
                raw_input="eipl answer",
                submission_type="eipl",
                passed_all_tests=True,
                is_correct=True,
            ),
            Submission.objects.create(
                user=grading_user,
                problem=grading_mcq,
                problem_set=grading_problem_set,
                raw_input="b",
                submission_type="mcq",
                passed_all_tests=True,
                is_correct=True,
            ),
            Submission.objects.create(
                user=grading_user,
                problem=grading_prompt,
                problem_set=grading_problem_set,
                raw_input="prompt answer",
                submission_type="prompt",
                passed_all_tests=True,
                is_correct=True,
            ),
        ]

        # Refetch and grade each
        grades = []
        for sub_id in [s.pk for s in submissions]:
            submission = Submission.objects.get(pk=sub_id)

            # Verify correct problem type resolution
            expected_type = submission.submission_type
            actual_type = submission.problem.problem_type
            assert actual_type == expected_type

            # Grade should work
            grade = GradingService.calculate_grade(submission)
            grades.append(grade)

        # All should have valid grades
        assert all(g in ["complete", "partial", "incomplete"] for g in grades)

    def test_filter_and_grade_by_problem_type(
        self, grading_user, grading_problem_set, grading_eipl, grading_mcq
    ):
        """Filter submissions by type and grade."""
        # Create mixed submissions
        Submission.objects.create(
            user=grading_user,
            problem=grading_eipl,
            problem_set=grading_problem_set,
            raw_input="eipl",
            submission_type="eipl",
        )
        Submission.objects.create(
            user=grading_user,
            problem=grading_mcq,
            problem_set=grading_problem_set,
            raw_input="b",
            submission_type="mcq",
            passed_all_tests=True,
            is_correct=True,
        )

        # Filter MCQ submissions only
        mcq_submissions = Submission.objects.filter(
            user=grading_user,
            submission_type="mcq",
        )

        for sub in mcq_submissions:
            # Problem should be McqProblem
            assert isinstance(sub.problem, McqProblem)

            # Grading should work
            grade = GradingService.calculate_grade(sub)
            assert grade in ["complete", "partial", "incomplete"]
