"""
Integration tests for the grading pipeline execution.

These tests verify:
1. Pipeline helper functions work correctly in isolation
2. Pipeline tasks handle errors gracefully
3. Progress publishing occurs at correct stages
4. Submission state transitions are correct

All tests mock Docker execution to avoid requiring a real Docker daemon.
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


# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.django_db
class TestGenerateVariationsHelper:
    """Tests for generate_variations_helper function."""

    def test_generate_variations_success(self, db):
        """
        generate_variations_helper should return a list of code variations
        when AI generation succeeds.
        """
        from purplex.problems_app.tasks.pipeline import generate_variations_helper

        problem = EiplProblemFactory(is_active=True)

        mock_ai_result = {
            "success": True,
            "variations": [
                "def double(x):\n    return x * 2",
                "def double(x):\n    return 2 * x",
                "def double(num):\n    return num + num",
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.AITestGenerationService"
        ) as MockAI:
            mock_service = MockAI.return_value
            mock_service.generate_eipl_variations.return_value = mock_ai_result

            variations = generate_variations_helper(problem.id, "Double the input")

            assert len(variations) == 3
            assert "def double(x)" in variations[0]
            mock_service.generate_eipl_variations.assert_called_once()

    def test_generate_variations_problem_not_found(self, db):
        """generate_variations_helper should raise when problem doesn't exist."""
        from purplex.problems_app.tasks.pipeline import generate_variations_helper

        with pytest.raises(Exception) as exc_info:
            generate_variations_helper(999999, "Test prompt")

        assert "not found" in str(exc_info.value)

    def test_generate_variations_inactive_problem(self, db):
        """generate_variations_helper should raise for inactive problems."""
        from purplex.problems_app.tasks.pipeline import generate_variations_helper

        problem = EiplProblemFactory(is_active=False)

        with pytest.raises(Exception) as exc_info:
            generate_variations_helper(problem.id, "Test prompt")

        assert "not active" in str(exc_info.value)

    def test_generate_variations_ai_failure(self, db):
        """generate_variations_helper should raise when AI generation fails."""
        from purplex.problems_app.tasks.pipeline import generate_variations_helper

        problem = EiplProblemFactory(is_active=True)

        mock_ai_result = {"success": False, "error": "API rate limit exceeded"}

        with patch(
            "purplex.problems_app.tasks.pipeline.AITestGenerationService"
        ) as MockAI:
            mock_service = MockAI.return_value
            mock_service.generate_eipl_variations.return_value = mock_ai_result

            with pytest.raises(Exception) as exc_info:
                generate_variations_helper(problem.id, "Test prompt")

            assert "AI generation failed" in str(exc_info.value)


@pytest.mark.django_db
class TestTestVariationHelper:
    """Tests for test_variation_helper function."""

    def test_variation_all_tests_pass(self, db):
        """test_variation_helper should return success when all tests pass."""
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(function_name="double")
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        TestCaseFactory(problem=problem, inputs=[3], expected_output=6)

        mock_docker_result = {
            "testsPassed": 2,
            "totalTests": 2,
            "success": True,
            "results": [
                {"pass": True, "inputs": [1], "expected_output": 2, "actual_output": 2},
                {"pass": True, "inputs": [3], "expected_output": 6, "actual_output": 6},
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            result = test_variation_helper(
                "def double(x):\n    return x * 2", problem.id, 0
            )

            assert result["success"] is True
            assert result["testsPassed"] == 2
            assert result["totalTests"] == 2
            assert result["variation_index"] == 0

    def test_variation_partial_failure(self, db):
        """test_variation_helper should return partial results when some tests fail."""
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(function_name="double")
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        TestCaseFactory(problem=problem, inputs=[3], expected_output=6)

        mock_docker_result = {
            "testsPassed": 1,
            "totalTests": 2,
            "success": False,
            "results": [
                {"pass": True, "inputs": [1], "expected_output": 2, "actual_output": 2},
                {
                    "pass": False,
                    "inputs": [3],
                    "expected_output": 6,
                    "actual_output": 5,
                },
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            result = test_variation_helper(
                "def double(x):\n    return x + 1", problem.id, 0
            )

            assert result["success"] is False
            assert result["testsPassed"] == 1
            assert result["totalTests"] == 2

    def test_variation_with_error(self, db):
        """test_variation_helper should preserve error messages from Docker."""
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(function_name="double")
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)

        mock_docker_result = {
            "testsPassed": 0,
            "totalTests": 1,
            "success": False,
            "error": "NameError: name 'undefined_var' is not defined",
            "results": [],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            result = test_variation_helper(
                "def double(x):\n    return undefined_var", problem.id, 0
            )

            assert result["success"] is False
            assert "error" in result
            assert "NameError" in result["error"]


@pytest.mark.django_db
class TestSegmentPromptHelper:
    """Tests for segment_prompt_helper function."""

    def test_segment_prompt_disabled(self, db):
        """segment_prompt_helper should return None when segmentation is disabled."""
        from purplex.problems_app.tasks.pipeline import segment_prompt_helper

        # Segmentation disabled via requires_highlevel_comprehension=False
        problem = EiplProblemFactory(requires_highlevel_comprehension=False)

        result = segment_prompt_helper("Test prompt", problem.id)

        assert result is None

    def test_segment_prompt_enabled(self, db):
        """segment_prompt_helper should return segmentation data when enabled."""
        from purplex.problems_app.tasks.pipeline import segment_prompt_helper

        # Segmentation enabled via requires_highlevel_comprehension=True
        # and segmentation_config with enabled=True (default)
        problem = EiplProblemFactory(
            requires_highlevel_comprehension=True,
            segmentation_threshold=3,
            segmentation_config={"enabled": True},
            reference_solution="def double(x):\n    return x * 2",
        )

        mock_result = {
            "success": True,
            "segment_count": 2,
            "comprehension_level": "relational",
            "segments": ["Take the input", "Multiply by 2"],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SegmentationService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.segment_prompt.return_value = mock_result

            result = segment_prompt_helper("Double the input and return it", problem.id)

            assert result is not None
            assert result["segment_count"] == 2
            assert result["passed"] is True  # 2 <= 3 threshold
            assert result["threshold"] == 3


@pytest.mark.django_db
class TestSaveSubmissionHelper:
    """Tests for save_submission_helper function."""

    @pytest.fixture
    def setup_eipl_problem(self, db):
        """Create a complete EiPL problem setup for testing."""
        user = UserFactory()
        UserProfileFactory(user=user)
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        tc1 = TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        tc2 = TestCaseFactory(problem=problem, inputs=[5], expected_output=10)

        return {
            "user": user,
            "problem": problem,
            "problem_set": problem_set,
            "test_cases": [tc1, tc2],
        }

    def test_save_creates_new_submission(self, setup_eipl_problem):
        """save_submission_helper creates a new submission when no submission_id."""
        from purplex.problems_app.tasks.pipeline import save_submission_helper

        user = setup_eipl_problem["user"]
        problem = setup_eipl_problem["problem"]
        problem_set = setup_eipl_problem["problem_set"]
        tc1, tc2 = setup_eipl_problem["test_cases"]

        variations = ["def func(x):\n    return x * 2"]
        test_results = [
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
                        "inputs": [5],
                        "expected_output": 10,
                        "actual_output": 10,
                    },
                ],
            }
        ]

        with patch("purplex.submissions.services.ProgressService.process_submission"):
            result = save_submission_helper(
                user_id=user.id,
                problem_id=problem.id,
                problem_set_id=problem_set.id,
                course_id=None,
                user_prompt="Double the input",
                variations=variations,
                test_results=test_results,
                segmentation=None,
                task_id="test-task-123",
            )

        assert "submission_id" in result
        assert result["score"] == 100
        assert result["successful_variations"] == 1

        # Verify submission was created
        sub = Submission.objects.get(submission_id=result["submission_id"])
        assert sub.user == user
        assert sub.problem == problem
        assert sub.score == 100

    def test_save_updates_existing_submission(self, setup_eipl_problem):
        """save_submission_helper updates existing submission when submission_id provided."""
        from purplex.problems_app.tasks.pipeline import save_submission_helper
        from purplex.submissions.services import SubmissionService

        user = setup_eipl_problem["user"]
        problem = setup_eipl_problem["problem"]
        problem_set = setup_eipl_problem["problem_set"]
        tc1, tc2 = setup_eipl_problem["test_cases"]

        # Create initial pending submission (simulating what view does)
        initial_submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            raw_input="Double the input",
            submission_type="eipl",
            problem_set=problem_set,
        )
        initial_id = str(initial_submission.submission_id)

        # Count before
        count_before = Submission.objects.filter(user=user, problem=problem).count()
        assert count_before == 1

        variations = ["def func(x):\n    return x * 2"]
        test_results = [
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
                        "inputs": [5],
                        "expected_output": 10,
                        "actual_output": 10,
                    },
                ],
            }
        ]

        with patch("purplex.submissions.services.ProgressService.process_submission"):
            result = save_submission_helper(
                user_id=user.id,
                problem_id=problem.id,
                problem_set_id=problem_set.id,
                course_id=None,
                user_prompt="Double the input",
                variations=variations,
                test_results=test_results,
                segmentation=None,
                task_id="test-task-456",
                submission_id=initial_id,  # Pass existing submission
            )

        # CRITICAL: No duplicate should be created
        count_after = Submission.objects.filter(user=user, problem=problem).count()
        assert count_after == 1, f"Expected 1 submission, got {count_after}"

        # Same submission_id returned
        assert result["submission_id"] == initial_id

    def test_save_with_partial_test_failure(self, setup_eipl_problem):
        """save_submission_helper correctly scores partial failures."""
        from purplex.problems_app.tasks.pipeline import save_submission_helper

        user = setup_eipl_problem["user"]
        problem = setup_eipl_problem["problem"]
        problem_set = setup_eipl_problem["problem_set"]
        tc1, tc2 = setup_eipl_problem["test_cases"]

        variations = [
            "def func(x):\n    return x * 2",
            "def func(x):\n    return x + 1",  # Wrong
        ]
        test_results = [
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
                        "inputs": [5],
                        "expected_output": 10,
                        "actual_output": 10,
                    },
                ],
            },
            {
                "variation_index": 1,
                "success": False,
                "testsPassed": 0,
                "totalTests": 2,
                "test_results": [
                    {
                        "test_case_id": tc1.id,
                        "pass": False,
                        "inputs": [1],
                        "expected_output": 2,
                        "actual_output": 2,
                    },
                    {
                        "test_case_id": tc2.id,
                        "pass": False,
                        "inputs": [5],
                        "expected_output": 10,
                        "actual_output": 6,
                    },
                ],
            },
        ]

        with patch("purplex.submissions.services.ProgressService.process_submission"):
            result = save_submission_helper(
                user_id=user.id,
                problem_id=problem.id,
                problem_set_id=problem_set.id,
                course_id=None,
                user_prompt="Double the input",
                variations=variations,
                test_results=test_results,
                segmentation=None,
                task_id="test-task-789",
            )

        # 1 of 2 variations passed
        assert result["successful_variations"] == 1
        assert result["total_variations"] == 2
        # Score is based on variations (50%)
        sub = Submission.objects.get(submission_id=result["submission_id"])
        assert sub.score == 50


# =============================================================================
# Pipeline task tests (with mocked dependencies)
# =============================================================================


@pytest.mark.django_db
class TestEiplPipelineExecution:
    """Tests for execute_eipl_pipeline task.

    These tests use `task.apply()` to run Celery tasks synchronously,
    which provides a real request context with auto-generated task_id.
    """

    @pytest.fixture
    def eipl_setup(self, db):
        """Create complete setup for EiPL pipeline testing."""
        user = UserFactory()
        UserProfileFactory(user=user)
        course = CourseFactory()
        CourseEnrollmentFactory(user=user, course=course)
        problem_set = ProblemSetFactory()
        CourseProblemSetFactory(course=course, problem_set=problem_set)
        problem = EiplProblemFactory(
            is_active=True,
            function_name="double",
            requires_highlevel_comprehension=False,  # Disable segmentation for simpler tests
        )
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        tc1 = TestCaseFactory(problem=problem, inputs=[2], expected_output=4)
        tc2 = TestCaseFactory(problem=problem, inputs=[5], expected_output=10)

        return {
            "user": user,
            "course": course,
            "problem_set": problem_set,
            "problem": problem,
            "test_cases": [tc1, tc2],
        }

    def test_pipeline_success_all_tests_pass(self, eipl_setup):
        """EiPL pipeline completes successfully when all tests pass."""
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        user = eipl_setup["user"]
        problem = eipl_setup["problem"]
        problem_set = eipl_setup["problem_set"]
        course = eipl_setup["course"]

        # Mock AI generation
        mock_variations = ["def double(x):\n    return x * 2"]

        # Mock Docker execution
        mock_docker_result = {
            "testsPassed": 2,
            "totalTests": 2,
            "success": True,
            "results": [
                {"pass": True, "inputs": [2], "expected_output": 4, "actual_output": 4},
                {
                    "pass": True,
                    "inputs": [5],
                    "expected_output": 10,
                    "actual_output": 10,
                },
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.generate_variations_helper",
            return_value=mock_variations,
        ):
            with patch(
                "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
            ) as MockCtx:
                mock_service = MagicMock()
                mock_service.test_solution.return_value = mock_docker_result
                MockCtx.return_value.__enter__.return_value = mock_service

                with patch("purplex.problems_app.tasks.pipeline.publish_progress"):
                    with patch(
                        "purplex.problems_app.tasks.pipeline.publish_completion"
                    ) as mock_completion:
                        with patch(
                            "purplex.submissions.services.ProgressService.process_submission"
                        ):
                            # Use .apply() to run task synchronously
                            async_result = execute_eipl_pipeline.apply(
                                args=[
                                    problem.id,
                                    "Double the input",
                                    user.id,
                                    problem_set.id,
                                    course.id,
                                ]
                            )
                            result = async_result.result

        assert result["score"] == 100
        assert result["is_correct"] is True
        assert "submission_id" in result

        # Verify completion was published
        mock_completion.assert_called_once()

    def test_pipeline_handles_ai_generation_failure(self, eipl_setup):
        """EiPL pipeline handles AI generation failure gracefully."""
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        user = eipl_setup["user"]
        problem = eipl_setup["problem"]

        # All patches must be active when exception is caught and publish_error is called
        with patch("purplex.problems_app.tasks.pipeline.publish_progress"):
            with patch(
                "purplex.problems_app.tasks.pipeline.publish_error"
            ) as mock_error:
                with patch(
                    "purplex.problems_app.tasks.pipeline.generate_variations_helper",
                    side_effect=Exception("AI service unavailable"),
                ):
                    # Use .apply(throw=False) to capture exception in result instead of raising
                    async_result = execute_eipl_pipeline.apply(
                        args=[problem.id, "Double the input", user.id],
                        throw=False,  # Don't raise, capture in result
                    )

                # apply() captures exception in result
                assert async_result.failed()
                assert "AI service unavailable" in str(async_result.result)
                mock_error.assert_called_once()

    def test_pipeline_idempotency_on_retry(self, eipl_setup):
        """EiPL pipeline returns cached result on retry instead of creating duplicate."""
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline
        from purplex.submissions.services import SubmissionService

        user = eipl_setup["user"]
        problem = eipl_setup["problem"]
        problem_set = eipl_setup["problem_set"]

        # Create existing submission with a specific task ID
        existing_submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            raw_input="Double the input",
            submission_type="eipl",
            problem_set=problem_set,
        )
        existing_task_id = "task-idempotent-test-12345"
        existing_submission.celery_task_id = existing_task_id
        existing_submission.score = 100
        existing_submission.execution_status = "completed"
        existing_submission.save()

        # Run task with same task_id (simulating idempotent retry)
        with patch("purplex.problems_app.tasks.pipeline.publish_progress"):
            # Use apply() with task_id to simulate retry
            async_result = execute_eipl_pipeline.apply(
                args=[problem.id, "Double the input", user.id, problem_set.id],
                task_id=existing_task_id,  # Same task ID as existing submission
            )
            result = async_result.result

        # Should return cached result, not create new submission
        assert result["submission_id"] == str(existing_submission.submission_id)

        # Verify submission count didn't increase
        count = Submission.objects.filter(user=user, problem=problem).count()
        assert count == 1, f"Expected 1 submission, got {count}"


@pytest.mark.django_db
class TestDebugFixPipelineExecution:
    """Tests for execute_debug_fix_pipeline task."""

    @pytest.fixture
    def debug_fix_setup(self, db):
        """Create setup for Debug Fix pipeline testing."""
        user = UserFactory()
        UserProfileFactory(user=user)
        problem = DebugFixProblemFactory(is_active=True, function_name="add_numbers")
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        tc1 = TestCaseFactory(problem=problem, inputs=[1, 2], expected_output=3)
        tc2 = TestCaseFactory(problem=problem, inputs=[5, 5], expected_output=10)

        return {
            "user": user,
            "problem": problem,
            "problem_set": problem_set,
            "test_cases": [tc1, tc2],
        }

    def test_debug_fix_pipeline_success(self, debug_fix_setup):
        """Debug Fix pipeline completes successfully with correct fix."""
        from purplex.problems_app.tasks.pipeline import execute_debug_fix_pipeline

        user = debug_fix_setup["user"]
        problem = debug_fix_setup["problem"]
        problem_set = debug_fix_setup["problem_set"]

        mock_docker_result = {
            "testsPassed": 2,
            "totalTests": 2,
            "success": True,
            "results": [
                {
                    "pass": True,
                    "inputs": [1, 2],
                    "expected_output": 3,
                    "actual_output": 3,
                },
                {
                    "pass": True,
                    "inputs": [5, 5],
                    "expected_output": 10,
                    "actual_output": 10,
                },
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            with patch("purplex.problems_app.tasks.pipeline.publish_progress"):
                with patch("purplex.problems_app.tasks.pipeline.publish_completion"):
                    with patch(
                        "purplex.submissions.services.ProgressService.process_submission"
                    ):
                        # Use .apply() for synchronous execution
                        async_result = execute_debug_fix_pipeline.apply(
                            args=[
                                problem.id,
                                "def add_numbers(a, b):\n    return a + b",
                                user.id,
                                problem_set.id,
                            ]
                        )
                        result = async_result.result

        assert result["score"] == 100
        assert result["is_correct"] is True


@pytest.mark.django_db
class TestProbeableCodePipelineExecution:
    """Tests for execute_probeable_code_pipeline task."""

    @pytest.fixture
    def probeable_setup(self, db):
        """Create setup for Probeable Code pipeline testing."""
        user = UserFactory()
        UserProfileFactory(user=user)
        problem = ProbeableCodeProblemFactory(is_active=True, function_name="mystery")
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)

        tc1 = TestCaseFactory(problem=problem, inputs=[2], expected_output=4)
        tc2 = TestCaseFactory(problem=problem, inputs=[0], expected_output=0)

        return {
            "user": user,
            "problem": problem,
            "problem_set": problem_set,
            "test_cases": [tc1, tc2],
        }

    def test_probeable_code_pipeline_success(self, probeable_setup):
        """Probeable Code pipeline completes successfully."""
        from purplex.problems_app.tasks.pipeline import execute_probeable_code_pipeline

        user = probeable_setup["user"]
        problem = probeable_setup["problem"]
        problem_set = probeable_setup["problem_set"]

        mock_docker_result = {
            "testsPassed": 2,
            "totalTests": 2,
            "success": True,
            "results": [
                {"pass": True, "inputs": [2], "expected_output": 4, "actual_output": 4},
                {"pass": True, "inputs": [0], "expected_output": 0, "actual_output": 0},
            ],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            with patch("purplex.problems_app.tasks.pipeline.publish_progress"):
                with patch("purplex.problems_app.tasks.pipeline.publish_completion"):
                    with patch(
                        "purplex.submissions.services.ProgressService.process_submission"
                    ):
                        # Use .apply() for synchronous execution
                        async_result = execute_probeable_code_pipeline.apply(
                            args=[
                                problem.id,
                                "def mystery(x):\n    return x * 2",
                                user.id,
                                problem_set.id,
                            ]
                        )
                        result = async_result.result

        assert result["score"] == 100
        assert result["is_correct"] is True


# =============================================================================
# Error handling tests
# =============================================================================


@pytest.mark.django_db
class TestPipelineErrorHandling:
    """Tests for pipeline error handling paths."""

    def test_pipeline_handles_docker_timeout(self, db):
        """Pipeline handles Docker execution timeout gracefully."""
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(function_name="slow_func")
        TestCaseFactory(problem=problem, inputs=[1], expected_output=1)

        mock_docker_result = {
            "testsPassed": 0,
            "totalTests": 1,
            "success": False,
            "error": "Code execution timed out after 5 seconds",
            "results": [],
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            result = test_variation_helper(
                "def slow_func(x):\n    while True: pass", problem.id, 0
            )

        assert result["success"] is False
        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_pipeline_handles_malformed_docker_result(self, db):
        """Pipeline handles malformed Docker results without crashing."""
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(function_name="test_func")
        TestCaseFactory(problem=problem, inputs=[1], expected_output=1)

        # Malformed result - missing expected fields
        mock_docker_result = {
            "error": "Container failed to start",
        }

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_docker_result
            MockCtx.return_value.__enter__.return_value = mock_service

            result = test_variation_helper(
                "def test_func(x):\n    return x", problem.id, 0
            )

        # Should not crash, should return error state
        assert result["success"] is False
        assert result["testsPassed"] == 0
        assert result["totalTests"] == 0
        assert "error" in result

    def test_pipeline_handles_user_not_found(self, db):
        """save_submission_helper handles non-existent user."""
        from purplex.problems_app.tasks.pipeline import save_submission_helper

        problem = EiplProblemFactory()

        with pytest.raises(Exception) as exc_info:
            save_submission_helper(
                user_id=999999,  # Non-existent
                problem_id=problem.id,
                problem_set_id=None,
                course_id=None,
                user_prompt="Test",
                variations=[],
                test_results=[],
                segmentation=None,
                task_id="test-task",
            )

        assert "User" in str(exc_info.value) and "not found" in str(exc_info.value)
