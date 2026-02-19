"""
Tests that verify frontend-backend contract fixes.

Each test here was written to catch a specific bug found during V1 review.
The test documents what was wrong and asserts the fix is in place.
If any of these fail, the corresponding bug has regressed.
"""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from purplex.problems_app.services.course_service import CourseService
from purplex.problems_app.tasks.pipeline import execute_mcq_pipeline
from purplex.submissions.models import Submission
from tests.factories import (
    CourseEnrollmentFactory,
    McqProblemFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# =============================================================================
# Bug 1: MCQ pipeline used "completed" instead of "complete"
#
# The pipeline set completion_status = "completed" (with trailing 'd') for
# correct MCQ answers. "completed" is NOT a valid choice on the model —
# the valid values are "incomplete", "partial", "complete". Django doesn't
# enforce choices at the DB level, so the invalid value was silently
# persisted, breaking status badges and filter dropdowns.
#
# These tests exercise the actual MCQ pipeline code path with Celery and
# Redis mocked out, then check what completion_status ends up in the DB.
# =============================================================================


class TestMcqPipelineCompletionStatus:
    """Test that the MCQ pipeline sets valid completion_status values."""

    @pytest.fixture
    def mcq_setup(self, user, problem_set):
        """Set up an MCQ problem with a known correct answer (option 'b')."""
        problem = McqProblemFactory(
            options=[
                {"id": "a", "text": "Wrong", "is_correct": False},
                {"id": "b", "text": "Right", "is_correct": True},
                {"id": "c", "text": "Wrong", "is_correct": False},
            ]
        )
        return {"user": user, "problem": problem, "problem_set": problem_set}

    @patch("purplex.problems_app.services.progress_service.ProgressService.process_submission")
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_correct_mcq_sets_complete_not_completed(
        self, mock_progress, mock_process_sub, mcq_setup
    ):
        """
        The actual bug: pipeline set "completed" instead of "complete".

        Uses Celery's .apply() to run the task synchronously with a known
        task_id, so self.request.id is properly set inside the bind=True task.
        ProgressService is mocked out — we're testing the pipeline's status
        assignment, not the progress rollup.
        """
        result = execute_mcq_pipeline.apply(
            kwargs={
                "problem_id": mcq_setup["problem"].pk,
                "selected_option": "b",  # correct answer
                "user_id": mcq_setup["user"].id,
                "problem_set_id": mcq_setup["problem_set"].pk,
                "course_id": None,
            },
            task_id="test-mcq-correct-task-id",
        )
        # Re-raise any exception from the task
        result.get()

        submission = Submission.objects.get(celery_task_id="test-mcq-correct-task-id")
        assert submission.completion_status == "complete", (
            f"Expected 'complete' but got '{submission.completion_status}'. "
            f"The MCQ pipeline is setting an invalid completion_status value."
        )
        # Also verify it passes Django validation
        submission.full_clean()

    @patch("purplex.problems_app.services.progress_service.ProgressService.process_submission")
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_incorrect_mcq_sets_incomplete(
        self, mock_progress, mock_process_sub, mcq_setup
    ):
        """Wrong answer should set completion_status to 'incomplete'."""
        result = execute_mcq_pipeline.apply(
            kwargs={
                "problem_id": mcq_setup["problem"].pk,
                "selected_option": "a",  # wrong answer
                "user_id": mcq_setup["user"].id,
                "problem_set_id": mcq_setup["problem_set"].pk,
                "course_id": None,
            },
            task_id="test-mcq-wrong-task-id",
        )
        result.get()

        submission = Submission.objects.get(celery_task_id="test-mcq-wrong-task-id")
        assert submission.completion_status == "incomplete"
        submission.full_clean()


class TestCompletionStatusModelValidation:
    """Verify the model itself rejects invalid status values."""

    @pytest.fixture
    def submission(self, user, problem_set):
        problem = McqProblemFactory()
        return Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            raw_input="b",
            submission_type="mcq",
        )

    def test_completed_is_not_a_valid_choice(self, submission):
        """
        'completed' (with trailing 'd') is NOT in the model's choices.
        This is the value the old buggy pipeline wrote.
        """
        submission.completion_status = "completed"
        with pytest.raises(ValidationError) as exc_info:
            submission.full_clean()
        assert "completion_status" in exc_info.value.message_dict

    @pytest.mark.parametrize("status", ["incomplete", "partial", "complete"])
    def test_valid_statuses_pass_validation(self, submission, status):
        submission.completion_status = status
        submission.full_clean()  # Should not raise


# =============================================================================
# Bug 2: Course student response missing 'id' field
#
# CourseService.get_course_students_with_progress() returned student dicts
# without an 'id' key. The frontend DataTable uses row-key="id" and the
# delete action needs it. Without it, row rendering and deletion both break.
# =============================================================================


class TestCourseStudentResponseStructure:
    """Verify the course students service response has the expected shape."""

    def test_student_response_includes_id(self, course):
        """Each student dict must have an 'id' field (enrollment ID)."""
        student = UserFactory(username="enrolled_student")
        UserProfileFactory(user=student)
        enrollment = CourseEnrollmentFactory(user=student, course=course)

        result = CourseService.get_course_students_with_progress(course)

        assert len(result) >= 1
        student_data = result[0]
        assert "id" in student_data, (
            "Student response must include 'id' — DataTable row-key depends on it"
        )
        assert student_data["id"] == enrollment.id

    def test_student_response_includes_nested_user(self, course):
        """Each student dict must have a nested 'user' object."""
        student = UserFactory(username="nested_check", email="nested@test.edu")
        UserProfileFactory(user=student)
        CourseEnrollmentFactory(user=student, course=course)

        result = CourseService.get_course_students_with_progress(course)

        student_data = result[0]
        assert "user" in student_data, "Response must include nested 'user'"
        user_obj = student_data["user"]
        assert user_obj["id"] == student.id
        assert user_obj["username"] == "nested_check"
        assert user_obj["email"] == "nested@test.edu"

    def test_student_response_includes_progress(self, course):
        """Each student dict must have a 'progress' object."""
        student = UserFactory(username="progress_check")
        UserProfileFactory(user=student)
        CourseEnrollmentFactory(user=student, course=course)

        result = CourseService.get_course_students_with_progress(course)
        assert "progress" in result[0]


# =============================================================================
# Bug 3: Course reorder URL mismatch
#
# Frontend called /problem-sets/reorder/ but backend registered /order/.
# This caused a 404. The fix renamed the backend URL to /reorder/.
# =============================================================================


class TestCourseReorderURL:
    """Verify the course reorder URL resolves correctly."""

    def test_instructor_reorder_url_contains_reorder(self):
        """The URL path must use 'reorder', not 'order'."""
        url = reverse(
            "instructor_course_reorder", kwargs={"course_id": "CS101"}
        )
        assert url.endswith("/problem-sets/reorder/"), (
            f"URL should end with '/problem-sets/reorder/' but got: {url}"
        )
