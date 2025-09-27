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
        Handles migration of progress records without problem_set context.
        """
        from purplex.problems_app.models import UserProgress
        from django.db import transaction

        logger.info(f"Processing submission created event for {submission.submission_id}")

        with transaction.atomic():
            # If submission has problem_set, check for existing progress without it
            if submission.problem_set:
                try:
                    # Look for existing progress without problem_set context
                    old_progress = UserProgress.objects.select_for_update().get(
                        user=submission.user,
                        problem=submission.problem,
                        problem_set__isnull=True,
                        course=submission.course if submission.course else None
                    )
                    # Update it to include problem_set
                    old_progress.problem_set = submission.problem_set
                    old_progress.save()
                    progress = old_progress
                    created = False
                    logger.info(f"Updated existing progress record to include problem_set for user {submission.user.username}")
                except UserProgress.DoesNotExist:
                    # No existing progress without problem_set, proceed normally
                    progress, created = UserProgress.objects.get_or_create(
                        user=submission.user,
                        problem=submission.problem,
                        problem_set=submission.problem_set,
                        course=submission.course,
                        defaults={'problem_version': submission.problem.version}
                    )
            else:
                # No problem_set context, proceed normally
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
        Handles migration of progress records without problem_set context.
        """
        from purplex.problems_app.models import UserProgress, UserProblemSetProgress
        from .grading_service import GradingService
        from django.db import transaction

        with transaction.atomic():
            # First, try to get progress with full context
            progress, created = UserProgress.objects.get_or_create(
                user=submission.user,
                problem=submission.problem,
                problem_set=submission.problem_set,
                course=submission.course,
                defaults={'problem_version': submission.problem.version}
            )

            # If we just created a new progress record with problem_set context,
            # check if there's an existing one without problem_set that we should migrate
            if created and submission.problem_set:
                try:
                    # Look for existing progress without problem_set context
                    old_progress = UserProgress.objects.get(
                        user=submission.user,
                        problem=submission.problem,
                        problem_set__isnull=True,
                        course=submission.course if submission.course else None
                    )

                    # Migrate the old progress data to the new record
                    logger.info(f"Migrating progress data from record without problem_set to new record with problem_set")

                    # Copy all relevant fields
                    progress.attempts = old_progress.attempts
                    progress.best_score = old_progress.best_score
                    progress.average_score = old_progress.average_score
                    progress.status = old_progress.status
                    progress.is_completed = old_progress.is_completed
                    progress.completion_percentage = old_progress.completion_percentage
                    progress.first_attempt = old_progress.first_attempt
                    progress.last_attempt = old_progress.last_attempt
                    progress.completed_at = old_progress.completed_at
                    progress.total_time_spent = old_progress.total_time_spent
                    progress.hints_used = old_progress.hints_used
                    progress.days_to_complete = old_progress.days_to_complete
                    if hasattr(old_progress, 'grade'):
                        progress.grade = old_progress.grade

                    # Save the migrated progress
                    progress.save()

                    # Delete the old progress record
                    old_progress.delete()
                    logger.info(f"Successfully migrated and deleted old progress record for user {submission.user.username}")

                except UserProgress.DoesNotExist:
                    # No old progress to migrate, that's fine
                    pass
                except UserProgress.MultipleObjectsReturned:
                    # Multiple old progress records - log warning but continue
                    logger.warning(f"Multiple progress records without problem_set found for user {submission.user.username} and problem {submission.problem.slug}")

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