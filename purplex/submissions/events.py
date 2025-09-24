"""Event handlers for submission lifecycle events."""

import logging
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class SubmissionEvents:
    """Centralized submission event handling."""

    @staticmethod
    def on_submission_created(submission):
        """
        Handle new submission creation (before testing).
        Just increment attempt counter, don't set status yet.
        """
        from purplex.problems_app.models import UserProgress

        logger.info(f"Processing submission created event for {submission.submission_id}")

        progress, created = UserProgress.objects.get_or_create(
            user=submission.user,
            problem=submission.problem,
            problem_set=submission.problem_set,
            course=submission.course,
            defaults={'problem_version': submission.problem.version}
        )

        # Only increment attempts and set first attempt
        progress.attempts += 1
        if not progress.first_attempt:
            progress.first_attempt = submission.submitted_at
        progress.last_attempt = submission.submitted_at

        # Don't set status here - wait for test results
        progress.save()

        logger.info(f"Updated attempt count to {progress.attempts} for user {submission.user.username}")

    @staticmethod
    def on_tests_completed(submission):
        """Handle test completion event."""
        logger.info(f"Processing tests completed event for {submission.submission_id}")
        SubmissionEvents._update_progress_from_submission(submission)

    @staticmethod
    def on_segmentation_completed(submission):
        """Handle segmentation analysis completion."""
        logger.info(f"Processing segmentation completed event for {submission.submission_id}")
        SubmissionEvents._update_progress_from_submission(submission)

    @staticmethod
    def _update_progress_from_submission(submission):
        """
        Update UserProgress based on current submission state.
        This is the main synchronization point.
        """
        from purplex.problems_app.models import UserProgress, UserProblemSetProgress
        from .grading_service import GradingService

        progress, created = UserProgress.objects.get_or_create(
            user=submission.user,
            problem=submission.problem,
            problem_set=submission.problem_set,
            course=submission.course,
            defaults={'problem_version': submission.problem.version}
        )

        # Update scores
        if submission.score > progress.best_score:
            progress.best_score = submission.score
            logger.info(f"Updated best score to {progress.best_score}")

        # Update average score
        if progress.attempts > 0:
            progress.average_score = (
                (progress.average_score * (progress.attempts - 1) + submission.score)
                / progress.attempts
            )

        # Update time tracking
        if submission.time_spent:
            progress.total_time_spent += submission.time_spent

        # Update hints used count
        progress.hints_used = submission.hint_activations.count()

        # Calculate grade using new GradingService
        grade = GradingService.calculate_grade(submission)
        old_grade = progress.grade if hasattr(progress, 'grade') else None
        progress.grade = grade

        # Update status for backward compatibility
        old_status = progress.status
        if grade == 'complete':
            progress.status = 'completed'
        elif grade == 'partial':
            progress.status = 'in_progress'
        else:
            # Check if user has attempts to determine status
            if progress.attempts > 0:
                progress.status = 'in_progress'
            else:
                progress.status = 'not_started'

        # Update completion percentage based on score
        progress.completion_percentage = progress.best_score

        # Update is_completed flag
        progress.is_completed = (grade == 'complete')

        # Update completion timestamp if newly completed
        if grade == 'complete' and not progress.completed_at:
            progress.completed_at = timezone.now()
            if progress.first_attempt:
                progress.days_to_complete = (progress.completed_at - progress.first_attempt).days
            logger.info(f"Problem completed for user {submission.user.username} with grade: {grade}")

        progress.save()

        if old_status != progress.status:
            logger.info(f"Progress status changed from {old_status} to {progress.status}")
        if old_grade != grade:
            logger.info(f"Grade changed from {old_grade} to {grade} for user {submission.user.username}")

        # Update problem set progress
        UserProblemSetProgress.update_from_progress(progress)