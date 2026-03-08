"""
Unit tests for supporting models (ProblemSet, Course, TestCase, Submission).

Tests the model definitions themselves:
- Field validation and defaults
- Custom save() methods
- Custom clean() methods
- Custom methods (soft_delete, increment_version)
- __str__ representations
- Model constraints
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from purplex.problems_app.models import (
    Course,
    EiplProblem,
    McqProblem,
    ProblemSet,
    ProblemSetMembership,
    TestCase,
)
from purplex.submissions.models import Submission

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def model_instructor(db):
    """Instructor user for model tests."""
    return User.objects.create_user(
        username="model_instructor",
        email="instructor@test.com",
        password="testpass123",  # pragma: allowlist secret
    )


@pytest.fixture
def model_user(db):
    """Regular user for model tests."""
    return User.objects.create_user(
        username="model_user",
        email="user@test.com",
        password="testpass123",  # pragma: allowlist secret
    )


@pytest.fixture
def model_problem(db):
    """Problem for model tests."""
    return EiplProblem.objects.create(
        slug="model-test-eipl",
        title="Model Test EiPL",
        reference_solution="def x(): pass",
        function_signature="def x() -> None",
    )


@pytest.fixture
def model_problem_set(db):
    """Problem set for model tests."""
    return ProblemSet.objects.create(
        slug="model-test-ps",
        title="Model Test Set",
    )


@pytest.fixture
def model_course(db, model_instructor, model_problem_set):
    """Course for model tests."""
    from purplex.problems_app.models import CourseInstructor

    course = Course.objects.create(
        course_id="MODEL-TEST-101",
        name="Model Test Course",
    )
    course.problem_sets.add(model_problem_set)
    CourseInstructor.objects.create(
        course=course, user=model_instructor, role="primary"
    )
    return course


# ─────────────────────────────────────────────────────────────────────────────
# ProblemSet Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProblemSetFieldDefaults:
    """Tests for ProblemSet field defaults."""

    def test_description_defaults_to_empty_string(self, db):
        """Default description should be empty string."""
        ps = ProblemSet.objects.create(title="Test Set")
        assert ps.description == ""

    def test_is_public_defaults_to_true(self, db):
        """Default is_public should be True."""
        ps = ProblemSet.objects.create(title="Test Set")
        assert ps.is_public is True

    def test_version_defaults_to_one(self, db):
        """Default version should be 1."""
        ps = ProblemSet.objects.create(title="Test Set")
        assert ps.version == 1

    def test_created_by_can_be_null(self, db):
        """created_by should allow null."""
        ps = ProblemSet.objects.create(title="Test Set")
        assert ps.created_by is None


@pytest.mark.django_db
class TestProblemSetSlugAutoGeneration:
    """Tests for ProblemSet.save() auto-slug generation."""

    def test_auto_generates_slug_from_title(self, db):
        """save() should auto-generate slug from title."""
        ps = ProblemSet.objects.create(title="My Problem Set")
        assert ps.slug == "my-problem-set"

    def test_explicit_slug_preserved(self, db):
        """Explicitly provided slug should not be overwritten."""
        ps = ProblemSet.objects.create(
            slug="explicit-slug",
            title="Different Title",
        )
        assert ps.slug == "explicit-slug"

    def test_slug_unique_constraint(self, db):
        """Duplicate slugs should raise IntegrityError."""
        ProblemSet.objects.create(slug="unique-ps", title="First")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemSet.objects.create(slug="unique-ps", title="Second")


@pytest.mark.django_db
class TestProblemSetProblemsCount:
    """Tests for ProblemSet.problems_count property."""

    def test_problems_count_zero_initially(self, model_problem_set):
        """problems_count should be 0 for empty set."""
        assert model_problem_set.problems_count == 0

    def test_problems_count_with_members(self, model_problem_set, model_problem):
        """problems_count should count problems in set."""
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set,
            problem=model_problem,
            order=0,
        )
        assert model_problem_set.problems_count == 1


@pytest.mark.django_db
class TestProblemSetIncrementVersion:
    """Tests for ProblemSet.increment_version() method."""

    def test_increments_version(self, model_problem_set):
        """increment_version should increase version by 1."""
        original_version = model_problem_set.version
        model_problem_set.increment_version()
        model_problem_set.refresh_from_db()
        assert model_problem_set.version == original_version + 1

    def test_multiple_increments(self, model_problem_set):
        """Multiple increment_version calls should each add 1."""
        model_problem_set.increment_version()
        model_problem_set.refresh_from_db()
        v1 = model_problem_set.version

        model_problem_set.increment_version()
        model_problem_set.refresh_from_db()
        v2 = model_problem_set.version

        assert v2 == v1 + 1

    def test_uses_f_expression_for_atomicity(self, model_problem_set):
        """increment_version uses F() expression (atomic at DB level)."""
        # This test documents that increment_version uses F() expression
        # which prevents race conditions at the database level
        original = model_problem_set.version
        model_problem_set.increment_version()

        # After increment, the in-memory version is an F() expression
        # until refresh_from_db() is called
        model_problem_set.refresh_from_db()
        assert model_problem_set.version == original + 1


@pytest.mark.django_db
class TestProblemSetMembershipVersionInteraction:
    """Tests for ProblemSet version interaction with membership changes."""

    def test_adding_problem_should_bump_version(self, model_problem_set, model_problem):
        """
        Document: Adding a problem to a set SHOULD bump version.

        Note: This is typically done in the view/service layer, not automatically.
        This test documents expected behavior.
        """
        original_version = model_problem_set.version

        # Add problem
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set,
            problem=model_problem,
            order=0,
        )

        # Version is NOT automatically bumped by membership creation
        # This is by design - version bumping should be explicit
        model_problem_set.refresh_from_db()
        assert model_problem_set.version == original_version

        # Service layer should call this:
        model_problem_set.increment_version()
        model_problem_set.refresh_from_db()
        assert model_problem_set.version == original_version + 1


@pytest.mark.django_db
class TestProblemSetStr:
    """Tests for ProblemSet.__str__()."""

    def test_str_returns_title(self, db):
        """__str__ should return the title."""
        ps = ProblemSet.objects.create(title="My Problem Set")
        assert str(ps) == "My Problem Set"


# ─────────────────────────────────────────────────────────────────────────────
# ProblemSetMembership Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProblemSetMembershipConstraints:
    """Tests for ProblemSetMembership constraints."""

    def test_unique_problem_in_set(self, model_problem_set, model_problem):
        """Same problem cannot be in same set twice."""
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set,
            problem=model_problem,
            order=0,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemSetMembership.objects.create(
                    problem_set=model_problem_set,
                    problem=model_problem,
                    order=1,
                )

    def test_same_problem_different_sets_allowed(self, model_problem):
        """Same problem can be in different sets."""
        ps1 = ProblemSet.objects.create(title="Set 1")
        ps2 = ProblemSet.objects.create(title="Set 2")

        ProblemSetMembership.objects.create(
            problem_set=ps1,
            problem=model_problem,
            order=0,
        )
        # Should not raise
        ProblemSetMembership.objects.create(
            problem_set=ps2,
            problem=model_problem,
            order=0,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Course Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCourseFieldDefaults:
    """Tests for Course field defaults."""

    def test_is_active_defaults_to_true(self, model_instructor):
        """Default is_active should be True."""
        course = Course.objects.create(
            course_id="TEST-101",
            name="Test Course",
        )
        assert course.is_active is True

    def test_enrollment_open_defaults_to_true(self, model_instructor):
        """Default enrollment_open should be True."""
        course = Course.objects.create(
            course_id="TEST-101",
            name="Test Course",
        )
        assert course.enrollment_open is True

    def test_is_deleted_defaults_to_false(self, model_instructor):
        """Default is_deleted should be False."""
        course = Course.objects.create(
            course_id="TEST-101",
            name="Test Course",
        )
        assert course.is_deleted is False


@pytest.mark.django_db
class TestCourseSlugAutoGeneration:
    """Tests for Course.save() auto-slug generation."""

    def test_auto_generates_slug_from_course_id(self, model_instructor):
        """save() should auto-generate slug from course_id."""
        course = Course.objects.create(
            course_id="CS101-FALL2024",
            name="Intro to CS",
        )
        assert course.slug == "cs101-fall2024"

    def test_explicit_slug_preserved(self, model_instructor):
        """Explicitly provided slug should not be overwritten."""
        course = Course.objects.create(
            course_id="CS101",
            slug="custom-slug",
            name="Test Course",
        )
        assert course.slug == "custom-slug"

    def test_course_id_unique(self, model_instructor):
        """course_id should be unique."""
        Course.objects.create(
            course_id="UNIQUE-101",
            name="First",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    course_id="UNIQUE-101",
                    name="Second",
                )


@pytest.mark.django_db
class TestCourseSoftDelete:
    """Tests for Course.soft_delete() method."""

    def test_soft_delete_sets_flags(self, model_course):
        """soft_delete should set is_deleted, is_active, enrollment_open."""
        model_course.soft_delete()
        model_course.refresh_from_db()

        assert model_course.is_deleted is True
        assert model_course.is_active is False
        assert model_course.enrollment_open is False
        assert model_course.deleted_at is not None

    def test_soft_delete_preserves_record(self, model_course):
        """soft_delete should not actually delete the record."""
        course_pk = model_course.pk
        model_course.soft_delete()
        # Should still exist (use all_objects since default manager excludes soft-deleted)
        assert Course.all_objects.filter(pk=course_pk).exists()


@pytest.mark.django_db
class TestCourseInstructorCascade:
    """Tests for CourseInstructor CASCADE behavior on user deletion."""

    def test_deleting_instructor_cascades_course_instructor(
        self, model_instructor, model_course
    ):
        """Deleting user should cascade-delete their CourseInstructor rows, not the course."""
        from purplex.problems_app.models import CourseInstructor

        assert CourseInstructor.objects.filter(
            user=model_instructor, course=model_course
        ).exists()
        course_pk = model_course.pk
        model_instructor.delete()
        # Course still exists, but instructor link is gone
        assert Course.objects.filter(pk=course_pk).exists()
        assert not CourseInstructor.objects.filter(
            user_id=model_instructor.pk, course=model_course
        ).exists()


@pytest.mark.django_db
class TestCourseStr:
    """Tests for Course.__str__()."""

    def test_str_format(self, model_instructor):
        """__str__ should be 'course_id - name'."""
        course = Course.objects.create(
            course_id="CS101",
            name="Intro to CS",
        )
        assert str(course) == "CS101 - Intro to CS"


# ─────────────────────────────────────────────────────────────────────────────
# TestCase Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTestCaseFieldDefaults:
    """Tests for TestCase field defaults."""

    def test_is_hidden_defaults_to_false(self, model_problem):
        """Default is_hidden should be False."""
        tc = TestCase.objects.create(
            problem=model_problem,
            inputs=[1, 2],
            expected_output=3,
            order=0,
        )
        assert tc.is_hidden is False

    def test_is_sample_defaults_to_false(self, model_problem):
        """Default is_sample should be False."""
        tc = TestCase.objects.create(
            problem=model_problem,
            inputs=[1, 2],
            expected_output=3,
            order=0,
        )
        assert tc.is_sample is False

    def test_order_defaults_to_zero(self, model_problem):
        """Default order should be 0."""
        tc = TestCase.objects.create(
            problem=model_problem,
            inputs=[1, 2],
            expected_output=3,
        )
        assert tc.order == 0


@pytest.mark.django_db
class TestTestCaseValidation:
    """Tests for TestCase.clean() validation."""

    def test_inputs_must_be_list(self, model_problem):
        """inputs must be a list."""
        tc = TestCase(
            problem=model_problem,
            inputs={"not": "a list"},  # Should be list
            expected_output=3,
        )
        with pytest.raises(ValidationError) as exc_info:
            tc.full_clean()
        assert (
            "inputs" in str(exc_info.value).lower()
            or "list" in str(exc_info.value).lower()
        )

    def test_inputs_as_list_is_valid(self, model_problem):
        """inputs as list should pass validation."""
        tc = TestCase(
            problem=model_problem,
            inputs=[1, 2, 3],
            expected_output=6,
        )
        tc.full_clean()  # Should not raise

    def test_empty_inputs_list_fails_validation(self, model_problem):
        """Empty inputs list is treated as blank and fails validation."""
        tc = TestCase(
            problem=model_problem,
            inputs=[],
            expected_output=0,
        )
        # Empty list is treated as blank=False violation
        with pytest.raises(ValidationError):
            tc.full_clean()


@pytest.mark.django_db
class TestTestCaseStr:
    """Tests for TestCase.__str__()."""

    def test_str_format(self, model_problem):
        """__str__ should include inputs and expected output."""
        tc = TestCase.objects.create(
            problem=model_problem,
            inputs=[1, 2],
            expected_output=3,
            order=0,
        )
        result = str(tc)
        assert "1" in result
        assert "2" in result
        assert "3" in result


# ─────────────────────────────────────────────────────────────────────────────
# Submission Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubmissionFieldDefaults:
    """Tests for Submission field defaults."""

    def test_execution_status_defaults_to_pending(
        self, model_user, model_problem, model_problem_set
    ):
        """Default execution_status should be 'pending'."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.execution_status == "pending"

    def test_score_defaults_to_zero(self, model_user, model_problem, model_problem_set):
        """Default score should be 0."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.score == 0

    def test_passed_all_tests_defaults_to_false(
        self, model_user, model_problem, model_problem_set
    ):
        """Default passed_all_tests should be False."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.passed_all_tests is False

    def test_completion_status_defaults_to_incomplete(
        self, model_user, model_problem, model_problem_set
    ):
        """Default completion_status should be 'incomplete'."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.completion_status == "incomplete"

    def test_is_correct_defaults_to_false(
        self, model_user, model_problem, model_problem_set
    ):
        """Default is_correct should be False."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.is_correct is False

    def test_comprehension_level_defaults_to_not_evaluated(
        self, model_user, model_problem, model_problem_set
    ):
        """Default comprehension_level should be 'not_evaluated'."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.comprehension_level == "not_evaluated"

    def test_submission_id_auto_generated(
        self, model_user, model_problem, model_problem_set
    ):
        """submission_id should be auto-generated UUID."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        assert sub.submission_id is not None
        assert isinstance(sub.submission_id, uuid.UUID)


@pytest.mark.django_db
class TestSubmissionTypeChoices:
    """Tests for Submission.submission_type choices."""

    def test_eipl_type_valid(self, model_user, model_problem, model_problem_set):
        """'eipl' should be valid submission type."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        sub.full_clean()

    def test_mcq_type_valid(self, model_user, model_problem_set):
        """'mcq' should be valid submission type."""
        mcq = McqProblem.objects.create(
            title="MCQ",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        sub = Submission.objects.create(
            user=model_user,
            problem=mcq,
            problem_set=model_problem_set,
            raw_input="a",
            submission_type="mcq",
        )
        sub.full_clean()

    def test_prompt_type_valid(self, model_user, model_problem_set):
        """'prompt' should be valid submission type."""
        from purplex.problems_app.models import PromptProblem

        prompt = PromptProblem.objects.create(
            title="Prompt",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        sub = Submission.objects.create(
            user=model_user,
            problem=prompt,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="prompt",
        )
        sub.full_clean()

    def test_invalid_submission_type_fails(
        self, model_user, model_problem, model_problem_set
    ):
        """Invalid submission type should fail validation."""
        sub = Submission(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="invalid_type",
        )
        with pytest.raises(ValidationError):
            sub.full_clean()


@pytest.mark.django_db
class TestSubmissionExecutionStatusChoices:
    """Tests for Submission.execution_status choices."""

    def test_pending_status_valid(self, model_user, model_problem, model_problem_set):
        """'pending' should be valid execution status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="pending",
        )
        sub.full_clean()

    def test_processing_status_valid(
        self, model_user, model_problem, model_problem_set
    ):
        """'processing' should be valid execution status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="processing",
        )
        sub.full_clean()

    def test_completed_status_valid(self, model_user, model_problem, model_problem_set):
        """'completed' should be valid execution status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="completed",
        )
        sub.full_clean()

    def test_failed_status_valid(self, model_user, model_problem, model_problem_set):
        """'failed' should be valid execution status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="failed",
        )
        sub.full_clean()

    def test_timeout_status_valid(self, model_user, model_problem, model_problem_set):
        """'timeout' should be valid execution status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="timeout",
        )
        sub.full_clean()

    def test_invalid_execution_status_fails(
        self, model_user, model_problem, model_problem_set
    ):
        """Invalid execution status should fail validation."""
        sub = Submission(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            execution_status="invalid_status",
        )
        with pytest.raises(ValidationError):
            sub.full_clean()


@pytest.mark.django_db
class TestSubmissionCompletionStatusChoices:
    """Tests for Submission.completion_status choices."""

    def test_incomplete_status_valid(
        self, model_user, model_problem, model_problem_set
    ):
        """'incomplete' should be valid completion status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            completion_status="incomplete",
        )
        sub.full_clean()

    def test_partial_status_valid(self, model_user, model_problem, model_problem_set):
        """'partial' should be valid completion status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            completion_status="partial",
        )
        sub.full_clean()

    def test_complete_status_valid(self, model_user, model_problem, model_problem_set):
        """'complete' should be valid completion status."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            completion_status="complete",
        )
        sub.full_clean()

    def test_invalid_completion_status_fails(
        self, model_user, model_problem, model_problem_set
    ):
        """Invalid completion status should fail validation."""
        sub = Submission(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            completion_status="invalid_status",
        )
        with pytest.raises(ValidationError):
            sub.full_clean()


@pytest.mark.django_db
class TestSubmissionComprehensionLevelChoices:
    """Tests for Submission.comprehension_level choices."""

    def test_high_level_valid(self, model_user, model_problem, model_problem_set):
        """'high-level' should be valid comprehension level."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            comprehension_level="high-level",
        )
        sub.full_clean()

    def test_low_level_valid(self, model_user, model_problem, model_problem_set):
        """'low-level' should be valid comprehension level."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            comprehension_level="low-level",
        )
        sub.full_clean()

    def test_not_evaluated_valid(self, model_user, model_problem, model_problem_set):
        """'not_evaluated' should be valid comprehension level."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            comprehension_level="not_evaluated",
        )
        sub.full_clean()

    def test_invalid_comprehension_level_fails(
        self, model_user, model_problem, model_problem_set
    ):
        """Invalid comprehension level should fail validation."""
        sub = Submission(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            comprehension_level="invalid_level",
        )
        with pytest.raises(ValidationError):
            sub.full_clean()


@pytest.mark.django_db
class TestSubmissionProtectedFKs:
    """Tests for Submission PROTECTED FK behavior."""

    def test_cannot_delete_problem_with_submissions(
        self, model_user, model_problem, model_problem_set
    ):
        """Deleting problem with submissions should raise ProtectedError."""
        Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        with pytest.raises(ProtectedError):
            model_problem.delete()

    def test_cannot_delete_problem_set_with_submissions(
        self, model_user, model_problem, model_problem_set
    ):
        """Deleting problem set with submissions should raise ProtectedError."""
        Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        with pytest.raises(ProtectedError):
            model_problem_set.delete()

    def test_user_deletion_sets_null(
        self, model_user, model_problem, model_problem_set
    ):
        """Deleting user should set submission.user to NULL."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        model_user.delete()
        sub.refresh_from_db()
        assert sub.user is None


@pytest.mark.django_db
class TestSubmissionCeleryTaskIdUnique:
    """Tests for Submission.celery_task_id unique constraint."""

    def test_celery_task_id_unique(self, model_user, model_problem, model_problem_set):
        """Duplicate celery_task_id should raise IntegrityError."""
        Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
            celery_task_id="unique-task-id",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Submission.objects.create(
                    user=model_user,
                    problem=model_problem,
                    problem_set=model_problem_set,
                    raw_input="test2",
                    submission_type="eipl",
                    celery_task_id="unique-task-id",
                )

    def test_null_celery_task_ids_allowed(
        self, model_user, model_problem, model_problem_set
    ):
        """Multiple null celery_task_ids should be allowed."""
        Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test1",
            submission_type="eipl",
            celery_task_id=None,
        )
        # Should not raise
        Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test2",
            submission_type="eipl",
            celery_task_id=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Error Message Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestValidationErrorMessages:
    """Tests that validation errors have meaningful, specific messages."""

    def test_mcq_options_error_specifies_field(self, db):
        """MCQ validation error should specify 'options' field."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[{"id": "a", "text": "Only one", "is_correct": True}],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        # Error should be attached to 'options' field
        assert "options" in exc_info.value.message_dict

    def test_mcq_option_index_in_error_message(self, db):
        """MCQ validation error should identify which option has the problem."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "Good", "is_correct": True},
                {"id": "b", "is_correct": False},  # Missing text - option 2
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        error_msg = str(exc_info.value)
        # Should mention option 2 (1-indexed in error messages)
        assert "2" in error_msg

    def test_eipl_reference_solution_error_specifies_field(self, db):
        """EiPL validation error should specify 'reference_solution' field."""
        eipl = EiplProblem(
            title="Test",
            function_signature="def x() -> None",
        )
        with pytest.raises(ValidationError) as exc_info:
            eipl.full_clean()
        assert "reference_solution" in exc_info.value.message_dict

    def test_course_requires_course_id(self, db):
        """Course without course_id should have clear error."""
        course = Course(name="Test Course")
        with pytest.raises(ValidationError) as exc_info:
            course.full_clean()
        assert "course_id" in exc_info.value.message_dict


# ─────────────────────────────────────────────────────────────────────────────
# Cross-Model Relationship Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCrossModelRelationships:
    """Tests for relationships between models."""

    def test_problem_can_be_in_multiple_sets(self, model_problem):
        """Same problem can belong to multiple problem sets."""
        ps1 = ProblemSet.objects.create(title="Set 1")
        ps2 = ProblemSet.objects.create(title="Set 2")
        ps3 = ProblemSet.objects.create(title="Set 3")

        ProblemSetMembership.objects.create(
            problem_set=ps1, problem=model_problem, order=0
        )
        ProblemSetMembership.objects.create(
            problem_set=ps2, problem=model_problem, order=0
        )
        ProblemSetMembership.objects.create(
            problem_set=ps3, problem=model_problem, order=0
        )

        assert model_problem.problem_sets.count() == 3

    def test_problem_set_can_have_mixed_problem_types(self, model_problem_set):
        """Problem set can contain different problem types."""
        eipl = EiplProblem.objects.create(
            title="EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        mcq = McqProblem.objects.create(
            title="MCQ",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )

        ProblemSetMembership.objects.create(
            problem_set=model_problem_set, problem=eipl, order=0
        )
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set, problem=mcq, order=1
        )

        problems = list(model_problem_set.problems.all())
        types = {type(p).__name__ for p in problems}
        assert types == {"EiplProblem", "McqProblem"}

    def test_submission_problem_type_matches_problem(
        self, model_user, model_problem, model_problem_set
    ):
        """Submission.submission_type should match problem.problem_type."""
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input="test",
            submission_type="eipl",
        )
        # Verify alignment
        assert sub.submission_type == sub.problem.problem_type

    def test_course_can_have_multiple_problem_sets(self, model_instructor):
        """Course can have multiple problem sets."""
        course = Course.objects.create(
            course_id="MULTI-PS",
            name="Multi PS Course",
        )
        ps1 = ProblemSet.objects.create(title="Week 1")
        ps2 = ProblemSet.objects.create(title="Week 2")
        ps3 = ProblemSet.objects.create(title="Week 3")

        course.problem_sets.add(ps1, ps2, ps3)

        assert course.problem_sets.count() == 3


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestModelEdgeCases:
    """Edge case tests for model behavior."""

    def test_very_long_title_fails_without_explicit_slug(self, db):
        """Very long title without explicit slug raises DataError.

        Note: ProblemSet.save() auto-generates slug but doesn't truncate.
        This documents that explicit slugs should be provided for long titles.
        """
        from django.db.utils import DataError

        long_title = "A" * 300  # Much longer than slug max_length
        with pytest.raises(DataError):
            ProblemSet.objects.create(title=long_title)

    def test_long_title_within_limit_works_with_explicit_slug(self, db):
        """Long title (within 200 char limit) works with explicit slug."""
        long_title = "A" * 150  # Within title max_length (200)
        ps = ProblemSet.objects.create(title=long_title, slug="short-slug")
        assert ps.title == long_title
        assert ps.slug == "short-slug"

    def test_unicode_in_title(self, db):
        """Unicode characters in title should work."""
        ps = ProblemSet.objects.create(title="数学问题集 - Math Problems")
        assert ps.title == "数学问题集 - Math Problems"
        # Slug will be ASCII-ified
        assert ps.slug  # Should have some slug

    def test_submission_with_very_long_raw_input(
        self, model_user, model_problem, model_problem_set
    ):
        """Submission should handle very long raw_input."""
        long_input = "x" * 100000  # 100KB of text
        sub = Submission.objects.create(
            user=model_user,
            problem=model_problem,
            problem_set=model_problem_set,
            raw_input=long_input,
            submission_type="eipl",
        )
        assert len(sub.raw_input) == 100000

    def test_problem_set_ordering_preserved(self, model_problem_set):
        """Problems should be retrievable in order."""
        p1 = EiplProblem.objects.create(
            title="First",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        p2 = EiplProblem.objects.create(
            title="Second",
            reference_solution="def y(): pass",
            function_signature="def y() -> None",
        )
        p3 = EiplProblem.objects.create(
            title="Third",
            reference_solution="def z(): pass",
            function_signature="def z() -> None",
        )

        # Add in non-sequential order
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set, problem=p2, order=1
        )
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set, problem=p3, order=2
        )
        ProblemSetMembership.objects.create(
            problem_set=model_problem_set, problem=p1, order=0
        )

        # Query with ordering
        memberships = model_problem_set.problemsetmembership_set.order_by("order")
        ordered_problems = [m.problem for m in memberships]

        assert ordered_problems[0].title == "First"
        assert ordered_problems[1].title == "Second"
        assert ordered_problems[2].title == "Third"
