"""
Service for exporting course progress data to CSV.
"""

import csv
from io import StringIO
from typing import Optional

from purplex.problems_app.models import Course, UserProgress, CourseEnrollment


class CourseExportService:
    """
    Service for exporting course data.
    """

    @classmethod
    def export_course_progress(
        cls,
        course: Course,
        include_inactive: bool = False
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
        writer.writerow([
            'student_username',
            'student_email',
            'student_first_name',
            'student_last_name',
            'enrolled_at',
            'problem_slug',
            'problem_title',
            'problem_difficulty',
            'problem_set',
            'status',
            'grade',
            'best_score',
            'average_score',
            'attempts',
            'successful_attempts',
            'hints_used',
            'total_time_spent_seconds',
            'first_attempt',
            'last_attempt',
            'completed_at',
            'is_completed',
        ])

        # Get enrolled students
        enrollments = CourseEnrollment.objects.filter(
            course=course
        ).select_related('user')

        if not include_inactive:
            enrollments = enrollments.filter(is_active=True)

        # CRITICAL FIX: Fetch ALL progress records in ONE query instead of N queries
        # Build enrollment lookup dict
        enrollment_dict = {e.user_id: e for e in enrollments}

        # Get all progress for all enrolled students in a single query
        all_progress = UserProgress.objects.filter(
            course=course,
            user_id__in=[e.user_id for e in enrollments]
        ).select_related(
            'user', 'problem', 'problem_set'
        ).order_by('user__username', 'problem__slug')

        # Write rows - NO additional queries
        for progress in all_progress:
            user = progress.user

            # Skip if user was deleted (SET_NULL on UserProgress.user)
            if not user:
                continue

            enrollment = enrollment_dict.get(user.id)

            if not enrollment:
                continue

            writer.writerow([
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                enrollment.enrolled_at.isoformat(),
                progress.problem.slug,
                progress.problem.title,
                progress.problem.difficulty,
                progress.problem_set.title if progress.problem_set else '',
                progress.status,
                progress.grade,
                progress.best_score,
                progress.average_score,
                progress.attempts,
                progress.successful_attempts,
                progress.hints_used,
                progress.total_time_spent.total_seconds() if progress.total_time_spent else 0,
                progress.first_attempt.isoformat() if progress.first_attempt else '',
                progress.last_attempt.isoformat() if progress.last_attempt else '',
                progress.completed_at.isoformat() if progress.completed_at else '',
                progress.is_completed,
            ])

        output.seek(0)
        return output.getvalue()
