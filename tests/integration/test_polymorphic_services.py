"""
Integration tests for polymorphic behavior in services and repositories.

These tests ensure that services and repositories properly handle
polymorphic Problem model instances throughout the data access layer.

Critical paths tested:
- ProblemSetMembershipRepository.get_problem_set_memberships_with_categories()
- ProgressService progress tracking with polymorphic problems
- InstructorAnalyticsService analytics with mixed problem types
- Submission flow through grading service
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    EiplProblem,
    McqProblem,
    ProblemSet,
    ProblemSetMembership,
    PromptProblem,
    UserProgress,
)
from purplex.problems_app.repositories.problem_set_membership_repository import (
    ProblemSetMembershipRepository,
)
from purplex.problems_app.repositories.user_progress_repository import (
    UserProgressRepository,
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
def service_test_user(db):
    """Test user for service tests."""
    user = User.objects.create_user(
        username="service_test_user",
        email="service_test@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(user=user, firebase_uid="service-test-firebase-uid")
    return user


@pytest.fixture
def instructor_user(db):
    """Instructor user for courses."""
    user = User.objects.create_user(
        username="service_instructor",
        email="service_instructor@example.com",
        password="testpass123",  # pragma: allowlist secret
    )
    UserProfile.objects.create(
        user=user, firebase_uid="service-instructor-firebase-uid"
    )
    return user


@pytest.fixture
def service_problem_set(db):
    """Problem set for service tests."""
    return ProblemSet.objects.create(
        slug="service-test-ps",
        title="Service Test Problem Set",
    )


@pytest.fixture
def service_course(db, instructor_user, service_problem_set):
    """Course for service tests."""
    course = Course.objects.create(
        course_id="SERVICE-TEST-101",
        name="Service Test Course",
        instructor=instructor_user,
    )
    course.problem_sets.add(service_problem_set)
    return course


@pytest.fixture
def service_eipl(db):
    """EiPL problem for service tests."""
    return EiplProblem.objects.create(
        slug="service-eipl-1",
        title="Service EiPL 1",
        reference_solution="def add(a, b):\n    return a + b",
        function_signature="def add(a: int, b: int) -> int",
        function_name="add",
        segmentation_threshold=2,
        requires_highlevel_comprehension=True,
    )


@pytest.fixture
def service_mcq(db):
    """MCQ problem for service tests."""
    return McqProblem.objects.create(
        slug="service-mcq-1",
        title="Service MCQ 1",
        question_text="What is 2 + 2?",
        options=[
            {"id": "a", "text": "3", "is_correct": False},
            {"id": "b", "text": "4", "is_correct": True},
            {"id": "c", "text": "5", "is_correct": False},
        ],
        allow_multiple=False,
    )


@pytest.fixture
def service_prompt(db):
    """Prompt problem for service tests."""
    return PromptProblem.objects.create(
        slug="service-prompt-1",
        title="Service Prompt 1",
        reference_solution='def describe():\n    return "flowchart"',
        function_signature="def describe() -> str",
        function_name="describe",
        image_url="https://example.com/flowchart.png",
        image_alt_text="Flowchart diagram",
    )


@pytest.fixture
def populated_problem_set(
    db, service_problem_set, service_eipl, service_mcq, service_prompt
):
    """Problem set populated with all problem types."""
    ProblemSetMembership.objects.create(
        problem_set=service_problem_set, problem=service_eipl, order=0
    )
    ProblemSetMembership.objects.create(
        problem_set=service_problem_set, problem=service_mcq, order=1
    )
    ProblemSetMembership.objects.create(
        problem_set=service_problem_set, problem=service_prompt, order=2
    )
    return service_problem_set


@pytest.fixture
def enrolled_user(db, service_test_user, service_course):
    """User enrolled in course."""
    CourseEnrollment.objects.create(
        user=service_test_user,
        course=service_course,
        is_active=True,
    )
    return service_test_user


# ─────────────────────────────────────────────────────────────────────────────
# ProblemSetMembershipRepository Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProblemSetMembershipRepository:
    """
    Tests for ProblemSetMembershipRepository polymorphic handling.

    Critical: get_problem_set_memberships_with_categories() must return
    correct subclass instances for handler config access.
    """

    def test_get_memberships_returns_correct_subclass_types(
        self, populated_problem_set
    ):
        """
        Repository should return correct Problem subclass instances.

        This is critical for the frontend problem listing and
        handler configuration access.
        """
        result = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        assert len(result) == 3

        # Check problem_obj field (the actual model instance)
        types = [type(r["problem_obj"]).__name__ for r in result]
        assert "EiplProblem" in types
        assert "McqProblem" in types
        assert "PromptProblem" in types

    def test_get_memberships_eipl_fields_accessible(self, populated_problem_set):
        """EiPL-specific fields should be accessible from repository result."""
        result = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        eipl_result = next(r for r in result if r["problem"]["problem_type"] == "eipl")

        # problem_obj should be actual EiplProblem instance
        assert isinstance(eipl_result["problem_obj"], EiplProblem)

        # Subclass fields should be accessible
        assert eipl_result["problem_obj"].function_name == "add"
        assert eipl_result["problem_obj"].segmentation_enabled is True

        # Also in serialized data
        assert eipl_result["problem"]["function_name"] == "add"
        assert eipl_result["problem"]["segmentation_enabled"] is True

    def test_get_memberships_mcq_fields_accessible(self, populated_problem_set):
        """MCQ-specific fields should be accessible from repository result."""
        result = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        mcq_result = next(r for r in result if r["problem"]["problem_type"] == "mcq")

        assert isinstance(mcq_result["problem_obj"], McqProblem)
        assert len(mcq_result["problem_obj"].options) == 3
        assert mcq_result["problem_obj"].allow_multiple is False

    def test_get_memberships_prompt_fields_accessible(self, populated_problem_set):
        """Prompt-specific fields should be accessible from repository result."""
        result = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        prompt_result = next(
            r for r in result if r["problem"]["problem_type"] == "prompt"
        )

        assert isinstance(prompt_result["problem_obj"], PromptProblem)
        assert (
            prompt_result["problem_obj"].image_url
            == "https://example.com/flowchart.png"
        )

    def test_get_memberships_preserves_order(self, populated_problem_set):
        """Memberships should be returned in correct order."""
        result = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        orders = [r["order"] for r in result]
        assert orders == [0, 1, 2]

        # Order should match problem type order set in fixture
        assert result[0]["problem"]["problem_type"] == "eipl"
        assert result[1]["problem"]["problem_type"] == "mcq"
        assert result[2]["problem"]["problem_type"] == "prompt"


# ─────────────────────────────────────────────────────────────────────────────
# UserProgressRepository Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUserProgressRepositoryPolymorphism:
    """
    Tests for UserProgressRepository with polymorphic problems.

    UserProgress.problem FK must return correct subclass for
    progress display and handler logic.
    """

    def test_get_user_progress_returns_polymorphic_problem(
        self, service_test_user, service_eipl, service_problem_set, service_course
    ):
        """UserProgress.problem should be correct subclass."""
        UserProgress.objects.create(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            course=service_course,
            status="in_progress",
            best_score=50,
        )

        # Use repository method
        progress = UserProgressRepository.get_user_problem_progress(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            course=service_course,
        )

        assert progress is not None
        assert isinstance(progress.problem, EiplProblem)
        assert progress.problem.function_name == "add"

    def test_get_progress_in_problem_set_returns_polymorphic(
        self,
        service_test_user,
        populated_problem_set,
        service_course,
        service_eipl,
        service_mcq,
        service_prompt,
    ):
        """All progress records should have polymorphic problems."""
        # Create progress for each problem type
        for problem in [service_eipl, service_mcq, service_prompt]:
            UserProgress.objects.create(
                user=service_test_user,
                problem=problem,
                problem_set=populated_problem_set,
                course=service_course,
            )

        progress_list = UserProgressRepository.get_user_progress_in_problem_set(
            user=service_test_user,
            problem_set=populated_problem_set,
            course=service_course,
        )

        assert len(progress_list) == 3

        # Each should have correct subclass
        types = {type(p.problem).__name__ for p in progress_list}
        assert types == {"EiplProblem", "McqProblem", "PromptProblem"}

    def test_get_or_create_preserves_polymorphism(
        self, service_test_user, service_mcq, service_problem_set
    ):
        """get_or_create should work with polymorphic problems."""
        progress, created = UserProgressRepository.get_or_create_progress(
            user=service_test_user,
            problem=service_mcq,
            problem_set=service_problem_set,
        )

        assert created
        assert isinstance(progress.problem, McqProblem)
        assert len(progress.problem.options) == 3

        # Second call should not create
        progress2, created2 = UserProgressRepository.get_or_create_progress(
            user=service_test_user,
            problem=service_mcq,
            problem_set=service_problem_set,
        )

        assert not created2
        assert progress.pk == progress2.pk


# ─────────────────────────────────────────────────────────────────────────────
# Submission Repository Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubmissionPolymorphism:
    """
    Tests for Submission model with polymorphic problems.

    The Submission -> Problem FK is the most critical path for
    handler operation.
    """

    def test_submission_queryset_returns_polymorphic_problems(
        self,
        service_test_user,
        service_problem_set,
        service_eipl,
        service_mcq,
        service_prompt,
    ):
        """Queryset of submissions should have polymorphic problems."""
        # Create submissions for each type
        Submission.objects.create(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            raw_input="test eipl",
            submission_type="eipl",
        )
        Submission.objects.create(
            user=service_test_user,
            problem=service_mcq,
            problem_set=service_problem_set,
            raw_input="b",
            submission_type="mcq",
        )
        Submission.objects.create(
            user=service_test_user,
            problem=service_prompt,
            problem_set=service_problem_set,
            raw_input="test prompt",
            submission_type="prompt",
        )

        # Query all submissions
        submissions = list(
            Submission.objects.filter(user=service_test_user).select_related(
                "user", "problem_set"
            )  # Note: NOT 'problem'
        )

        assert len(submissions) == 3

        # Verify each has correct problem type
        for sub in submissions:
            if sub.submission_type == "eipl":
                assert isinstance(sub.problem, EiplProblem)
                assert sub.problem.function_name == "add"
            elif sub.submission_type == "mcq":
                assert isinstance(sub.problem, McqProblem)
                assert len(sub.problem.options) == 3
            elif sub.submission_type == "prompt":
                assert isinstance(sub.problem, PromptProblem)
                assert sub.problem.image_url == "https://example.com/flowchart.png"

    def test_submission_recent_filter_preserves_polymorphism(
        self, service_test_user, service_eipl, service_problem_set
    ):
        """Filtered querysets should preserve polymorphic resolution."""
        Submission.objects.create(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            raw_input="test",
            submission_type="eipl",
            submitted_at=timezone.now(),
        )

        # Filter by recent
        recent = Submission.objects.filter(
            submitted_at__gte=timezone.now() - timedelta(hours=1)
        )

        for submission in recent:
            assert isinstance(submission.problem, EiplProblem)


# ─────────────────────────────────────────────────────────────────────────────
# Cross-Module Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCrossModulePolymorphism:
    """
    Tests for polymorphic behavior across module boundaries.

    These tests verify that polymorphic resolution works when
    data flows between repositories, services, and views.
    """

    def test_problem_set_to_progress_polymorphism(
        self,
        service_test_user,
        populated_problem_set,
        service_course,
        service_eipl,
        service_mcq,
        service_prompt,
    ):
        """
        Test flow: ProblemSet -> Membership -> Problem -> Progress

        This mimics the student dashboard flow.
        """
        # Get problem set memberships (as API would)
        memberships = (
            ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(
                populated_problem_set
            )
        )

        # Create progress for each (as student starts problems)
        for m in memberships:
            UserProgress.objects.create(
                user=service_test_user,
                problem=m["problem_obj"],
                problem_set=populated_problem_set,
                course=service_course,
                status="in_progress",
            )

        # Fetch progress back (as dashboard would)
        progress_list = UserProgressRepository.get_user_progress_in_problem_set(
            user=service_test_user,
            problem_set=populated_problem_set,
            course=service_course,
        )

        # All should have correct polymorphic types
        for progress in progress_list:
            problem_type = progress.problem.problem_type

            if problem_type == "eipl":
                assert hasattr(progress.problem, "function_name")
                assert hasattr(progress.problem, "segmentation_enabled")
            elif problem_type == "mcq":
                assert hasattr(progress.problem, "options")
                assert hasattr(progress.problem, "allow_multiple")
            elif problem_type == "prompt":
                assert hasattr(progress.problem, "image_url")

    def test_submission_to_progress_update_polymorphism(
        self, service_test_user, service_eipl, service_problem_set, service_course
    ):
        """
        Test flow: Submission -> Progress Update

        This mimics the grading pipeline flow.
        """
        # Create initial progress
        progress, _ = UserProgressRepository.get_or_create_progress(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            course=service_course,
        )

        # Create submission
        submission = Submission.objects.create(
            user=service_test_user,
            problem=service_eipl,
            problem_set=service_problem_set,
            course=service_course,
            raw_input="The add function adds two numbers",
            submission_type="eipl",
            score=100,
            is_correct=True,
        )

        # Verify submission has polymorphic problem
        submission_refetched = Submission.objects.get(pk=submission.pk)
        assert isinstance(submission_refetched.problem, EiplProblem)

        # Verify progress update would have access to problem fields
        progress_refetched = UserProgress.objects.get(pk=progress.pk)
        assert isinstance(progress_refetched.problem, EiplProblem)

        # Handler would need these for segmentation
        assert progress_refetched.problem.segmentation_enabled is True
        assert progress_refetched.problem.segmentation_threshold == 2
