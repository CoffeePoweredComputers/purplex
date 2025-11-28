"""
Handler for Multiple Choice Question (MCQ) activity type.

MCQ problems present a question with multiple options. Students select
one answer, and grading is deterministic (correct/incorrect).
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from ..base import ActivityHandler, ProcessingResult, ValidationResult
from .. import register_handler

if TYPE_CHECKING:
    from problems_app.models import Problem
    from submissions.models import Submission

logger = logging.getLogger(__name__)


@register_handler('mcq')
class MCQHandler(ActivityHandler):
    """Handler for Multiple Choice Question (MCQ) problems."""

    @property
    def type_name(self) -> str:
        return 'mcq'

    # ─── Input Validation ───────────────────────────────────────

    def validate_input(self, raw_input: str, problem: 'Problem') -> ValidationResult:
        """
        Validate MCQ answer input.

        raw_input should be the selected option ID (e.g., "1", "2", "A", "B").
        """
        text = raw_input.strip()

        if not text:
            return ValidationResult(
                is_valid=False,
                error="Please select an answer"
            )

        # Get MCQ options from problem
        mcq_options = getattr(problem, 'mcq_options', None) or []

        if not mcq_options:
            return ValidationResult(
                is_valid=False,
                error="This problem has no answer options configured"
            )

        # Validate that the selected option exists
        valid_ids = [str(opt.get('id', '')) for opt in mcq_options]
        if text not in valid_ids:
            return ValidationResult(
                is_valid=False,
                error=f"Invalid option selected. Valid options: {', '.join(valid_ids)}"
            )

        return ValidationResult(is_valid=True)

    # ─── Submission Processing ──────────────────────────────────

    def process_submission(
        self,
        submission: 'Submission',
        raw_input: str,
        problem: 'Problem'
    ) -> ProcessingResult:
        """
        Process MCQ submission.

        MCQ processing is synchronous and simple:
        1. Compare selected option to correct answer
        2. Update submission fields
        """
        selected_id = raw_input.strip()
        mcq_options = getattr(problem, 'mcq_options', None) or []

        # Find correct answer
        correct_option = next(
            (opt for opt in mcq_options if opt.get('is_correct', False)),
            None
        )

        if not correct_option:
            logger.error(f"MCQ problem {problem.slug} has no correct answer defined")
            return ProcessingResult(
                success=False,
                error="Problem configuration error: no correct answer defined"
            )

        # Check if answer is correct
        is_correct = selected_id == str(correct_option.get('id', ''))

        return ProcessingResult(
            success=True,
            processed_code=selected_id,  # Store selected option
            type_specific_data={
                'selected_option': selected_id,
                'correct_option': str(correct_option.get('id', '')),
                'is_correct': is_correct,
            }
        )

    # ─── Grading ────────────────────────────────────────────────

    def calculate_grade(self, submission: 'Submission') -> str:
        """
        Calculate grade for MCQ submission.

        MCQ grading is binary: complete (correct) or incomplete (wrong).
        """
        if submission.passed_all_tests:
            return 'complete'
        return 'incomplete'

    def is_correct(self, submission: 'Submission') -> bool:
        """Check if MCQ submission is correct."""
        return submission.passed_all_tests

    # ─── Completion Evaluation ──────────────────────────────────

    def evaluate_completion(
        self,
        submission: 'Submission',
        problem: 'Problem'
    ) -> str:
        """
        Evaluate completion status for progress tracking.

        For MCQ: Just correctness check.
        """
        if submission.passed_all_tests:
            return 'complete'
        return 'incomplete'

    # ─── Data Extraction ────────────────────────────────────────

    def extract_variations(self, submission: 'Submission') -> List[str]:
        """Extract variations from MCQ submission (returns single answer)."""
        return [submission.raw_input] if submission.raw_input else []

    def extract_test_results(
        self,
        submission: 'Submission',
        problem: 'Problem'
    ) -> List[Dict[str, Any]]:
        """Extract test results for MCQ (single correct/incorrect result)."""
        mcq_options = getattr(problem, 'mcq_options', None) or []
        selected_id = submission.raw_input.strip() if submission.raw_input else ''

        # Find selected and correct options
        selected_option = next(
            (opt for opt in mcq_options if str(opt.get('id', '')) == selected_id),
            None
        )
        correct_option = next(
            (opt for opt in mcq_options if opt.get('is_correct', False)),
            None
        )

        return [{
            'isSuccessful': submission.passed_all_tests,
            'selected_answer': selected_option.get('text', selected_id) if selected_option else selected_id,
            'correct_answer': correct_option.get('text', '') if correct_option else '',
            'explanation': correct_option.get('explanation', '') if correct_option else '',
        }]

    def count_variations(self, submission: 'Submission') -> int:
        """MCQ has exactly 1 variation (the selected answer)."""
        return 1

    def count_passing_variations(self, submission: 'Submission') -> int:
        """MCQ has 1 passing if correct, 0 if wrong."""
        return 1 if submission.passed_all_tests else 0

    # ─── API Configuration ──────────────────────────────────────

    def get_problem_config(self, problem: 'Problem') -> Dict[str, Any]:
        """Return configuration for frontend rendering of MCQ problems."""
        mcq_options = getattr(problem, 'mcq_options', None) or []

        return {
            'display': {
                'show_reference_code': False,  # MCQ typically doesn't show code
                'code_read_only': True,
                'show_function_signature': False,
            },
            'input': {
                'type': 'radio',  # Radio button selection
                'label': 'Select the correct answer',
                'options': [
                    {
                        'id': str(opt.get('id', '')),
                        'text': opt.get('text', ''),
                    }
                    for opt in mcq_options
                ],
            },
            'hints': {
                'available': [],  # MCQ typically doesn't use hints
                'enabled': False,
            },
            'feedback': {
                'show_variations': False,
                'show_segmentation': False,
                'show_test_results': True,
                'show_correct_answer': True,  # Show correct answer after submission
            }
        }

    def serialize_result(self, submission: 'Submission') -> Dict[str, Any]:
        """Serialize MCQ submission result for API response."""
        problem = submission.problem
        mcq_options = getattr(problem, 'mcq_options', None) or []
        selected_id = submission.raw_input.strip() if submission.raw_input else ''

        # Find selected and correct options
        selected_option = next(
            (opt for opt in mcq_options if str(opt.get('id', '')) == selected_id),
            None
        )
        correct_option = next(
            (opt for opt in mcq_options if opt.get('is_correct', False)),
            None
        )

        return {
            'selected_option': {
                'id': selected_id,
                'text': selected_option.get('text', '') if selected_option else '',
            },
            'correct_option': {
                'id': str(correct_option.get('id', '')) if correct_option else '',
                'text': correct_option.get('text', '') if correct_option else '',
                'explanation': correct_option.get('explanation', '') if correct_option else '',
            },
            'is_correct': submission.passed_all_tests,
        }

    def get_admin_config(self) -> Dict[str, Any]:
        """Return admin UI configuration for MCQ problems."""
        return {
            'hidden_sections': ['code_solution', 'test_cases', 'segmentation'],
            'required_fields': ['title', 'mcq_options'],
            'optional_fields': ['description', 'tags', 'categories'],
            'type_specific_section': 'mcq_options',
            'supports': {
                'hints': False,
                'segmentation': False,
                'test_cases': False,
            }
        }
