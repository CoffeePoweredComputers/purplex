"""
Probeable Code activity handler.

Students discover hidden function behavior by querying an oracle,
then write code that implements the same behavior.

Flow:
1. Student sees function signature (optionally)
2. Student probes oracle: enters input, gets output (sync API)
3. Probe limit enforced based on probe_mode
4. Student writes code implementing the behavior
5. Submit code (async): Tests against hidden test cases

Grading: Test pass rate
"""

import logging
import re
from typing import TYPE_CHECKING, Any

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


def _parse_function_params(signature: str) -> list[dict[str, str]]:
    """Parse function signature to extract parameter names and types."""
    match = re.search(r"\(([^)]*)\)", signature)
    if not match:
        return []
    params_str = match.group(1).strip()
    if not params_str:
        return []
    params = []
    for param in params_str.split(","):
        param = param.strip()
        if ":" in param:
            name, type_hint = param.split(":", 1)
            params.append({"name": name.strip(), "type": type_hint.strip()})
        else:
            params.append({"name": param, "type": "Any"})
    return params


@register_handler("probeable_code")
class ProbeableCodeHandler(ActivityHandler):
    """Handler for Probeable Code problems."""

    MIN_CODE_LENGTH = 10
    MAX_CODE_LENGTH = 10000

    @property
    def type_name(self) -> str:
        return "probeable_code"

    # --- Input Validation ---

    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate student code submission input."""
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
        Process Probeable Code submission.

        Note: This is a stub. Actual processing is handled by the
        execute_probeable_code_pipeline Celery task.
        """
        raise NotImplementedError(
            "Probeable Code processing is handled by execute_probeable_code_pipeline task."
        )

    # --- Grading ---

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for Probeable Code submission.

        Simple binary grading: all tests pass = complete, otherwise incomplete.
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if submission is correct (passes all tests)."""
        return submission.passed_all_tests

    # --- Completion Evaluation ---

    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """
        Evaluate completion status for progress tracking.

        For Probeable Code: Just correctness (no comprehension check).
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    # --- Data Extraction ---

    def extract_variations(self, submission: "Submission") -> list[str]:
        """
        Extract code from submission.

        Probeable Code has only one "variation" - the student's code.
        """
        if submission.processed_code:
            return [submission.processed_code]
        return []

    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> list[dict[str, Any]]:
        """Transform test execution to frontend format."""
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
        """Count total variations (always 1 for Probeable Code)."""
        return 1 if submission.processed_code else 0

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests (0 or 1)."""
        return 1 if submission.passed_all_tests else 0

    # --- API Configuration ---

    def get_problem_config(self, problem: "Problem") -> dict[str, Any]:
        """Return configuration for frontend rendering of Probeable Code problems."""
        # Get probe config from the problem model
        show_signature = getattr(problem, "show_function_signature", True)
        probe_mode = getattr(problem, "probe_mode", "explore")
        max_probes = getattr(problem, "max_probes", 10)
        cooldown_attempts = getattr(problem, "cooldown_attempts", 3)
        cooldown_refill = getattr(problem, "cooldown_refill", 5)

        return {
            "display": {
                "show_reference_code": False,  # Don't show oracle code
                "show_function_signature": show_signature,
                "code_read_only": False,  # Code is editable
                "section_label": "Discover the function behavior",
            },
            "input": {
                "type": "probeable_code",
                "language": "python",
                "label": "Write your implementation",
                "min_length": self.MIN_CODE_LENGTH,
                "max_length": self.MAX_CODE_LENGTH,
            },
            "probe": {
                "enabled": True,
                "mode": probe_mode,
                "max_probes": max_probes,
                "cooldown_attempts": cooldown_attempts,
                "cooldown_refill": cooldown_refill,
                "function_signature": (
                    problem.function_signature if show_signature else None
                ),
                "function_name": problem.function_name,
                "parameters": (
                    _parse_function_params(problem.function_signature)
                    if problem.function_signature
                    else []
                ),
            },
            "hints": {
                "available": [],  # No traditional hints for this type
                "enabled": False,
            },
            "feedback": {
                "show_variations": False,  # No LLM variations
                "show_segmentation": False,  # No comprehension analysis
                "show_test_results": True,
                "show_probe_history": True,  # Show past probe queries
            },
        }

    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize submission result for API response."""
        result = {
            "student_code": submission.processed_code or "",
            "test_results": [],
        }

        # Serialize test results using extract_test_results
        if hasattr(submission, "problem") and submission.problem:
            result["test_results"] = self.extract_test_results(
                submission, submission.problem
            )

        return result

    def get_admin_config(self) -> dict[str, Any]:
        """Return admin UI configuration for Probeable Code problems."""
        return {
            "hidden_sections": ["mcq_options", "image_config", "buggy_code"],
            "required_fields": ["title", "function_signature", "reference_solution"],
            "optional_fields": [
                "description",
                "tags",
                "categories",
                "probe_mode",
                "max_probes",
                "cooldown_attempts",
                "cooldown_refill",
                "show_function_signature",
            ],
            "type_specific_section": "probeable_code_config",
            "supports": {
                "hints": False,  # No traditional hints
                "segmentation": False,  # No comprehension analysis
                "test_cases": True,  # Uses test cases for code submission
            },
        }

    # --- Submission Execution ---

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "Problem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute Probeable Code submission asynchronously via Celery.

        Code submission requires async because it involves:
        - Docker containers for code execution
        - Test case execution
        """
        from purplex.problems_app.tasks.pipeline import execute_probeable_code_pipeline

        # Queue the Celery task
        task = execute_probeable_code_pipeline.apply_async(
            args=[
                problem.id,
                raw_input,  # The student's code
                context["user_id"],
                context.get("problem_set_id"),
                context.get("course_id"),
            ],
            task_id=context["request_id"],
        )

        logger.info(
            f"Probeable Code submission queued: task_id={task.id}, "
            f"problem={problem.slug}, user={context['user_id']}"
        )

        return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)
