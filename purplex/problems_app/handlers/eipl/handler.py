"""
Handler for Explain in Plain Language (EiPL) activity type.

EiPL problems present code to students who must describe what it does in
natural language. The system generates code variations from the description
and runs tests to verify understanding.

EiPL uses asynchronous processing via Celery because it requires:
- LLM calls for code generation
- Docker containers for code execution
- Segmentation analysis
"""

import logging
from typing import TYPE_CHECKING, Any

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


@register_handler("eipl")
class EiPLHandler(ActivityHandler):
    """Handler for Explain in Plain Language (EiPL) problems."""

    MIN_INPUT_LENGTH = 10
    MAX_INPUT_LENGTH = 1000

    @property
    def type_name(self) -> str:
        return "eipl"

    # ─── Input Validation ───────────────────────────────────────

    def validate_input(self, raw_input: str, problem: "Problem") -> ValidationResult:
        """Validate EiPL description input."""
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

        # Prompt injection heuristic — log only, don't block
        # (avoids false positives on legitimate code descriptions)
        from purplex.utils.prompt_sanitizer import PromptSanitizer

        PromptSanitizer.analyze(text)

        return ValidationResult(is_valid=True)

    # ─── Submission Processing ──────────────────────────────────

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "Problem"
    ) -> ProcessingResult:
        """
        Process EiPL submission.

        Note: In Phase 1, this is a stub. Full implementation requires
        pipeline integration (Phase 2+). Currently, processing is handled
        by the execute_eipl_pipeline Celery task.
        """
        raise NotImplementedError(
            "EiPL processing is handled by execute_eipl_pipeline task. "
            "Direct handler processing will be available in Phase 2."
        )

    # ─── Grading ────────────────────────────────────────────────

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for EiPL submission.

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

        # Get threshold (DB field is single source of truth)
        threshold = submission.problem.get_segmentation_threshold

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
        """Check if EiPL submission is correct (passes all tests)."""
        return submission.passed_all_tests

    # ─── Completion Evaluation ──────────────────────────────────

    def evaluate_completion(self, submission: "Submission", problem: "Problem") -> str:
        """
        Evaluate completion status for progress tracking.

        For EiPL: Requires correctness + high-level comprehension (if enabled).

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

    # ─── Data Extraction ────────────────────────────────────────

    def extract_variations(self, submission: "Submission") -> list[str]:
        """Extract code variations from EiPL submission."""
        variations = submission.code_variations.all().order_by("variation_index")
        return [v.generated_code for v in variations]

    def extract_test_results(
        self, submission: "Submission", problem: "Problem"
    ) -> list[dict[str, Any]]:
        """Transform TestExecution objects to frontend format for EiPL."""
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
        """Count total variations for EiPL submission."""
        return submission.code_variations.count()

    def count_passing_variations(self, submission: "Submission") -> int:
        """Count variations that pass all tests."""
        from django.db import models

        return submission.code_variations.filter(
            tests_passed=models.F("tests_total"), tests_total__gt=0
        ).count()

    # ─── API Configuration ──────────────────────────────────────

    def get_problem_config(self, problem: "Problem") -> dict[str, Any]:
        """Return configuration for frontend rendering of EiPL problems."""
        return {
            "display": {
                "show_reference_code": True,
                "code_read_only": True,
                "show_function_signature": True,
                "section_label": "Describe the code here",
            },
            "input": {
                "type": "textarea",
                "label": "Describe what this code does",
                "placeholder": "This function...",
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

    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize EiPL submission result for API response."""
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
            threshold = submission.problem.get_segmentation_threshold

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

    def get_admin_config(self) -> dict[str, Any]:
        """Return admin UI configuration for EiPL problems."""
        return {
            "hidden_sections": [],
            "required_fields": ["title", "function_signature", "reference_solution"],
            "optional_fields": [
                "description",
                "tags",
                "categories",
                "segmentation_config",
            ],
            "type_specific_section": None,  # Uses standard code editor
            "supports": {
                "hints": True,
                "segmentation": True,
                "test_cases": True,
            },
        }

    # ─── Submission Execution ─────────────────────────────────────

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "Problem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute EiPL submission asynchronously via Celery.

        EiPL requires async because it involves:
        - LLM API calls for code variation generation
        - Docker containers for code execution
        - Segmentation analysis

        IMPORTANT: We pass submission_id to the pipeline so it UPDATES the existing
        submission created by the view, instead of creating a duplicate.
        """
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        # Queue the Celery task with submission_id to prevent duplicates
        task = execute_eipl_pipeline.apply_async(
            args=[
                problem.id,
                raw_input,
                context["user_id"],
                context.get("problem_set_id"),
                context.get("course_id"),
                str(submission.submission_id),  # CRITICAL: Pass existing submission ID
            ],
            task_id=context["request_id"],
        )

        logger.info(
            f"EiPL submission queued: task_id={task.id}, "
            f"problem={problem.slug}, user={context['user_id']}, "
            f"submission_id={submission.submission_id}"
        )

        return SubmissionOutcome(complete=False, submission=submission, task_id=task.id)
