"""
Probeable Spec activity handler.

Like EiPL but student first discovers behavior via oracle probes,
THEN writes natural language explanation that gets converted to code by LLM.

Flow:
1. Student sees function signature (optionally)
2. Student probes oracle: enters input, gets output (sync API - reuses ProbeService)
3. Probe limit enforced based on probe_mode
4. Student writes NL explanation of the function
5. LLM generates code from explanation (reuses EiPL pipeline)
6. Code tested against test cases

Grading: Test pass + comprehension level (reuses EiPL logic)
"""

import logging
import re
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


def _parse_function_params(signature: str) -> List[Dict[str, str]]:
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


@register_handler("probeable_spec")
class ProbeableSpecHandler(ActivityHandler):
    """Handler for Probeable Spec problems.

    Combines probe discovery (from ProbeableCode) with NL explanation
    processing (from EiPL). Uses segmentation for comprehension analysis.
    """

    MIN_INPUT_LENGTH = 10
    MAX_INPUT_LENGTH = 1000

    @property
    def type_name(self) -> str:
        return "probeable_spec"

    # --- Input Validation ---

    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate NL description input (same as EiPL)."""
        text = raw_input.strip()

        if len(text) < self.MIN_INPUT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Description must be at least {self.MIN_INPUT_LENGTH} characters",
            )

        if len(text) > self.MAX_INPUT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error=f"Description must be under {self.MAX_INPUT_LENGTH} characters",
            )

        return ValidationResult(is_valid=True)

    # --- Submission Processing ---

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "Problem"
    ) -> ProcessingResult:
        """
        Process Probeable Spec submission.

        Note: Processing is handled by the execute_eipl_pipeline Celery task.
        The pipeline is identical to EiPL - NL -> LLM code generation -> testing.
        """
        raise NotImplementedError(
            "Probeable Spec processing is handled by execute_eipl_pipeline task. "
            "Direct handler processing not supported."
        )

    # --- Grading (reuses EiPL logic) ---

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for Probeable Spec submission.

        Grading Dimensions:
        1. Correctness: Must pass all tests
        2. High-levelness: If segmentation enabled, must meet threshold

        Returns: 'complete', 'partial', or 'incomplete'
        """
        # Dimension 1: Correctness
        if not submission.passed_all_tests:
            logger.debug(
                f"Submission {submission.submission_id}: incorrect (failed tests)"
            )
            return "incomplete"

        # Dimension 2: High-levelness (segmentation check)
        if not submission.problem.segmentation_enabled:
            logger.debug(
                f"Submission {submission.submission_id}: complete (segmentation disabled)"
            )
            return "complete"

        # Segmentation must exist when enabled
        if not hasattr(submission, "segmentation"):
            logger.warning(
                f"Submission {submission.submission_id}: incomplete (missing segmentation)"
            )
            return "incomplete"

        segmentation = submission.segmentation

        # Get threshold from problem configuration
        threshold = getattr(submission.problem, "segmentation_threshold", None)
        if threshold is None:
            threshold = submission.problem.segmentation_config.get("threshold", 2)

        # Apply threshold-based grading
        segment_count = segmentation.segment_count

        if segment_count <= threshold:
            logger.debug(
                f"Submission {submission.submission_id}: complete "
                f"(segments={segment_count} <= threshold={threshold})"
            )
            return "complete"  # Correct + high-level
        else:
            logger.debug(
                f"Submission {submission.submission_id}: partial "
                f"(segments={segment_count} > threshold={threshold})"
            )
            return "partial"  # Correct but low-level

    def is_correct(self, submission: "Submission") -> bool:
        """Check if submission is correct (passes all tests)."""
        return submission.passed_all_tests

    # --- Completion Evaluation ---

    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """
        Evaluate completion status for progress tracking.

        For Probeable Spec: Requires correctness + high-level comprehension (if enabled).

        Returns: 'complete', 'partial', or 'incomplete'
        """
        # Perfect test score required
        if submission.score < 100:
            return "incomplete"

        # If segmentation is enabled, must pass segmentation
        if problem.segmentation_enabled:
            if hasattr(submission, "segmentation") and submission.segmentation:
                return "complete" if submission.segmentation.passed else "partial"
            else:
                # No segmentation data when it's required
                return "incomplete"

        # All criteria met
        return "complete"

    # --- Data Extraction (reuses EiPL logic) ---

    def extract_variations(self, submission: "Submission") -> List[str]:
        """Extract code variations from submission."""
        variations = submission.code_variations.all().order_by("variation_index")
        return [v.generated_code for v in variations]

    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> List[Dict[str, Any]]:
        """Transform TestExecution objects to frontend format."""
        results = []

        # Group test results by code variation
        variations = submission.code_variations.all().order_by("variation_index")
        for variation in variations:
            test_execs = variation.test_executions.all().order_by("execution_order")
            var_results = []

            # If we have TestExecution records, use them
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
            # Fallback: If no TestExecution records exist but we have summary data
            elif variation.tests_total > 0:
                # Create placeholder results based on the summary
                for i in range(variation.tests_total):
                    is_passed = i < variation.tests_passed
                    var_results.append(
                        {
                            "isSuccessful": is_passed,
                            "function_call": f"{problem.function_name}(test_case_{i+1})",
                            "expected_output": "Test details not available",
                            "actual_output": "Passed" if is_passed else "Failed",
                            "error": (
                                ""
                                if is_passed
                                else "Test failed (details not available)"
                            ),
                        }
                    )

            results.append(
                {
                    "success": (
                        variation.tests_passed == variation.tests_total
                        and variation.tests_total > 0
                    ),
                    "testsPassed": variation.tests_passed,
                    "totalTests": variation.tests_total,
                    "test_results": var_results,
                    "results": var_results,  # Duplicate for frontend compatibility
                }
            )

        return results

    def count_variations(self, submission: "Submission") -> int:
        """Count total variations for submission."""
        return submission.code_variations.count()

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests."""
        from django.db import models

        return submission.code_variations.filter(
            tests_passed=models.F("tests_total"), tests_total__gt=0
        ).count()

    # --- API Configuration ---

    def get_problem_config(self, problem: "Problem") -> Dict[str, Any]:
        """Return configuration for frontend rendering of Probeable Spec problems."""
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
                "code_read_only": True,  # Read-only code display (if any)
                "section_label": "Discover and explain the function",
            },
            "input": {
                "type": "probeable_spec",  # Combined probe + NL input
                "label": "Describe what the function does",
                "placeholder": "This function...",
                "min_length": self.MIN_INPUT_LENGTH,
                "max_length": self.MAX_INPUT_LENGTH,
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
                "available": [],  # No traditional hints - probing is the discovery mechanism
                "enabled": False,
            },
            "feedback": {
                "show_variations": True,  # Show LLM-generated code
                "show_segmentation": problem.segmentation_enabled,  # Comprehension analysis
                "show_test_results": True,
                "show_probe_history": True,  # Show past probe queries
            },
        }

    def serialize_result(self, submission: "Submission") -> Dict[str, Any]:
        """Serialize submission result for API response (same as EiPL)."""
        result = {
            "variations": [],
            "test_results": [],
            "segmentation": None,
        }

        # Serialize variations
        if hasattr(submission, "code_variations"):
            result["variations"] = [
                {
                    "code": v.generated_code,
                    "score": v.score,
                    "tests_passed": v.tests_passed,
                    "tests_total": v.tests_total,
                    "is_selected": v.is_selected,
                }
                for v in submission.code_variations.all()
            ]

        # Serialize test results using extract_test_results
        if hasattr(submission, "problem") and submission.problem:
            result["test_results"] = self.extract_test_results(
                submission, submission.problem
            )

        # Serialize segmentation (full data for modal display)
        if hasattr(submission, "segmentation") and submission.segmentation:
            seg = submission.segmentation
            threshold = getattr(submission.problem, "segmentation_threshold", None)
            if threshold is None:
                threshold = submission.problem.segmentation_config.get("threshold", 2)

            result["segmentation"] = {
                "segment_count": seg.segment_count,
                "comprehension_level": seg.comprehension_level,
                "passed": seg.passed,
                "threshold": threshold,
                # Full data for SegmentAnalysisModal
                "segments": seg.segments,
                "code_mappings": seg.code_mappings,
                "feedback_message": seg.feedback_message,
                "confidence_score": seg.confidence_score,
                "suggested_improvements": seg.suggested_improvements,
            }

        return result

    def get_admin_config(self) -> Dict[str, Any]:
        """Return admin UI configuration for Probeable Spec problems."""
        return {
            "hidden_sections": ["mcq_options", "image_config", "buggy_code"],
            "required_fields": ["title", "function_signature", "reference_solution"],
            "optional_fields": [
                "description",
                "tags",
                "categories",
                "segmentation_config",
                "probe_mode",
                "max_probes",
                "cooldown_attempts",
                "cooldown_refill",
                "show_function_signature",
            ],
            "type_specific_section": "probeable_spec_config",
            "supports": {
                "hints": False,  # No traditional hints - probing is the discovery
                "segmentation": True,  # Uses comprehension analysis
                "test_cases": True,  # Uses test cases for code submission
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
        Execute Probeable Spec submission asynchronously via Celery.

        Reuses the EiPL pipeline since the NL -> code -> test flow is identical.
        The difference is how the student discovered what to describe (probing).
        """
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        # Queue the Celery task (same as EiPL)
        task = execute_eipl_pipeline.apply_async(
            args=[
                problem.id,
                raw_input,  # The student's NL description
                context["user_id"],
                context.get("problem_set_id"),
                context.get("course_id"),
            ],
            task_id=context["request_id"],
        )

        logger.info(
            f"Probeable Spec submission queued: task_id={task.id}, "
            f"problem={problem.slug}, user={context['user_id']}"
        )

        return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)
