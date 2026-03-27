"""
Service for comprehensive research data exports.

This service provides structured, research-grade data exports including:
- Submission details with test results
- Progress tracking and learning analytics
- Hint usage and intervention effectiveness
- Temporal analytics (progression over time)
"""

from datetime import datetime
from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from purplex.problems_app.models import Course, ProblemSet
from purplex.utils.anonymization import AnonymizationService


class ResearchExportService:
    """
    Service for exporting comprehensive research data.
    """

    @classmethod
    def export_complete_dataset(
        cls,
        course: Course | None = None,
        problem_set: ProblemSet | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_code: bool = False,
        anonymize: bool = True,  # FERPA U4: Default anonymized to protect PII
        event_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Export complete research dataset with all metrics.

        Args:
            course: Optional course filter
            problem_set: Optional problem set filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            include_code: Whether to include student code (privacy consideration)
            anonymize: Whether to anonymize user data
            event_types: Optional list of event types to filter activity events

        Returns:
            Dictionary with complete research data
        """
        dataset = {
            "metadata": cls._build_metadata(
                course, problem_set, start_date, end_date, event_types
            ),
            "submissions": cls._export_submissions(
                course, problem_set, start_date, end_date, include_code, anonymize
            ),
            "progress": cls._export_progress(course, problem_set, anonymize),
            "progress_history": cls._export_progress_history(
                course, problem_set, start_date, end_date, anonymize
            ),
            "hint_usage": cls._export_hint_usage(course, problem_set, anonymize),
            "activity_events": cls._export_activity_events(
                course, start_date, end_date, event_types, anonymize
            ),
        }

        return dataset

    @classmethod
    def _build_metadata(
        cls,
        course: Course | None,
        problem_set: ProblemSet | None,
        start_date: datetime | None,
        end_date: datetime | None,
        event_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build export metadata."""
        return {
            "export_timestamp": timezone.now().isoformat(),
            "export_version": "1.0.0",
            "filters": {
                "course": course.course_id if course else None,
                "problem_set": problem_set.slug if problem_set else None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "event_types": event_types,
            },
            "schema_version": "1.0.0",
        }

    @classmethod
    def _export_submissions(
        cls,
        course: Course | None,
        problem_set: ProblemSet | None,
        start_date: datetime | None,
        end_date: datetime | None,
        include_code: bool,
        anonymize: bool,
    ) -> list[dict[str, Any]]:
        """Export detailed submission data."""
        from purplex.submissions.repositories import SubmissionRepository

        # Build filtered queryset via repository
        queryset = SubmissionRepository.get_for_research_export(
            course=course,
            problem_set=problem_set,
            start_date=start_date,
            end_date=end_date,
        )

        submissions = []
        for submission in queryset:
            submission_data = {
                "submission_id": str(submission.submission_id),
                "user_id": cls._anonymize_user_id(submission.user, anonymize),
                "problem_slug": submission.problem.slug,
                "problem_difficulty": submission.problem.difficulty,
                "problem_set_slug": (
                    submission.problem_set.slug if submission.problem_set else None
                ),
                "course_id": submission.course.course_id if submission.course else None,
                "submission_type": submission.submission_type,
                "submitted_at": submission.submitted_at.isoformat(),
                # Results
                "score": submission.score,
                "passed_all_tests": submission.passed_all_tests,
                "is_correct": submission.is_correct,
                "comprehension_level": submission.comprehension_level,
                "completion_status": submission.completion_status,
                # Performance
                "execution_time_ms": submission.execution_time_ms,
                "memory_used_mb": submission.memory_used_mb,
                "time_spent_seconds": (
                    submission.time_spent.total_seconds()
                    if submission.time_spent
                    else None
                ),
                # Test results
                "test_results": cls._format_test_results(
                    submission.test_executions.all()
                ),
                # Hint activations
                "hints_activated": cls._format_hint_activations(
                    submission.hint_activations.all()
                ),
            }

            # Include code if requested (privacy consideration)
            if include_code:
                submission_data["raw_input"] = submission.raw_input
                submission_data["processed_code"] = submission.processed_code

            submissions.append(submission_data)

        return submissions

    @classmethod
    def _export_progress(
        cls,
        course: Course | None,
        problem_set: ProblemSet | None,
        anonymize: bool,
    ) -> list[dict[str, Any]]:
        """Export current progress state for all users."""
        from ..repositories import ProgressRepository

        # Get progress via repository
        queryset = ProgressRepository.get_for_research_export(
            course=course, problem_set=problem_set
        )

        progress_data = []
        for progress in queryset:
            progress_data.append(
                {
                    "user_id": cls._anonymize_user_id(progress.user, anonymize),
                    "problem_slug": progress.problem.slug,
                    "problem_difficulty": progress.problem.difficulty,
                    "problem_set_slug": (
                        progress.problem_set.slug if progress.problem_set else None
                    ),
                    "course_id": progress.course.course_id if progress.course else None,
                    "status": progress.status,
                    "grade": progress.grade,
                    "best_score": progress.best_score,
                    "average_score": progress.average_score,
                    "attempts": progress.attempts,
                    "successful_attempts": progress.successful_attempts,
                    "hints_used": progress.hints_used,
                    "total_time_spent_seconds": (
                        progress.total_time_spent.total_seconds()
                        if progress.total_time_spent
                        else 0
                    ),
                    "first_attempt": (
                        progress.first_attempt.isoformat()
                        if progress.first_attempt
                        else None
                    ),
                    "last_attempt": (
                        progress.last_attempt.isoformat()
                        if progress.last_attempt
                        else None
                    ),
                    "completed_at": (
                        progress.completed_at.isoformat()
                        if progress.completed_at
                        else None
                    ),
                    "days_to_complete": progress.days_to_complete,
                    "is_completed": progress.is_completed,
                    "completion_percentage": progress.completion_percentage,
                }
            )

        return progress_data

    @classmethod
    def _export_progress_history(
        cls,
        course: Course | None,
        problem_set: ProblemSet | None,
        start_date: datetime | None,
        end_date: datetime | None,
        anonymize: bool,
    ) -> list[dict[str, Any]]:
        """Export historical progress snapshots."""
        from ..repositories import ProgressRepository

        # Get snapshots via repository
        queryset = ProgressRepository.get_snapshots_for_research_export(
            problem_set=problem_set, start_date=start_date, end_date=end_date
        )

        snapshots = []
        for snapshot in queryset:
            snapshots.append(
                {
                    "user_id": cls._anonymize_user_id(snapshot.user, anonymize),
                    "problem_slug": snapshot.problem.slug if snapshot.problem else None,
                    "problem_set_slug": (
                        snapshot.problem_set.slug if snapshot.problem_set else None
                    ),
                    "snapshot_date": snapshot.snapshot_date.isoformat(),
                    "completion_percentage": snapshot.completion_percentage,
                    "problems_completed": snapshot.problems_completed,
                    "average_score": snapshot.average_score,
                    "time_spent_today_seconds": (
                        snapshot.time_spent_today.total_seconds()
                        if snapshot.time_spent_today
                        else 0
                    ),
                }
            )

        return snapshots

    @classmethod
    def _export_hint_usage(
        cls,
        course: Course | None,
        problem_set: ProblemSet | None,
        anonymize: bool,
    ) -> list[dict[str, Any]]:
        """Export hint usage patterns and effectiveness."""
        from ..repositories import HintRepository

        # Get hint activations via repository
        queryset = HintRepository.get_activations_for_research_export(
            course=course, problem_set=problem_set
        )

        hint_usage = []
        for activation in queryset:
            hint_usage.append(
                {
                    "user_id": cls._anonymize_user_id(
                        activation.submission.user, anonymize
                    ),
                    "problem_slug": activation.submission.problem.slug,
                    "problem_set_slug": (
                        activation.submission.problem_set.slug
                        if activation.submission.problem_set
                        else None
                    ),
                    "hint_type": activation.hint.hint_type,
                    "activated_at": activation.activated_at.isoformat(),
                    "activation_order": activation.activation_order,
                    "trigger_type": activation.trigger_type,
                    "viewed_duration_seconds": activation.viewed_duration_seconds,
                    "was_helpful": activation.was_helpful,
                    "submission_score_after": activation.submission.score,
                    "submission_passed": activation.submission.passed_all_tests,
                }
            )

        return hint_usage

    @classmethod
    def _export_activity_events(
        cls,
        course: Course | None,
        start_date: datetime | None,
        end_date: datetime | None,
        event_types: list[str] | None,
        anonymize: bool,
    ) -> list[dict[str, Any]]:
        """Export activity events (probes, hints, refute trials).

        Uses the pre-computed anonymous_user_id field rather than re-computing
        from the user FK, because the user may have been deleted (SET_NULL).
        """
        from purplex.submissions.activity_event_repository import (
            ActivityEventRepository,
        )

        queryset = ActivityEventRepository.get_for_research_export(
            course=course,
            start_date=start_date,
            end_date=end_date,
            event_types=event_types,
        )

        events = []
        for event in queryset:
            if anonymize:
                user_id = event.anonymous_user_id or "deleted"
            else:
                user_id = (
                    event.user.username
                    if event.user
                    else event.anonymous_user_id or "deleted"
                )

            events.append(
                {
                    "user_id": user_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "problem_slug": event.problem.slug if event.problem else None,
                    "course_id": (event.course.course_id if event.course else None),
                    "payload": event.payload,
                    "schema_version": event.schema_version,
                }
            )

        return events

    @classmethod
    def _format_test_results(cls, test_executions) -> list[dict[str, Any]]:
        """Format test execution results."""
        return [
            {
                "execution_order": te.execution_order,
                "passed": te.passed,
                "error_type": te.error_type,
                "execution_time_ms": te.execution_time_ms,
                "is_hidden": te.test_case.is_hidden,
            }
            for te in test_executions
        ]

    @classmethod
    def _format_hint_activations(cls, hint_activations) -> list[dict[str, Any]]:
        """Format hint activation data."""
        return [
            {
                "hint_type": ha.hint.hint_type,
                "activation_order": ha.activation_order,
                "trigger_type": ha.trigger_type,
                "activated_at": ha.activated_at.isoformat(),
                "viewed_duration_seconds": ha.viewed_duration_seconds,
            }
            for ha in hint_activations
        ]

    @classmethod
    def _anonymize_user_id(cls, user: User, anonymize: bool) -> str:
        """Anonymize user ID if requested."""
        if anonymize:
            return AnonymizationService.anonymize_user_id(user)
        return user.username
