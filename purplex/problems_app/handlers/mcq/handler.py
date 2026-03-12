"""
Handler for Multiple Choice Question (MCQ) activity type.

MCQ problems present a question with multiple options. Students select
one or more answers. Single-select MCQs are binary (correct/incorrect).
Multi-select MCQs (allow_multiple=True) use partial credit grading:
score = (# correct selected) / (# total correct), passed only on exact match.

MCQ uses synchronous processing - no Celery needed since it's just
comparing the selected answer(s) to the correct one(s).
"""

import json
import logging
import random
from typing import TYPE_CHECKING, Any, Union

from .. import register_handler
from ..base import (
    ActivityHandler,
    ProcessingResult,
    SubmissionOutcome,
    ValidationResult,
)

if TYPE_CHECKING:
    from purplex.problems_app.models import McqProblem, Problem
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


def _ensure_mcq_problem(problem: Union["Problem", "McqProblem"]) -> "McqProblem":
    """
    Ensure we have the actual McqProblem instance.

    When problems are accessed through related managers (e.g., problem_set.problems),
    django-polymorphic may return the base Problem type. This helper fetches
    the actual McqProblem instance via the repository.
    """
    from purplex.problems_app.models import McqProblem
    from purplex.problems_app.repositories import ProblemRepository

    if isinstance(problem, McqProblem):
        return problem

    # Duck-typing: if the object already has 'options' attribute (e.g., mock in tests),
    # use it directly without DB lookup
    if hasattr(problem, "options") and hasattr(problem, "allow_multiple"):
        return problem  # type: ignore

    # Fetch the actual McqProblem instance via repository
    mcq_problem = ProblemRepository.get_mcq_problem_by_pk(problem.pk)
    if mcq_problem is None:
        raise ValueError(f"Problem {problem.pk} is not an MCQ problem")
    return mcq_problem


def _get_correct_options(mcq: "McqProblem") -> list[dict]:
    """Return all options where is_correct=True."""
    return [opt for opt in mcq.options if opt.get("is_correct", False)]


def _parse_selected_ids(raw_input: str, allow_multiple: bool) -> list[str]:
    """
    Parse selected option IDs from raw input.

    For multi-select (allow_multiple=True): expects JSON array like '["a","b"]'.
    For single-select: expects plain string like "a".
    Falls back to single-element list on parse failure.
    """
    text = raw_input.strip()
    if allow_multiple:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        # Fallback: treat as single selection
        return [text] if text else []
    return [text] if text else []


@register_handler("mcq")
class MCQHandler(ActivityHandler):
    """Handler for Multiple Choice Question (MCQ) problems."""

    @property
    def type_name(self) -> str:
        return "mcq"

    # ─── Input Validation ───────────────────────────────────────

    def validate_input(self, raw_input: str, problem: "McqProblem") -> ValidationResult:
        """
        Validate MCQ answer input.

        Single-select: raw_input is a plain option ID (e.g., "1", "2").
        Multi-select: raw_input is a JSON array (e.g., '["1","3"]').
        """
        mcq = _ensure_mcq_problem(problem)
        text = raw_input.strip()

        if not text:
            return ValidationResult(is_valid=False, error="Please select an answer")

        if not mcq.options:
            return ValidationResult(
                is_valid=False, error="This problem has no answer options configured"
            )

        valid_ids = [str(opt.get("id", "")) for opt in mcq.options]
        selected_ids = _parse_selected_ids(text, mcq.allow_multiple)

        if not selected_ids:
            return ValidationResult(is_valid=False, error="Please select an answer")

        # Validate that all selected options exist
        for sid in selected_ids:
            if sid not in valid_ids:
                return ValidationResult(
                    is_valid=False,
                    error=f"Invalid option selected: {sid}. Valid options: {', '.join(valid_ids)}",
                )

        return ValidationResult(is_valid=True)

    # ─── Submission Processing ──────────────────────────────────

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "McqProblem"
    ) -> ProcessingResult:
        """
        Process MCQ submission.

        MCQ processing is synchronous and simple:
        1. Compare selected option(s) to correct answer(s)
        2. For multi-select: partial credit = (# correct selected) / (# total correct)
        """
        mcq = _ensure_mcq_problem(problem)
        correct_options = _get_correct_options(mcq)

        if not correct_options:
            logger.error(f"MCQ problem {mcq.slug} has no correct answer defined")
            return ProcessingResult(
                success=False,
                error="Problem configuration error: no correct answer defined",
            )

        selected_id_list = _parse_selected_ids(raw_input, mcq.allow_multiple)
        selected_ids = set(selected_id_list)
        correct_ids = {str(opt["id"]) for opt in correct_options}

        is_correct = selected_ids == correct_ids
        score_ratio = len(selected_ids & correct_ids) / len(correct_ids)

        # Backwards compat: singular fields use first element (stable order)
        first_selected = selected_id_list[0] if selected_id_list else ""
        first_correct = str(correct_options[0]["id"])

        return ProcessingResult(
            success=True,
            processed_code=raw_input.strip(),
            type_specific_data={
                "selected_option": first_selected,
                "correct_option": first_correct,
                "selected_options": sorted(selected_ids),
                "correct_options": sorted(correct_ids),
                "is_correct": is_correct,
                "partial_score": score_ratio,
            },
        )

    # ─── Grading ────────────────────────────────────────────────

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for MCQ submission.

        complete = exact match, partial = some correct, incomplete = none correct.
        """
        if submission.passed_all_tests:
            return "complete"
        score = getattr(submission, "score", 0)
        if isinstance(score, (int, float)) and score > 0:
            return "partial"
        return "incomplete"

    def is_correct(self, submission: "Submission") -> bool:
        """Check if MCQ submission is correct."""
        return submission.passed_all_tests

    # ─── Completion Evaluation ──────────────────────────────────

    def evaluate_completion(
        self, submission: "Submission", problem: "McqProblem"
    ) -> str:
        """
        Evaluate completion status for progress tracking.

        complete = exact match, partial = some correct, incomplete = none correct.
        """
        if submission.passed_all_tests:
            return "complete"
        score = getattr(submission, "score", 0)
        if isinstance(score, (int, float)) and score > 0:
            return "partial"
        return "incomplete"

    # ─── Data Extraction ────────────────────────────────────────

    def extract_variations(self, submission: "Submission") -> list[str]:
        """Extract variations from MCQ submission (returns single answer)."""
        return [submission.raw_input] if submission.raw_input else []

    def extract_test_results(
        self, submission: "Submission", problem: "McqProblem"
    ) -> list[dict[str, Any]]:
        """Extract test results for MCQ (single correct/incorrect result)."""
        mcq = _ensure_mcq_problem(problem)
        selected_ids = set(
            _parse_selected_ids(
                submission.raw_input.strip() if submission.raw_input else "",
                mcq.allow_multiple,
            )
        )

        # Find selected and correct options
        selected_options = [
            opt for opt in mcq.options if str(opt.get("id", "")) in selected_ids
        ]
        correct_options = _get_correct_options(mcq)

        selected_text = ", ".join(
            opt.get("text", str(opt.get("id", ""))) for opt in selected_options
        ) or str(selected_ids)
        correct_text = ", ".join(opt.get("text", "") for opt in correct_options)
        explanation = ", ".join(
            opt.get("explanation", "")
            for opt in correct_options
            if opt.get("explanation")
        )

        return [
            {
                "isSuccessful": submission.passed_all_tests,
                "selected_answer": selected_text,
                "correct_answer": correct_text,
                "explanation": explanation,
            }
        ]

    def count_variations(self, submission: "Submission") -> int:
        """MCQ has exactly 1 variation (the selected answer)."""
        return 1

    def count_passing_variations(self, submission: "Submission") -> int:
        """MCQ has 1 passing if correct, 0 if wrong."""
        return 1 if submission.passed_all_tests else 0

    # ─── API Configuration ──────────────────────────────────────

    def get_problem_config(self, problem: "McqProblem") -> dict[str, Any]:
        """Return configuration for frontend rendering of MCQ problems."""
        # Ensure we have the actual McqProblem instance with MCQ-specific fields
        mcq = _ensure_mcq_problem(problem)

        options_to_display = list(mcq.options)
        if mcq.shuffle_options:
            random.shuffle(options_to_display)

        return {
            "display": {
                "show_reference_code": False,
                "code_read_only": True,
                "show_function_signature": False,
                "section_label": "Select your answer",
            },
            "input": {
                "type": "checkbox" if mcq.allow_multiple else "radio",
                "label": "Select the correct answer",
                "options": [
                    {
                        "id": str(opt.get("id", "")),
                        "text": opt.get("text", ""),
                    }
                    for opt in options_to_display
                ],
            },
            "hints": {
                "available": [],
                "enabled": False,
            },
            "feedback": {
                "show_variations": False,
                "show_segmentation": False,
                "show_test_results": True,
                "show_correct_answer": True,
            },
        }

    def serialize_result(self, submission: "Submission") -> dict[str, Any]:
        """Serialize MCQ submission result for API response."""
        mcq = _ensure_mcq_problem(submission.problem)
        selected_ids = set(
            _parse_selected_ids(
                submission.raw_input.strip() if submission.raw_input else "",
                mcq.allow_multiple,
            )
        )

        # Find selected and correct options
        selected_options = [
            opt for opt in mcq.options if str(opt.get("id", "")) in selected_ids
        ]
        correct_options = _get_correct_options(mcq)

        # Backwards compat: singular fields use first element
        first_selected = selected_options[0] if selected_options else None
        first_correct = correct_options[0] if correct_options else None

        return {
            "selected_option": {
                "id": str(first_selected.get("id", "")) if first_selected else "",
                "text": first_selected.get("text", "") if first_selected else "",
            },
            "correct_option": {
                "id": str(first_correct.get("id", "")) if first_correct else "",
                "text": first_correct.get("text", "") if first_correct else "",
                "explanation": (
                    first_correct.get("explanation", "") if first_correct else ""
                ),
            },
            "selected_options": [
                {"id": str(opt.get("id", "")), "text": opt.get("text", "")}
                for opt in selected_options
            ],
            "correct_options": [
                {
                    "id": str(opt.get("id", "")),
                    "text": opt.get("text", ""),
                    "explanation": opt.get("explanation", ""),
                }
                for opt in correct_options
            ],
            "is_correct": submission.passed_all_tests,
        }

    def get_admin_config(self) -> dict[str, Any]:
        """Return admin UI configuration for MCQ problems."""
        return {
            "hidden_sections": ["code_solution", "test_cases", "segmentation"],
            "required_fields": ["title", "question_text", "options"],
            "optional_fields": [
                "tags",
                "categories",
                "allow_multiple",
                "shuffle_options",
            ],
            "type_specific_section": "options",
            "supports": {
                "hints": False,
                "segmentation": False,
                "test_cases": False,
            },
        }

    # ─── Submission Execution ─────────────────────────────────────

    def submit(
        self,
        submission: "Submission",
        raw_input: str,
        problem: "McqProblem",
        context: dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute MCQ submission synchronously.

        MCQ doesn't need Celery - it's just comparing the selected answer(s)
        to the correct one(s). This runs inline in the request.
        """
        mcq = _ensure_mcq_problem(problem)
        correct_options = _get_correct_options(mcq)

        if not correct_options:
            logger.error(f"MCQ problem {mcq.slug} has no correct answer defined")
            return SubmissionOutcome(
                complete=True,
                submission=submission,
                error="Problem configuration error: no correct answer defined",
            )

        selected_ids = set(_parse_selected_ids(raw_input, mcq.allow_multiple))
        correct_ids = {str(opt["id"]) for opt in correct_options}

        is_correct = selected_ids == correct_ids
        score_ratio = len(selected_ids & correct_ids) / len(correct_ids)
        score = int(score_ratio * 100)

        # Determine completion status
        if is_correct:
            completion_status = "complete"
        elif score > 0:
            completion_status = "partial"
        else:
            completion_status = "incomplete"

        # Update submission
        submission.processed_code = raw_input.strip()
        submission.score = score
        submission.passed_all_tests = is_correct
        submission.is_correct = is_correct
        submission.completion_status = completion_status
        submission.execution_status = "completed"
        submission.save()

        # Update progress
        from purplex.problems_app.services.progress_service import ProgressService

        ProgressService.process_submission(submission)

        logger.info(
            f"MCQ submission {submission.submission_id}: "
            f"selected={sorted(selected_ids)}, correct={is_correct}, score={score}"
        )

        # Build result data
        selected_opts = [
            opt for opt in mcq.options if str(opt.get("id", "")) in selected_ids
        ]

        # Backwards compat: singular fields
        first_selected = selected_opts[0] if selected_opts else None
        first_correct = correct_options[0]

        result_data = {
            "submission_id": str(submission.submission_id),
            "problem_type": "mcq",
            "score": score,
            "is_correct": is_correct,
            "completion_status": completion_status,
            "problem_slug": problem.slug,
            "user_input": raw_input,
            "selected_option": {
                "id": str(first_selected.get("id", "")) if first_selected else "",
                "text": first_selected.get("text", "") if first_selected else "",
            },
            "correct_option": {
                "id": str(first_correct.get("id", "")),
                "text": first_correct.get("text", ""),
                "explanation": first_correct.get("explanation", ""),
            },
            "selected_options": [
                {"id": str(opt.get("id", "")), "text": opt.get("text", "")}
                for opt in selected_opts
            ],
            "correct_options": [
                {
                    "id": str(opt.get("id", "")),
                    "text": opt.get("text", ""),
                    "explanation": opt.get("explanation", ""),
                }
                for opt in correct_options
            ],
            "result": self.serialize_result(submission),
        }

        return SubmissionOutcome(
            complete=True, submission=submission, result_data=result_data
        )
