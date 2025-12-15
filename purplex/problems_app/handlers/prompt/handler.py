"""
Handler for Prompt (image-based EiPL) activity type.

Prompt problems present an image to students who must describe what it
represents in natural language. Reuses the EiPL pipeline for processing.

Prompt uses asynchronous processing via Celery (same as EiPL) because
it requires LLM calls and Docker code execution.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from .. import register_handler

if TYPE_CHECKING:
    from purplex.problems_app.models import Problem
    from purplex.submissions.models import Submission

from ..base import (
    ActivityHandler,
    ProcessingResult,
    SubmissionOutcome,
    ValidationResult,
)

logger = logging.getLogger(__name__)


@register_handler("prompt")
class PromptHandler(ActivityHandler):
    """Handler for Prompt (image-based EiPL) problems."""

    MIN_INPUT_LENGTH = 10
    MAX_INPUT_LENGTH = 1000

    @property
    def type_name(self) -> str:
        return "prompt"

    # --- Input Validation ---

    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate prompt description input (same rules as EiPL)."""
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
        Process prompt submission.

        Note: Processing is handled by the execute_eipl_pipeline Celery task.
        """
        raise NotImplementedError(
            "Prompt processing is handled by execute_eipl_pipeline task. "
            "Direct handler processing not supported."
        )

    # --- Grading (delegates to EiPL logic) ---

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for prompt submission.

        Same grading logic as EiPL:
        1. Correctness: Must pass all tests
        2. High-levelness: If segmentation enabled, must meet threshold
        """
        if not submission.passed_all_tests:
            logger.debug(
                f"Submission {submission.submission_id}: incorrect (failed tests)"
            )
            return "incomplete"

        if not submission.problem.segmentation_enabled:
            logger.debug(
                f"Submission {submission.submission_id}: complete (segmentation disabled)"
            )
            return "complete"

        if not hasattr(submission, "segmentation"):
            logger.warning(
                f"Submission {submission.submission_id}: incomplete (missing segmentation)"
            )
            return "incomplete"

        segmentation = submission.segmentation
        threshold = getattr(submission.problem, "segmentation_threshold", None)
        if threshold is None:
            threshold = submission.problem.segmentation_config.get("threshold", 2)

        segment_count = segmentation.segment_count

        if segment_count <= threshold:
            logger.debug(
                f"Submission {submission.submission_id}: complete "
                f"(segments={segment_count} <= threshold={threshold})"
            )
            return "complete"
        else:
            logger.debug(
                f"Submission {submission.submission_id}: partial "
                f"(segments={segment_count} > threshold={threshold})"
            )
            return "partial"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if prompt submission is correct (passes all tests)."""
        return submission.passed_all_tests

    # --- Completion Evaluation ---

    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """
        Evaluate completion status for progress tracking.

        Same logic as EiPL: requires correctness + high-level comprehension.
        """
        if submission.score < 100:
            return "incomplete"

        if problem.segmentation_enabled:
            if hasattr(submission, "segmentation") and submission.segmentation:
                return "complete" if submission.segmentation.passed else "partial"
            else:
                return "incomplete"

        return "complete"

    # --- Data Extraction (same as EiPL) ---

    def extract_variations(self, submission: "Submission") -> List[str]:
        """Extract code variations from prompt submission."""
        variations = submission.code_variations.all().order_by("variation_index")
        return [v.generated_code for v in variations]

    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> List[Dict[str, Any]]:
        """Transform TestExecution objects to frontend format."""
        results = []

        variations = submission.code_variations.all().order_by("variation_index")
        for variation in variations:
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
            elif variation.tests_total > 0:
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
                    "results": var_results,
                }
            )

        return results

    def count_variations(self, submission: "Submission") -> int:
        """Count total variations for prompt submission."""
        return submission.code_variations.count()

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests."""
        from django.db import models

        return submission.code_variations.filter(
            tests_passed=models.F("tests_total"), tests_total__gt=0
        ).count()

    # --- API Configuration ---

    def get_problem_config(self, problem: "Problem") -> Dict[str, Any]:
        """Return configuration for frontend rendering of prompt problems."""
        return {
            "display": {
                "show_reference_code": False,  # Don't show code
                "show_image": True,  # Show image instead
                "image_url": getattr(problem, "image_url", "") or "",
                "image_alt_text": getattr(problem, "image_alt_text", "Problem image")
                or "Problem image",
                "code_read_only": True,
                "show_function_signature": True,
                "section_label": "Describe the image here",
            },
            "input": {
                "type": "textarea",
                "label": "Describe what this image represents",
                "placeholder": "This represents...",
                "min_length": self.MIN_INPUT_LENGTH,
                "max_length": self.MAX_INPUT_LENGTH,
            },
            "hints": {
                "available": ["variable_fade", "subgoal_highlight", "suggested_trace"],
                "enabled": True,
            },
            "feedback": {
                "show_variations": True,
                "show_segmentation": problem.segmentation_enabled,
                "show_test_results": True,
            },
        }

    def serialize_result(self, submission: "Submission") -> Dict[str, Any]:
        """Serialize prompt submission result for API response."""
        result = {
            "variations": [],
            "test_results": [],
            "segmentation": None,
        }

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

        if hasattr(submission, "problem") and submission.problem:
            result["test_results"] = self.extract_test_results(
                submission, submission.problem
            )

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
                "segments": seg.segments,
                "code_mappings": seg.code_mappings,
                "feedback_message": seg.feedback_message,
                "confidence_score": seg.confidence_score,
                "suggested_improvements": seg.suggested_improvements,
            }

        return result

    def get_admin_config(self) -> Dict[str, Any]:
        """Return admin UI configuration for prompt problems."""
        return {
            "hidden_sections": [],
            "required_fields": [
                "title",
                "function_signature",
                "reference_solution",
                "image_url",
            ],
            "optional_fields": [
                "image_alt_text",
                "tags",
                "categories",
                "segmentation_config",
            ],
            "type_specific_section": "prompt_image",
            "supports": {
                "hints": True,
                "segmentation": True,
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
        Execute Prompt submission asynchronously via Celery.

        Prompt reuses the EiPL pipeline since the processing is identical
        (LLM code generation, Docker execution, segmentation).
        """
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        # Queue the Celery task (reuses EiPL pipeline)
        task = execute_eipl_pipeline.apply_async(
            args=[
                problem.id,
                raw_input,
                context["user_id"],
                context.get("problem_set_id"),
                context.get("course_id"),
            ],
            task_id=context["request_id"],
        )

        logger.info(
            f"Prompt submission queued: task_id={task.id}, "
            f"problem={problem.slug}, user={context['user_id']}"
        )

        return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)
