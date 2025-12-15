"""
Debug Fix activity type handler.

Students receive buggy code and must fix it to pass all test cases.
No LLM involved - student directly edits and submits code.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from .. import register_handler
from ..base import (
    ActivityHandler,
    ProcessingResult,
    SubmissionOutcome,
    ValidationResult,
)

if TYPE_CHECKING:
    from purplex.problems_app.models import Problem
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


@register_handler("debug_fix")
class DebugFixHandler(ActivityHandler):
    """Handler for Debug Fix problems."""

    MIN_CODE_LENGTH = 10
    MAX_CODE_LENGTH = 10000

    @property
    def type_name(self) -> str:
        return "debug_fix"

    # --- Input Validation ---

    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate fixed code input."""
        code = raw_input.strip()

        if len(code) < self.MIN_CODE_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Code must be at least {self.MIN_CODE_LENGTH} characters",
            )

        if len(code) > self.MAX_CODE_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Code must be under {self.MAX_CODE_LENGTH} characters",
            )

        # Basic Python syntax check
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False, error=f"Syntax error: {e.msg} (line {e.lineno})"
            )

        return ValidationResult(is_valid=True)

    # --- Submission Processing ---

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "Problem"
    ) -> ProcessingResult:
        """
        Process Debug Fix submission.

        Note: This is a stub. Actual processing is handled by the
        execute_debug_fix_pipeline Celery task.
        """
        raise NotImplementedError(
            "Debug Fix processing is handled by execute_debug_fix_pipeline task."
        )

    # --- Grading ---

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for Debug Fix submission.

        Simple binary grading: all tests pass = complete, otherwise incomplete.
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if Debug Fix submission is correct (passes all tests)."""
        return submission.passed_all_tests

    # --- Completion Evaluation ---

    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """
        Evaluate completion status for progress tracking.

        For Debug Fix: Just correctness (no comprehension check).
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    # --- Data Extraction ---

    def extract_variations(self, submission: "Submission") -> List[str]:
        """
        Extract code from Debug Fix submission.

        Debug Fix has only one "variation" - the student's fixed code.
        """
        # For debug_fix, we store the fixed code in processed_code
        if submission.processed_code:
            return [submission.processed_code]
        return []

    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> List[Dict[str, Any]]:
        """Transform test execution to frontend format for Debug Fix."""
        results = []

        # Check if we have code variations (reusing EiPL's data structure)
        if (
            hasattr(submission, "code_variations")
            and submission.code_variations.exists()
        ):
            variation = submission.code_variations.first()
            if variation:
                test_execs = variation.test_executions.all().order_by("execution_order")
                var_results = []

                if test_execs.exists():
                    for test_exec in test_execs:
                        var_results.append(
                            {
                                "isSuccessful": test_exec.passed,
                                "function_call": self._format_function_call(
                                    problem.function_name, test_exec.input_values
                                ),
                                "expected_output": test_exec.expected_output,
                                "actual_output": test_exec.actual_output,
                                "error": test_exec.error_message,
                            }
                        )

                results.append(
                    {
                        "success": variation.tests_passed == variation.tests_total
                        and variation.tests_total > 0,
                        "testsPassed": variation.tests_passed,
                        "totalTests": variation.tests_total,
                        "test_results": var_results,
                        "results": var_results,  # Duplicate for frontend compatibility
                    }
                )

        return results

    def count_variations(self, submission: "Submission") -> int:
        """Count total variations for Debug Fix submission (always 1)."""
        return 1 if submission.processed_code else 0

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests (0 or 1 for Debug Fix)."""
        return 1 if submission.passed_all_tests else 0

    # --- API Configuration ---

    def get_problem_config(self, problem: "Problem") -> Dict[str, Any]:
        """Return configuration for frontend rendering of Debug Fix problems."""
        return {
            "display": {
                "show_reference_code": False,  # Don't show solution
                "show_buggy_code": True,  # Show buggy code to edit
                "code_read_only": False,  # Code is editable
                "show_function_signature": True,
                "section_label": "Fix the buggy code",
            },
            "input": {
                "type": "code",
                "language": "python",
                "label": "Fix the code below",
                "initial_code": getattr(problem, "buggy_code", ""),
                "min_length": self.MIN_CODE_LENGTH,
                "max_length": self.MAX_CODE_LENGTH,
            },
            "hints": {
                "available": ["bug_hint"],  # Progressive bug hints
                "bug_hints": getattr(problem, "bug_hints", []),
                "enabled": True,
            },
            "feedback": {
                "show_variations": False,  # No LLM variations
                "show_segmentation": False,  # No comprehension analysis
                "show_test_results": True,
            },
        }

    def serialize_result(self, submission: "Submission") -> Dict[str, Any]:
        """Serialize Debug Fix submission result for API response."""
        result = {
            "fixed_code": submission.processed_code or "",
            "test_results": [],
        }

        # Serialize test results using extract_test_results
        if hasattr(submission, "problem") and submission.problem:
            result["test_results"] = self.extract_test_results(
                submission, submission.problem
            )

        return result

    def get_admin_config(self) -> Dict[str, Any]:
        """Return admin UI configuration for Debug Fix problems."""
        return {
            "hidden_sections": ["mcq_options", "image_config"],
            "required_fields": [
                "title",
                "function_signature",
                "reference_solution",
                "buggy_code",
            ],
            "optional_fields": [
                "description",
                "tags",
                "categories",
                "bug_hints",
                "allow_complete_rewrite",
            ],
            "type_specific_section": "debug_fix_config",
            "supports": {
                "hints": True,  # Bug hints
                "segmentation": False,  # No comprehension analysis
                "test_cases": True,
            },
        }

    # --- Submission Execution ---

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "Problem",
        context: Dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute Debug Fix submission asynchronously via Celery.

        Debug Fix requires async because it involves:
        - Docker containers for code execution
        - Test case execution
        """
        from purplex.problems_app.tasks.pipeline import execute_debug_fix_pipeline

        # Queue the Celery task
        task = execute_debug_fix_pipeline.apply_async(
            args=[
                problem.id,
                raw_input,  # The fixed code
                context["user_id"],
                context.get("problem_set_id"),
                context.get("course_id"),
            ],
            task_id=context["request_id"],
        )

        logger.info(
            f"Debug Fix submission queued: task_id={task.id}, "
            f"problem={problem.slug}, user={context['user_id']}"
        )

        return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)
