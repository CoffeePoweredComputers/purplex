"""
Tests to verify that async submission pipelines update existing submissions
instead of creating duplicates.

Bug Description:
- ActivitySubmissionView creates a submission BEFORE calling handler.submit()
- Async handlers (EiPL, DebugFix, ProbeableCode) ignore the passed submission
- Pipeline tasks create NEW submissions in save_submission_helper()
- Result: TWO submissions per attempt (one orphaned with 0%, one with results)

Expected Behavior:
- View creates submission with status='pending'
- Handler passes submission_id to Celery task
- Pipeline updates the EXISTING submission with results
- Result: ONE submission per attempt

These tests verify the fix by checking submission count before/after pipeline.
"""

from unittest.mock import MagicMock, patch

import pytest

from purplex.submissions.models import Submission
from tests.factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    CourseProblemSetFactory,
    DebugFixProblemFactory,
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    TestCaseFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = pytest.mark.integration


@pytest.mark.django_db
class TestNoSubmissionDuplicates:
    """
    Regression tests for duplicate submission creation bug.

    Each test verifies that exactly ONE submission exists after pipeline completion.
    """

    @pytest.fixture
    def user_with_enrollment(self, db):
        """Create a user enrolled in a course with a problem set."""
        user = UserFactory()
        UserProfileFactory(user=user)

        course = CourseFactory()
        CourseEnrollmentFactory(user=user, course=course)

        problem_set = ProblemSetFactory()
        CourseProblemSetFactory(course=course, problem_set=problem_set)

        return {
            "user": user,
            "course": course,
            "problem_set": problem_set,
        }

    @pytest.fixture
    def eipl_problem_with_tests(self, user_with_enrollment):
        """Create an EiPL problem with test cases."""
        problem = EiplProblemFactory()
        ps = user_with_enrollment["problem_set"]
        ProblemSetMembershipFactory(problem_set=ps, problem=problem)

        # Create test cases
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        TestCaseFactory(problem=problem, inputs=[2], expected_output=4)

        return problem

    def test_eipl_pipeline_updates_existing_submission(
        self, user_with_enrollment, eipl_problem_with_tests
    ):
        """
        CRITICAL: EiPL pipeline should update the submission created by the view,
        not create a new one.

        This test verifies:
        1. A submission is created with status='pending' before pipeline runs
        2. After pipeline completes, the SAME submission is updated
        3. No additional submissions are created
        """
        from purplex.problems_app.tasks.pipeline import save_submission_helper
        from purplex.submissions.services import SubmissionService

        user = user_with_enrollment["user"]
        course = user_with_enrollment["course"]
        problem_set = user_with_enrollment["problem_set"]
        problem = eipl_problem_with_tests

        # Step 1: Create submission (simulating what view does)
        initial_submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            raw_input="Test prompt for EiPL",
            submission_type="eipl",
            problem_set=problem_set,
            course=course,
        )

        # Verify initial state
        assert initial_submission.execution_status == "pending"
        assert initial_submission.score == 0

        # Count submissions before pipeline
        count_before = Submission.objects.filter(
            user=user,
            problem=problem,
            problem_set=problem_set,
        ).count()
        assert count_before == 1, "Should have exactly 1 submission before pipeline"

        # Get test case IDs
        test_cases = list(problem.test_cases.all())
        tc1_id = test_cases[0].id
        tc2_id = test_cases[1].id

        # Step 2: Run save_submission_helper with submission_id
        # This simulates what the fixed pipeline should do
        mock_variations = ["def test_func(x):\n    return x * 2"]
        mock_test_results = [
            {
                "variation_index": 0,
                "success": True,
                "testsPassed": 2,
                "totalTests": 2,
                "test_results": [
                    {
                        "test_case_id": tc1_id,
                        "pass": True,
                        "inputs": [1],
                        "expected_output": 2,
                        "actual_output": 2,
                    },
                    {
                        "test_case_id": tc2_id,
                        "pass": True,
                        "inputs": [2],
                        "expected_output": 4,
                        "actual_output": 4,
                    },
                ],
            }
        ]

        # The fix should make save_submission_helper accept submission_id
        # and update the existing submission instead of creating a new one
        # Mock progress tracking to avoid unrelated F() expression bug
        with patch("purplex.submissions.services.ProgressService.process_submission"):
            save_submission_helper(
                user_id=user.id,
                problem_id=problem.id,
                problem_set_id=problem_set.id,
                course_id=course.id,
                user_prompt="Test prompt for EiPL",
                variations=mock_variations,
                test_results=mock_test_results,
                segmentation=None,
                task_id="test-task-id",
                # NEW PARAMETER: submission_id for updating existing submission
                submission_id=str(initial_submission.submission_id),
            )

        # Step 3: Verify NO DUPLICATE was created
        count_after = Submission.objects.filter(
            user=user,
            problem=problem,
            problem_set=problem_set,
        ).count()

        # This assertion is the KEY test - should still be 1
        assert count_after == 1, (
            f"DUPLICATE BUG: Expected 1 submission, got {count_after}. "
            "Pipeline created a new submission instead of updating the existing one."
        )

        # Step 4: Verify the EXISTING submission was updated
        initial_submission.refresh_from_db()
        assert initial_submission.execution_status == "completed"
        assert initial_submission.score == 100
        assert initial_submission.passed_all_tests is True


@pytest.mark.django_db
class TestEiplHandlerPassesSubmissionId:
    """
    Tests that EiPL handler correctly passes submission_id to Celery task.
    """

    def test_eipl_handler_includes_submission_id_in_task_args(self, db):
        """
        The EiPL handler should pass submission.submission_id to the Celery task
        so the pipeline can update the existing submission.
        """
        from purplex.problems_app.handlers.eipl.handler import EiPLHandler
        from purplex.submissions.models import Submission

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        # Create a mock submission
        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            raw_input="test prompt",
            submission_type="eipl",
        )

        handler = EiPLHandler()
        context = {
            "user_id": user.id,
            "problem_set_id": problem_set.id,
            "course_id": None,
            "request_id": "test-request-123",
        }

        # Mock the Celery task to capture its arguments
        with patch(
            "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline.apply_async"
        ) as mock_apply:
            mock_async_result = MagicMock()
            mock_async_result.id = "test-task-id"
            mock_apply.return_value = mock_async_result

            handler.submit(submission, "test prompt", problem, context)

            # Verify task was called
            assert mock_apply.called

            # Get the call arguments
            call_kwargs = mock_apply.call_args
            task_args = call_kwargs.kwargs.get(
                "args", call_kwargs.args[0] if call_kwargs.args else []
            )

            # The fix should include submission_id in the task arguments
            # Expected args: [problem_id, user_prompt, user_id, problem_set_id, course_id, submission_id]
            assert (
                len(task_args) >= 6
            ), f"Task should include submission_id. Got {len(task_args)} args: {task_args}"

            # submission_id should be the 6th argument (index 5)
            submission_id_arg = task_args[5] if len(task_args) > 5 else None
            assert submission_id_arg == str(submission.submission_id), (
                f"submission_id not passed to task. Expected {submission.submission_id}, "
                f"got {submission_id_arg}"
            )


@pytest.mark.django_db
class TestDebugFixHandlerPassesSubmissionId:
    """
    Tests that Debug Fix handler correctly passes submission_id to Celery task.
    """

    def test_debug_fix_handler_includes_submission_id(self, db):
        """
        The Debug Fix handler should pass submission.submission_id to the Celery task.
        """
        from purplex.problems_app.handlers.debug_fix.handler import DebugFixHandler
        from purplex.submissions.models import Submission

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = DebugFixProblemFactory()
        problem_set = ProblemSetFactory()

        # Create a mock submission
        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            raw_input="def add(a, b):\n    return a + b",
            submission_type="debug_fix",
        )

        handler = DebugFixHandler()
        context = {
            "user_id": user.id,
            "problem_set_id": problem_set.id,
            "course_id": None,
            "request_id": "test-request-456",
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.execute_debug_fix_pipeline.apply_async"
        ) as mock_apply:
            mock_async_result = MagicMock()
            mock_async_result.id = "test-task-id"
            mock_apply.return_value = mock_async_result

            handler.submit(
                submission, "def add(a, b):\n    return a + b", problem, context
            )

            call_kwargs = mock_apply.call_args
            task_args = call_kwargs.kwargs.get(
                "args", call_kwargs.args[0] if call_kwargs.args else []
            )

            # The fix should include submission_id in the task arguments
            assert (
                len(task_args) >= 6
            ), f"Task should include submission_id. Got {len(task_args)} args"

            submission_id_arg = task_args[5] if len(task_args) > 5 else None
            assert submission_id_arg == str(submission.submission_id)


@pytest.mark.django_db
class TestProbeableCodeHandlerPassesSubmissionId:
    """
    Tests that Probeable Code handler correctly passes submission_id to Celery task.
    """

    def test_probeable_code_handler_includes_submission_id(self, db):
        """
        The Probeable Code handler should pass submission.submission_id to the Celery task.
        """
        from purplex.problems_app.handlers.probeable_code.handler import (
            ProbeableCodeHandler,
        )
        from purplex.submissions.models import Submission

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = ProbeableCodeProblemFactory()
        problem_set = ProblemSetFactory()

        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            raw_input="def mystery(x):\n    return x * 2",
            submission_type="probeable_code",
        )

        handler = ProbeableCodeHandler()
        context = {
            "user_id": user.id,
            "problem_set_id": problem_set.id,
            "course_id": None,
            "request_id": "test-request-789",
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.execute_probeable_code_pipeline.apply_async"
        ) as mock_apply:
            mock_async_result = MagicMock()
            mock_async_result.id = "test-task-id"
            mock_apply.return_value = mock_async_result

            handler.submit(
                submission, "def mystery(x):\n    return x * 2", problem, context
            )

            call_kwargs = mock_apply.call_args
            task_args = call_kwargs.kwargs.get(
                "args", call_kwargs.args[0] if call_kwargs.args else []
            )

            assert (
                len(task_args) >= 6
            ), f"Task should include submission_id. Got {len(task_args)} args"

            submission_id_arg = task_args[5] if len(task_args) > 5 else None
            assert submission_id_arg == str(submission.submission_id)


@pytest.mark.django_db
class TestPipelineAcceptsSubmissionId:
    """
    Tests that pipeline tasks accept and use the submission_id parameter.
    """

    def test_save_submission_helper_accepts_submission_id(self, db):
        """
        save_submission_helper should accept submission_id parameter
        and update existing submission instead of creating new one.
        """
        from purplex.problems_app.tasks.pipeline import save_submission_helper
        from purplex.submissions.services import SubmissionService

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        # Create test cases
        tc1 = TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        tc2 = TestCaseFactory(problem=problem, inputs=[2], expected_output=4)

        # Create initial submission
        initial_submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            raw_input="Test prompt",
            submission_type="eipl",
            problem_set=problem_set,
        )
        initial_id = initial_submission.submission_id

        # Prepare mock data
        mock_variations = ["def test_func(x):\n    return x * 2"]
        mock_test_results = [
            {
                "variation_index": 0,
                "success": True,
                "testsPassed": 2,
                "totalTests": 2,
                "test_results": [
                    {
                        "test_case_id": tc1.id,
                        "pass": True,
                        "inputs": [1],
                        "expected_output": 2,
                        "actual_output": 2,
                    },
                    {
                        "test_case_id": tc2.id,
                        "pass": True,
                        "inputs": [2],
                        "expected_output": 4,
                        "actual_output": 4,
                    },
                ],
            }
        ]

        # Call helper WITH submission_id (the fix)
        # Mock progress tracking to avoid unrelated F() expression bug
        with patch("purplex.submissions.services.ProgressService.process_submission"):
            result = save_submission_helper(
                user_id=user.id,
                problem_id=problem.id,
                problem_set_id=problem_set.id,
                course_id=None,
                user_prompt="Test prompt",
                variations=mock_variations,
                test_results=mock_test_results,
                segmentation=None,
                task_id="test-task-id",
                submission_id=str(initial_id),  # THE FIX: pass existing submission_id
            )

        # The returned submission_id should be the SAME as the initial one
        assert result["submission_id"] == str(initial_id), (
            f"Expected submission_id {initial_id}, got {result['submission_id']}. "
            "Pipeline should update existing submission, not create new one."
        )

        # Verify only one submission exists
        count = Submission.objects.filter(user=user, problem=problem).count()
        assert count == 1, f"Expected 1 submission, got {count}"

        # Verify the submission was updated
        initial_submission.refresh_from_db()
        assert initial_submission.score == 100
        assert initial_submission.execution_status == "completed"


@pytest.mark.django_db
class TestSubmissionHistoryNoDuplicates:
    """
    End-to-end test that submission history shows no duplicates.
    """

    def test_submission_history_count_matches_actual_attempts(self, db):
        """
        Submission history should show exactly N entries for N submission attempts.

        This is a sanity check that can be used to detect duplicates in production.
        """
        from purplex.submissions.repositories.submission_repository import (
            SubmissionRepository,
        )

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        # Create exactly 3 submissions manually (simulating 3 attempts)
        for i in range(3):
            Submission.objects.create(
                user=user,
                problem=problem,
                problem_set=problem_set,
                raw_input=f"Attempt {i+1}",
                submission_type="eipl",
                score=100 if i % 2 == 0 else 0,
                execution_status="completed",
            )

        # Get submission history
        history = SubmissionRepository.get_user_submission_history(
            user=user,
            problem=problem,
            problem_set=problem_set,
        )

        # Should have exactly 3 entries
        assert len(history) == 3, (
            f"Expected 3 submissions in history, got {len(history)}. "
            "This may indicate duplicate submissions."
        )
