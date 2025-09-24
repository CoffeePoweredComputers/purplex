"""
Centralized grading service implementing GRADING_PIPELINE.md specifications.

This is the single source of truth for grading logic in the system.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GradingService:
    """
    Single source of truth for grading logic per GRADING_PIPELINE.md.

    Grading Dimensions:
    1. Correctness: Solution passes all test cases
    2. High-levelness: For EiPL problems, segmentation meets threshold

    Grading Outcomes:
    - complete: correct and high-level
    - partial: correct but low-level
    - incomplete: incorrect
    """

    @staticmethod
    def calculate_grade(submission) -> str:
        """
        Calculate grade for a submission based on GRADING_PIPELINE.md rules.

        Args:
            submission: Submission instance with test results and optional segmentation

        Returns:
            Grade string: 'complete', 'partial', or 'incomplete'
        """
        # Dimension 1: Correctness
        # The submission must pass all test cases to be considered correct
        if not submission.passed_all_tests:
            logger.debug(f"Submission {submission.submission_id}: incorrect (failed tests)")
            return 'incomplete'

        # For non-EiPL problems, correctness is sufficient for completion
        if submission.problem.problem_type != 'eipl':
            logger.debug(f"Submission {submission.submission_id}: complete (non-EiPL, passed tests)")
            return 'complete'

        # Dimension 2: High-levelness (EiPL problems only)
        # Check if segmentation is required and enabled
        if not submission.problem.segmentation_enabled:
            logger.debug(f"Submission {submission.submission_id}: complete (EiPL, segmentation disabled)")
            return 'complete'

        # Segmentation must exist for EiPL problems with segmentation enabled
        if not hasattr(submission, 'segmentation'):
            logger.warning(f"Submission {submission.submission_id}: incomplete (EiPL, missing segmentation)")
            return 'incomplete'

        segmentation = submission.segmentation

        # Get threshold from problem configuration
        # First try direct field (future), then fall back to JSON config
        threshold = getattr(submission.problem, 'segmentation_threshold', None)
        if threshold is None:
            threshold = submission.problem.segmentation_config.get('threshold', 2)

        # Apply threshold-based grading
        segment_count = segmentation.segment_count

        if segment_count <= threshold:
            logger.debug(
                f"Submission {submission.submission_id}: complete "
                f"(segments={segment_count} <= threshold={threshold})"
            )
            return 'complete'  # Correct + high-level
        else:
            logger.debug(
                f"Submission {submission.submission_id}: partial "
                f"(segments={segment_count} > threshold={threshold})"
            )
            return 'partial'  # Correct but low-level

    @staticmethod
    def grade_from_dimensions(
        is_correct: bool,
        problem_type: str,
        segment_count: Optional[int] = None,
        threshold: Optional[int] = None,
        segmentation_enabled: bool = True
    ) -> str:
        """
        Calculate grade from individual dimensions (for testing/preview).

        Args:
            is_correct: Whether all tests pass
            problem_type: Type of problem ('eipl' or other)
            segment_count: Number of segments (for EiPL)
            threshold: Segmentation threshold (for EiPL)
            segmentation_enabled: Whether segmentation is required

        Returns:
            Grade string: 'complete', 'partial', or 'incomplete'
        """
        # Must be correct as baseline
        if not is_correct:
            return 'incomplete'

        # Non-EiPL problems only need correctness
        if problem_type != 'eipl':
            return 'complete'

        # EiPL without segmentation requirement
        if not segmentation_enabled:
            return 'complete'

        # EiPL with segmentation requirement
        if segment_count is None:
            return 'incomplete'  # Missing required segmentation

        # Apply threshold (default to 2 if not specified)
        effective_threshold = threshold or 2

        if segment_count <= effective_threshold:
            return 'complete'
        else:
            return 'partial'

    @staticmethod
    def get_grade_display_name(grade: str) -> str:
        """
        Get human-readable display name for a grade.

        Args:
            grade: Grade string

        Returns:
            Display name string
        """
        display_names = {
            'complete': 'Complete',
            'partial': 'Partially Complete',
            'incomplete': 'Incomplete'
        }
        return display_names.get(grade, grade.title())

    @staticmethod
    def is_passing_grade(grade: str) -> bool:
        """
        Check if a grade is considered passing.

        Args:
            grade: Grade string

        Returns:
            True if grade is 'complete', False otherwise
        """
        return grade == 'complete'

    @staticmethod
    def get_grade_feedback(grade: str, segment_count: Optional[int] = None, threshold: Optional[int] = None) -> str:
        """
        Generate feedback message for a grade.

        Args:
            grade: Grade string
            segment_count: Number of segments (for partial grades)
            threshold: Threshold for high-level comprehension

        Returns:
            Feedback message string
        """
        if grade == 'complete':
            return "Excellent! Your solution is correct and demonstrates high-level understanding."
        elif grade == 'partial':
            if segment_count is not None and threshold is not None:
                return (
                    f"Good work! Your solution is correct but uses {segment_count} segments. "
                    f"Try to describe it in {threshold} or fewer segments for full credit."
                )
            else:
                return "Your solution is correct but could demonstrate better high-level understanding."
        else:  # incomplete
            return "Your solution does not pass all test cases. Please review and try again."