"""Centralized service for evaluating submission and progress completion status."""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CompletionStatus(Enum):
    """Submission completion states."""
    INCOMPLETE = 'incomplete'
    PARTIAL = 'partial'
    PENDING = 'pending'
    COMPLETE = 'complete'


class CompletionEvaluator:
    """Single source of truth for completion rules."""

    @staticmethod
    def evaluate_submission(submission) -> CompletionStatus:
        """
        Determine if a single submission meets completion criteria.

        Args:
            submission: Submission instance to evaluate

        Returns:
            CompletionStatus enum value
        """
        problem = submission.problem

        # Rule 1: Must pass all tests as baseline
        if not submission.passed_all_tests:
            return CompletionStatus.INCOMPLETE

        # Rule 2: For EiPL problems, must achieve relational understanding
        if problem.problem_type == 'eipl' and problem.segmentation_enabled:
            # Check if segmentation analysis exists
            if hasattr(submission, 'segmentation'):
                segmentation = submission.segmentation
                if segmentation.comprehension_level == 'relational':
                    return CompletionStatus.COMPLETE
                else:
                    # Tests pass but comprehension insufficient
                    return CompletionStatus.PARTIAL
            else:
                # Awaiting segmentation analysis
                return CompletionStatus.PENDING

        # Rule 3: Non-EiPL problems just need to pass tests
        return CompletionStatus.COMPLETE

    @staticmethod
    def compute_user_progress_status(user_progress) -> str:
        """
        Derive progress status from submissions.

        Args:
            user_progress: UserProgress instance

        Returns:
            Status string: 'not_started', 'in_progress', or 'completed'
        """
        from .models import Submission

        if user_progress.attempts == 0:
            return 'not_started'

        # Get ALL submissions for this problem/user/context
        submissions = Submission.objects.filter(
            user=user_progress.user,
            problem=user_progress.problem,
            problem_set=user_progress.problem_set,
            course=user_progress.course
        ).order_by('-score', '-submitted_at')

        if not submissions.exists():
            return 'not_started'

        # Check if ANY submission meets completion criteria
        # This prevents later incomplete submissions from overriding completion
        for submission in submissions:
            completion = CompletionEvaluator.evaluate_submission(submission)
            if completion == CompletionStatus.COMPLETE:
                return 'completed'

        # If no complete submissions, use the best submission's status
        best_submission = submissions.first()
        completion = CompletionEvaluator.evaluate_submission(best_submission)

        # Map completion status to progress status
        status_mapping = {
            CompletionStatus.COMPLETE: 'completed',
            CompletionStatus.PARTIAL: 'in_progress',
            CompletionStatus.INCOMPLETE: 'in_progress',
            CompletionStatus.PENDING: 'in_progress'
        }

        return status_mapping[completion]