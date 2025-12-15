"""
Service for exporting course progress data to CSV.
"""

import csv
import json
from collections import defaultdict
from io import StringIO

from purplex.problems_app.models import Course


class CourseExportService:
    """
    Service for exporting course data.
    """

    @classmethod
    def export_course_progress(
        cls, course: Course, include_inactive: bool = False
    ) -> str:
        """
        Export course progress to CSV format.

        Args:
            course: Course instance
            include_inactive: Include inactive students

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "student_username",
                "student_email",
                "student_first_name",
                "student_last_name",
                "enrolled_at",
                "problem_slug",
                "problem_title",
                "problem_difficulty",
                "problem_set",
                "status",
                "grade",
                "best_score",
                "average_score",
                "attempts",
                "successful_attempts",
                "hints_used_count",
                "hints_variable_fade_count",
                "hints_subgoal_highlight_count",
                "hints_suggested_trace_count",
                "hints_details",
                "total_time_spent_seconds",
                "first_attempt",
                "last_attempt",
                "completed_at",
                "is_completed",
            ]
        )

        # Get enrolled students via repository
        from ..repositories import (
            CourseEnrollmentRepository,
            HintRepository,
            ProgressRepository,
        )

        enrollments = CourseEnrollmentRepository.get_for_course_with_users(
            course, include_inactive=include_inactive
        )

        # CRITICAL FIX: Fetch ALL progress records in ONE query instead of N queries
        # Build enrollment lookup dict
        enrollment_dict = {e.user_id: e for e in enrollments}
        user_ids = list(enrollment_dict.keys())

        # Get all progress for all enrolled students via repository
        all_progress = ProgressRepository.get_for_course_export(course, user_ids)

        # Fetch ALL hint activations for this course via repository
        # Build a mapping: (user_id, problem_id) -> list of hint activations
        hint_activations = HintRepository.get_activations_for_course_export(
            course, user_ids
        )

        # Build lookup dict for efficient access
        hint_lookup = defaultdict(list)
        for activation in hint_activations:
            key = (activation.submission.user_id, activation.submission.problem_id)
            hint_lookup[key].append(
                {
                    "type": activation.hint.hint_type,
                    "activated_at": activation.activated_at.isoformat(),
                    "trigger": activation.trigger_type,
                    "order": activation.activation_order,
                    "viewed_duration": activation.viewed_duration_seconds,
                    "helpful": activation.was_helpful,
                }
            )

        # Write rows - NO additional queries
        for progress in all_progress:
            user = progress.user

            # Skip if user was deleted (SET_NULL on UserProgress.user)
            if not user:
                continue

            enrollment = enrollment_dict.get(user.id)

            if not enrollment:
                continue

            # Get hint activations for this user/problem
            hint_key = (user.id, progress.problem.id)
            user_hints = hint_lookup.get(hint_key, [])

            # Count by hint type
            hint_type_counts = defaultdict(int)
            for hint in user_hints:
                hint_type_counts[hint["type"]] += 1

            # Format detailed hints as JSON string for CSV
            hints_details_json = json.dumps(user_hints) if user_hints else ""

            writer.writerow(
                [
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    enrollment.enrolled_at.isoformat(),
                    progress.problem.slug,
                    progress.problem.title,
                    progress.problem.difficulty,
                    progress.problem_set.title if progress.problem_set else "",
                    progress.status,
                    progress.grade,
                    progress.best_score,
                    progress.average_score,
                    progress.attempts,
                    progress.successful_attempts,
                    progress.hints_used,  # Total count from UserProgress
                    hint_type_counts.get("variable_fade", 0),
                    hint_type_counts.get("subgoal_highlight", 0),
                    hint_type_counts.get("suggested_trace", 0),
                    hints_details_json,
                    (
                        progress.total_time_spent.total_seconds()
                        if progress.total_time_spent
                        else 0
                    ),
                    (
                        progress.first_attempt.isoformat()
                        if progress.first_attempt
                        else ""
                    ),
                    progress.last_attempt.isoformat() if progress.last_attempt else "",
                    progress.completed_at.isoformat() if progress.completed_at else "",
                    progress.is_completed,
                ]
            )

        output.seek(0)
        return output.getvalue()
