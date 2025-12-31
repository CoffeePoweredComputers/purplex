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

    @classmethod
    def export_problem_set_scores(
        cls,
        course: Course,
        problem_set,
        include_inactive: bool = False,
    ) -> str:
        """
        Export scores for all students in a specific problem set.

        Args:
            course: Course instance
            problem_set: ProblemSet instance
            include_inactive: Include inactive students

        Returns:
            CSV string with student scores for each problem in the set
        """
        from ..repositories import CourseEnrollmentRepository, ProgressRepository

        output = StringIO()
        writer = csv.writer(output)

        # Get problems in this problem set, ordered
        problems = list(problem_set.problems.order_by("problemsetmembership__order"))

        # Build header: student info + one column per problem
        header = [
            "student_username",
            "student_email",
            "student_first_name",
            "student_last_name",
        ]
        for problem in problems:
            header.append(f"{problem.slug}_score")
            header.append(f"{problem.slug}_status")
            header.append(f"{problem.slug}_attempts")

        # Add summary columns
        header.extend(["average_score", "completion_rate", "total_attempts"])
        writer.writerow(header)

        # Get enrolled students
        enrollments = CourseEnrollmentRepository.get_for_course_with_users(
            course, include_inactive=include_inactive
        )

        # Get all progress for these students in this course/problem_set
        user_ids = [e.user_id for e in enrollments]
        all_progress = list(
            ProgressRepository.get_for_course_export(course, user_ids).filter(
                problem_set=problem_set
            )
        )

        # Build lookup: (user_id, problem_id) -> progress
        progress_lookup = {(p.user_id, p.problem_id): p for p in all_progress}

        # Write rows for each student
        for enrollment in enrollments:
            user = enrollment.user
            row = [
                user.username,
                user.email,
                user.first_name,
                user.last_name,
            ]

            scores = []
            completed_count = 0
            total_attempts = 0

            for problem in problems:
                progress = progress_lookup.get((user.id, problem.id))
                if progress:
                    score = progress.best_score if progress.best_score else 0
                    scores.append(score)
                    row.extend(
                        [
                            score,
                            progress.status,
                            progress.attempts,
                        ]
                    )
                    if progress.is_completed:
                        completed_count += 1
                    total_attempts += progress.attempts
                else:
                    row.extend([0, "not_started", 0])

            # Calculate summary stats
            avg_score = sum(scores) / len(scores) if scores else 0
            completion_rate = (completed_count / len(problems) * 100) if problems else 0

            row.extend([round(avg_score, 2), round(completion_rate, 2), total_attempts])
            writer.writerow(row)

        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_problem_scores(
        cls,
        course: Course,
        problem,
        include_inactive: bool = False,
    ) -> str:
        """
        Export scores for all students for a specific problem.

        Args:
            course: Course instance
            problem: Problem instance
            include_inactive: Include inactive students

        Returns:
            CSV string with detailed scores for each student on this problem
        """
        from ..repositories import (
            CourseEnrollmentRepository,
            HintRepository,
            ProgressRepository,
        )

        output = StringIO()
        writer = csv.writer(output)

        # Header with detailed problem-level stats
        writer.writerow(
            [
                "student_username",
                "student_email",
                "student_first_name",
                "student_last_name",
                "status",
                "best_score",
                "average_score",
                "attempts",
                "successful_attempts",
                "hints_used",
                "total_time_spent_seconds",
                "first_attempt",
                "last_attempt",
                "completed_at",
            ]
        )

        # Get enrolled students
        enrollments = CourseEnrollmentRepository.get_for_course_with_users(
            course, include_inactive=include_inactive
        )

        user_ids = [e.user_id for e in enrollments]

        # Get all progress for this problem
        all_progress = list(
            ProgressRepository.get_for_course_export(course, user_ids).filter(
                problem=problem
            )
        )

        # Build lookup: user_id -> progress
        progress_lookup = {p.user_id: p for p in all_progress}

        # Fetch hint activations for this problem
        hint_activations = HintRepository.get_activations_for_course_export(
            course, user_ids
        )
        hint_lookup = {}
        for activation in hint_activations:
            if activation.submission.problem_id == problem.id:
                key = activation.submission.user_id
                if key not in hint_lookup:
                    hint_lookup[key] = 0
                hint_lookup[key] += 1

        # Write rows for each student
        for enrollment in enrollments:
            user = enrollment.user
            progress = progress_lookup.get(user.id)

            if progress:
                row = [
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    progress.status,
                    progress.best_score or 0,
                    progress.average_score or 0,
                    progress.attempts,
                    progress.successful_attempts,
                    hint_lookup.get(user.id, 0),
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
                ]
            else:
                # Student hasn't attempted this problem yet
                row = [
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    "not_started",
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "",
                    "",
                    "",
                ]

            writer.writerow(row)

        output.seek(0)
        return output.getvalue()
