"""
Handler for Multiple Choice Question (MCQ) activity type.

MCQ problems present a question with multiple options. Students select
one answer, and grading is deterministic (correct/incorrect).

MCQ uses synchronous processing - no Celery needed since it's just
comparing the selected answer to the correct one.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Union

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

        raw_input should be the selected option ID (e.g., "1", "2", "A", "B").
        """
        mcq = _ensure_mcq_problem(problem)
        text = raw_input.strip()

        if not text:
            return ValidationResult(is_valid=False, error="Please select an answer")

        if not mcq.options:
            return ValidationResult(
                is_valid=False, error="This problem has no answer options configured"
            )

        # Validate that the selected option exists
        valid_ids = [str(opt.get("id", "")) for opt in mcq.options]
        if text not in valid_ids:
            return ValidationResult(
                is_valid=False,
                error=f"Invalid option selected. Valid options: {', '.join(valid_ids)}",
            )

        return ValidationResult(is_valid=True)

    # ─── Submission Processing ──────────────────────────────────

    def process_submission(
        self, submission: "Submission", raw_input: str, problem: "McqProblem"
    ) -> ProcessingResult:
        """
        Process MCQ submission.

        MCQ processing is synchronous and simple:
        1. Compare selected option to correct answer
        2. Update submission fields
        """
        mcq = _ensure_mcq_problem(problem)
        selected_id = raw_input.strip()

        # Find correct answer
        correct_option = next(
            (opt for opt in mcq.options if opt.get("is_correct", False)), None
        )

        if not correct_option:
            logger.error(f"MCQ problem {mcq.slug} has no correct answer defined")
            return ProcessingResult(
                success=False,
                error="Problem configuration error: no correct answer defined",
            )

        # Check if answer is correct
        is_correct = selected_id == str(correct_option.get("id", ""))

        return ProcessingResult(
            success=True,
            processed_code=selected_id,
            type_specific_data={
                "selected_option": selected_id,
                "correct_option": str(correct_option.get("id", "")),
                "is_correct": is_correct,
            },
        )

    # ─── Grading ────────────────────────────────────────────────

    def calculate_grade(self, submission: "Submission") -> str:
        """
        Calculate grade for MCQ submission.

        MCQ grading is binary: complete (correct) or incomplete (wrong).
        """
        if submission.passed_all_tests:
            return "complete"
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

        For MCQ: Just correctness check.
        """
        if submission.passed_all_tests:
            return "complete"
        return "incomplete"

    # ─── Data Extraction ────────────────────────────────────────

    def extract_variations(self, submission: "Submission") -> List[str]:
        """Extract variations from MCQ submission (returns single answer)."""
        return [submission.raw_input] if submission.raw_input else []

    def extract_test_results(
        self, submission: "Submission", problem: "McqProblem"
    ) -> List[Dict[str, Any]]:
        """Extract test results for MCQ (single correct/incorrect result)."""
        mcq = _ensure_mcq_problem(problem)
        selected_id = submission.raw_input.strip() if submission.raw_input else ""

        # Find selected and correct options
        selected_option = next(
            (opt for opt in mcq.options if str(opt.get("id", "")) == selected_id), None
        )
        correct_option = next(
            (opt for opt in mcq.options if opt.get("is_correct", False)), None
        )

        return [
            {
                "isSuccessful": submission.passed_all_tests,
                "selected_answer": (
                    selected_option.get("text", selected_id)
                    if selected_option
                    else selected_id
                ),
                "correct_answer": (
                    correct_option.get("text", "") if correct_option else ""
                ),
                "explanation": (
                    correct_option.get("explanation", "") if correct_option else ""
                ),
            }
        ]

    def count_variations(self, submission: "Submission") -> int:
        """MCQ has exactly 1 variation (the selected answer)."""
        return 1

    def count_passing_variations(self, submission: "Submission") -> int:
        """MCQ has 1 passing if correct, 0 if wrong."""
        return 1 if submission.passed_all_tests else 0

    # ─── API Configuration ──────────────────────────────────────

    def get_problem_config(self, problem: "McqProblem") -> Dict[str, Any]:
        """Return configuration for frontend rendering of MCQ problems."""
        # Ensure we have the actual McqProblem instance with MCQ-specific fields
        mcq = _ensure_mcq_problem(problem)

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
                    for opt in mcq.options
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

    def serialize_result(self, submission: "Submission") -> Dict[str, Any]:
        """Serialize MCQ submission result for API response."""
        mcq = _ensure_mcq_problem(submission.problem)
        selected_id = submission.raw_input.strip() if submission.raw_input else ""

        # Find selected and correct options
        selected_option = next(
            (opt for opt in mcq.options if str(opt.get("id", "")) == selected_id), None
        )
        correct_option = next(
            (opt for opt in mcq.options if opt.get("is_correct", False)), None
        )

        return {
            "selected_option": {
                "id": selected_id,
                "text": selected_option.get("text", "") if selected_option else "",
            },
            "correct_option": {
                "id": str(correct_option.get("id", "")) if correct_option else "",
                "text": correct_option.get("text", "") if correct_option else "",
                "explanation": (
                    correct_option.get("explanation", "") if correct_option else ""
                ),
            },
            "is_correct": submission.passed_all_tests,
        }

    def get_admin_config(self) -> Dict[str, Any]:
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
        context: Dict[str, Any],
    ) -> SubmissionOutcome:
        """
        Execute MCQ submission synchronously.

        MCQ doesn't need Celery - it's just comparing the selected answer
        to the correct one. This runs inline in the request.
        """
        mcq = _ensure_mcq_problem(problem)
        selected_id = raw_input.strip()

        # Find correct option
        correct_option = next(
            (opt for opt in mcq.options if opt.get("is_correct", False)), None
        )

        if not correct_option:
            logger.error(f"MCQ problem {mcq.slug} has no correct answer defined")
            return SubmissionOutcome(
                complete=True,
                submission=submission,
                error="Problem configuration error: no correct answer defined",
            )

        # Check answer
        is_correct = selected_id == str(correct_option.get("id", ""))
        score = 100 if is_correct else 0

        # Update submission
        submission.processed_code = selected_id
        submission.score = score
        submission.passed_all_tests = is_correct
        submission.is_correct = is_correct
        submission.completion_status = "complete" if is_correct else "incomplete"
        submission.execution_status = "completed"
        submission.save()

        # Update progress
        from purplex.problems_app.services.progress_service import ProgressService

        ProgressService.process_submission(submission)

        logger.info(
            f"MCQ submission {submission.submission_id}: "
            f"selected={selected_id}, correct={is_correct}, score={score}"
        )

        # Build result data
        selected_opt = next(
            (opt for opt in mcq.options if str(opt.get("id", "")) == selected_id), None
        )

        result_data = {
            "submission_id": str(submission.submission_id),
            "problem_type": "mcq",
            "score": score,
            "is_correct": is_correct,
            "completion_status": submission.completion_status,
            "problem_slug": problem.slug,
            "user_input": raw_input,
            "selected_option": {
                "id": selected_id,
                "text": selected_opt.get("text", "") if selected_opt else "",
            },
            "correct_option": {
                "id": str(correct_option.get("id", "")),
                "text": correct_option.get("text", ""),
                "explanation": correct_option.get("explanation", ""),
            },
            "result": self.serialize_result(submission),
        }

        return SubmissionOutcome(
            complete=True, submission=submission, result_data=result_data
        )
