"""
Unified Progress Engine - Single source of truth for all progress operations.
This replaces the scattered progress update logic across multiple files.
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from typing import Optional
from purplex.submissions.grading_service import GradingService

logger = logging.getLogger(__name__)


class ProgressEngine:
    """
    Central engine for all progress-related operations.

    Provides a unified interface for tracking and updating user progress across
    problems, problem sets, and courses. Uses GradingService for grade calculation
    to maintain single source of truth.
    """

    def on_submission_created(self, submission):
        """
        Handle initial submission creation - just increment attempts.

        Args:
            submission: A newly created Submission instance
        """
        from purplex.problems_app.models import UserProgress

        logger.info(f"[ProgressEngine] Processing submission created event for {submission.submission_id}")

        with transaction.atomic():
            # Get or create progress, handling migration
            progress = self._get_or_create_progress(submission)

            # Only increment attempts and set timestamps
            # Don't update status yet - wait for test results
            progress.attempts += 1
            if not progress.first_attempt:
                progress.first_attempt = submission.submitted_at
            progress.last_attempt = submission.submitted_at

            progress.save()

            logger.info(f"[ProgressEngine] Updated attempt count to {progress.attempts} for user {submission.user.username}")

    def process_submission(self, submission):
        """
        Main entry point for processing any submission's impact on progress.
        This is the ONLY method that should update UserProgress records.

        Args:
            submission: A Submission model instance

        Returns:
            The updated UserProgress instance
        """
        from purplex.problems_app.models import UserProgress, UserProblemSetProgress

        logger.info(f"[ProgressEngine] Processing submission {submission.submission_id}")
        logger.info(f"[ProgressEngine] User: {submission.user.username}, Problem: {submission.problem.slug}")
        logger.info(f"[ProgressEngine] Score: {submission.score}, Problem Set: {submission.problem_set.slug if submission.problem_set else 'None'}")

        with transaction.atomic():
            # Get or create progress record with full context
            progress = self._get_or_create_progress(submission)

            # Calculate all progress metrics
            old_status = progress.status
            old_score = progress.best_score

            # Update core metrics
            self._update_scores(progress, submission)
            self._update_timing(progress, submission)
            self._update_attempts(progress, submission)

            # Evaluate completion and grade using GradingService
            grade = GradingService.calculate_grade(submission)
            status = self._evaluate_status(submission, progress)

            # Update progress fields
            progress.grade = grade
            progress.status = status

            # Update completion fields based on status
            if status == 'completed':
                progress.is_completed = True
                progress.completion_percentage = 100
                if not progress.completed_at:
                    progress.completed_at = timezone.now()
                    if progress.first_attempt:
                        progress.days_to_complete = (progress.completed_at - progress.first_attempt).days
            elif status == 'in_progress':
                progress.is_completed = False
                # Use best score for percentage, but cap at 99 if not complete
                progress.completion_percentage = min(progress.best_score, 99)
            else:  # not_started
                progress.is_completed = False
                progress.completion_percentage = 0

            # Update hints used
            if hasattr(submission, 'hint_activations'):
                progress.hints_used = submission.hint_activations.count()

            # Log changes
            if old_status != status:
                logger.info(f"[ProgressEngine] Status changed: {old_status} → {status}")
            if old_score != progress.best_score:
                logger.info(f"[ProgressEngine] Best score changed: {old_score} → {progress.best_score}")

            logger.info(f"[ProgressEngine] Saving progress - is_completed: {progress.is_completed}, status: {status}, grade: {grade}")

            # Save progress
            progress.save()

            # Update problem set progress
            if submission.problem_set:
                UserProblemSetProgress.update_from_progress(progress)

            # Emit SSE event for real-time updates
            self._emit_progress_event(progress, submission)

            return progress

    def _get_or_create_progress(self, submission):
        """Get or create UserProgress record, handling migration of old records."""
        from purplex.problems_app.models import UserProgress

        # Try to get existing progress with full context
        progress, created = UserProgress.objects.get_or_create(
            user=submission.user,
            problem=submission.problem,
            problem_set=submission.problem_set,
            course=submission.course,
            defaults={'problem_version': submission.problem.version}
        )

        logger.info(f"[ProgressEngine] Progress record {'CREATED' if created else 'FOUND'} with ID: {progress.id}")

        # Handle migration of old records without problem_set
        if created and submission.problem_set:
            try:
                # Look for existing progress without problem_set context
                old_progress = UserProgress.objects.get(
                    user=submission.user,
                    problem=submission.problem,
                    problem_set__isnull=True,
                    course=submission.course if submission.course else None
                )

                logger.info(f"[ProgressEngine] Migrating old progress record without problem_set")

                # Migrate all relevant fields
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
                progress.grade = getattr(old_progress, 'grade', 'incomplete')

                # Save migrated progress and delete old
                progress.save()
                old_progress.delete()
                logger.info(f"[ProgressEngine] Migration complete, old record deleted")

            except UserProgress.DoesNotExist:
                pass  # No old progress to migrate
            except UserProgress.MultipleObjectsReturned:
                logger.warning(f"[ProgressEngine] Multiple old progress records found for user {submission.user.username}")

        return progress

    def _update_scores(self, progress, submission):
        """Update score-related fields."""
        # Update best score
        if submission.score > progress.best_score:
            progress.best_score = submission.score
            logger.info(f"[ProgressEngine] Updated best score to {progress.best_score}")

        # Update average score
        if progress.attempts > 0:
            # Account for the new attempt that will be added
            progress.average_score = (
                (progress.average_score * progress.attempts + submission.score)
                / (progress.attempts + 1)
            )

    def _update_timing(self, progress, submission):
        """Update timing-related fields."""
        # Set timestamps
        if not progress.first_attempt:
            progress.first_attempt = submission.submitted_at
        progress.last_attempt = submission.submitted_at

        # Update time spent if available
        if hasattr(submission, 'time_spent') and submission.time_spent:
            progress.total_time_spent += submission.time_spent

    def _update_attempts(self, progress, submission):
        """Update attempt counters."""
        progress.attempts += 1

        # Update successful attempts if this is a perfect score
        if submission.score == 100:
            progress.successful_attempts = getattr(progress, 'successful_attempts', 0) + 1
            progress.consecutive_successes = getattr(progress, 'consecutive_successes', 0) + 1
        else:
            progress.consecutive_successes = 0


    def _evaluate_status(self, submission, progress):
        """
        Evaluate the overall progress status.
        This is the ONE place where completion is determined.

        Returns:
            'not_started', 'in_progress', or 'completed'
        """
        if progress.attempts == 0:
            return 'not_started'

        # For completion, we need grade to be 'complete'
        grade = GradingService.calculate_grade(submission)

        # Check if ANY submission for this problem has achieved 'complete' grade
        # This prevents regression - once completed, always completed
        if grade == 'complete' or progress.is_completed:
            return 'completed'

        # Otherwise, we're in progress
        return 'in_progress'

    def _evaluate_completion(self, submission):
        """
        Simple completion check for a single submission.
        Used internally and can be called externally if needed.

        Returns:
            True if submission meets completion criteria, False otherwise
        """
        # For EiPL, completion requires:
        # 1. Perfect test score (100%)
        if submission.score < 100:
            return False

        # 2. If segmentation is enabled, must pass segmentation
        problem = submission.problem
        if problem.problem_type == 'eipl' and problem.segmentation_enabled:
            if hasattr(submission, 'segmentation') and submission.segmentation:
                return submission.segmentation.passed
            else:
                # No segmentation data when it's required
                return False

        # All criteria met
        return True

    def _emit_progress_event(self, progress, submission):
        """
        Emit SSE event for real-time frontend updates.
        Maintains exact same event format that frontend expects.
        """
        logger.info(f"[ProgressEngine] SSE Event - Progress updated for {progress.user.username} on {progress.problem.slug}")

        # Store progress update in Redis for SSE views to poll
        # This follows the pattern used by the task SSE system
        try:
            import redis
            import json
            from django.core.cache import cache

            # Create event data structure
            event_data = {
                'type': 'progress_update',
                'user_id': progress.user.id,
                'problem_slug': progress.problem.slug,
                'problem_set_slug': progress.problem_set.slug if progress.problem_set else None,
                'course_id': progress.course.id if progress.course else None,
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
                'grade': progress.grade,
                'submission_id': str(submission.submission_id) if hasattr(submission, 'submission_id') else None,
                'timestamp': timezone.now().isoformat()
            }

            # Store with expiry for cleanup (1 hour)
            key = f"progress:update:{progress.user.id}:{progress.problem.id}"
            cache.set(key, event_data, timeout=3600)

            # Also publish to a channel for real-time subscribers
            # Note: Pub/sub functionality requires direct Redis connection
            # For now, we'll skip pub/sub in favor of polling-based updates
            channel = f"progress:channel:{progress.user.id}"
            # redis_client.publish(channel, json.dumps(event_data))  # Disabled for Docker compatibility

            logger.debug(f"[ProgressEngine] Published progress event to Redis channel {channel}")

        except Exception as e:
            # Don't fail the whole operation if SSE emission fails
            logger.error(f"[ProgressEngine] Failed to emit SSE event: {str(e)}")