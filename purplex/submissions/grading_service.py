"""
Centralized grading service implementing GRADING_PIPELINE.md specifications.

This service delegates to activity type handlers for type-specific grading logic.
"""

import logging

from purplex.problems_app.handlers import get_handler

logger = logging.getLogger(__name__)


class GradingService:
    """
    Single source of truth for grading logic per GRADING_PIPELINE.md.

    Delegates to activity type handlers for type-specific grading.

    Grading Outcomes:
    - complete: correct and high-level
    - partial: correct but low-level
    - incomplete: incorrect
    """

    @staticmethod
    def calculate_grade(submission) -> str:
        """
        Calculate grade for a submission by delegating to the appropriate handler.

        Args:
            submission: Submission instance with test results and optional segmentation

        Returns:
            Grade string: 'complete', 'partial', or 'incomplete'
        """
        handler = get_handler(submission.problem.problem_type)
        return handler.calculate_grade(submission)

    @staticmethod
    def is_correct(submission) -> bool:
        """
        Check if submission is correct by delegating to the appropriate handler.

        Args:
            submission: Submission instance

        Returns:
            True if submission meets correctness criteria
        """
        handler = get_handler(submission.problem.problem_type)
        return handler.is_correct(submission)
