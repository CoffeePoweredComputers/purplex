"""
Service for instructor analytics and dashboard data.

Provides aggregated metrics, student performance analysis, and
actionable insights for instructors.
"""

from typing import Dict, List, Any
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import (
    Q, Count, Avg, Sum, Max,
    Case, When, FloatField
)
from django.utils import timezone

from purplex.problems_app.models import (
    Problem, Course, UserProgress,
    UserProblemSetProgress, ProgressSnapshot, CourseEnrollment
)
from purplex.submissions.models import Submission, HintActivation


class InstructorAnalyticsService:
    """
    Service for instructor-focused analytics.
    """

    @classmethod
    def get_course_overview(cls, course: Course) -> Dict[str, Any]:
        """
        Get high-level course metrics.

        Returns:
            Dictionary with course statistics
        """
        # Get enrolled student IDs via repository
        from ..repositories import CourseEnrollmentRepository, ProgressRepository
        from purplex.submissions.repositories import SubmissionRepository

        student_ids = CourseEnrollmentRepository.get_active_student_ids(course)

        # Get all progress for this course via repository
        progress_records = ProgressRepository.get_for_course_analytics(course, student_ids)

        # Calculate aggregates
        stats = progress_records.aggregate(
            total_students=Count('user', distinct=True),
            total_attempts=Sum('attempts'),
            avg_score=Avg('best_score'),
            completion_rate=Avg(
                Case(
                    When(is_completed=True, then=1),
                    default=0,
                    output_field=FloatField()
                )
            ) * 100,
            avg_time_per_problem=Avg('total_time_spent'),
        )

        # Get problem set progress via repository
        # CRITICAL FIX: Use single annotated query instead of loop with aggregates
        # This reduces N queries (1 per problem set) to just 1 query total
        ps_stats = ProgressRepository.get_problem_set_for_course_analytics(course, student_ids)

        # Build dict for O(1) lookup
        ps_stats_dict = {stat['problem_set_id']: stat for stat in ps_stats}

        problem_sets = course.problem_sets.all()
        problem_set_stats = []

        for ps in problem_sets:
            stats = ps_stats_dict.get(ps.id, {
                'avg_completion': 0,
                'students_completed': 0,
                'students_started': 0
            })

            problem_set_stats.append({
                'problem_set_slug': ps.slug,
                'problem_set_title': ps.title,
                'avg_completion': stats.get('avg_completion') or 0,
                'students_completed': stats.get('students_completed') or 0,
                'students_started': stats.get('students_started') or 0,
                'completion_rate': (
                    (stats.get('students_completed', 0) / len(student_ids) * 100)
                    if student_ids else 0
                ),
            })

        # Get recent activity via repository
        recent_submissions = SubmissionRepository.get_recent_for_course(course, student_ids)

        return {
            'course_id': course.course_id,
            'course_name': course.name,
            'total_students': stats['total_students'] or 0,
            'total_attempts': stats['total_attempts'] or 0,
            'avg_score': round(stats['avg_score'] or 0, 2),
            'completion_rate': round(stats['completion_rate'] or 0, 2),
            'avg_time_per_problem_seconds': (
                stats['avg_time_per_problem'].total_seconds()
                if stats['avg_time_per_problem'] else 0
            ),
            'recent_submissions_7days': recent_submissions,
            'problem_set_stats': problem_set_stats,
        }

    @classmethod
    def get_student_list(
        cls,
        course: Course,
        sort_by: str = 'progress',
        order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Get list of students with their progress metrics.

        Args:
            course: Course instance
            sort_by: Sort field (progress, score, activity, name)
            order: Sort order (asc or desc)

        Returns:
            List of student data dictionaries
        """
        # Get all enrolled students
        # CRITICAL FIX: Use annotated query instead of loop with aggregates
        # This reduces N queries (2 per student) to just 1 query total
        # Get enrollments with progress stats via repository
        from ..repositories import CourseEnrollmentRepository
        enrollments = CourseEnrollmentRepository.get_enrollments_with_progress_stats(course)

        students = []

        for enrollment in enrollments:
            user = enrollment.user

            # Calculate flags for at-risk students
            is_struggling = (
                enrollment.total_attempts and
                enrollment.total_attempts > 10 and
                (enrollment.avg_score or 0) < 50
            )

            is_inactive = (
                not enrollment.last_activity or
                enrollment.last_activity < timezone.now() - timedelta(days=7)
            )

            students.append({
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'total_problems': enrollment.total_problems or 0,
                'completed_problems': enrollment.completed_problems or 0,
                'completion_percentage': enrollment.avg_completion or 0,
                'avg_score': round(enrollment.avg_score or 0, 2),
                'total_attempts': enrollment.total_attempts or 0,
                'total_time_spent_seconds': (
                    enrollment.total_time_spent.total_seconds()
                    if enrollment.total_time_spent else 0
                ),
                'last_activity': (
                    enrollment.last_activity.isoformat()
                    if enrollment.last_activity else None
                ),
                'flags': {
                    'is_struggling': is_struggling,
                    'is_inactive': is_inactive,
                    'needs_attention': is_struggling or is_inactive,
                },
            })

        # Sort students
        sort_key_map = {
            'progress': 'completion_percentage',
            'score': 'avg_score',
            'activity': 'last_activity',
            'name': 'username',
        }

        sort_key = sort_key_map.get(sort_by, 'completion_percentage')
        reverse = (order == 'desc')

        students.sort(
            key=lambda x: x[sort_key] if x[sort_key] is not None else '',
            reverse=reverse
        )

        return students

    @classmethod
    def get_student_detail(
        cls,
        course: Course,
        user: User
    ) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific student.

        Args:
            course: Course instance
            user: User instance

        Returns:
            Detailed student analytics
        """
        # Get overall progress via repository
        from ..repositories import ProgressRepository, HintRepository
        from purplex.submissions.repositories import SubmissionRepository

        progress_records = ProgressRepository.get_for_student_detail(course, user)

        # Get problem set progress via repository
        ps_progress = ProgressRepository.get_problem_set_for_student(course, user)

        # Get submissions via repository
        submissions = SubmissionRepository.get_for_student_detail(course, user)

        # Get hint usage via repository
        hint_usage = HintRepository.get_usage_stats_for_student(course, user)

        # Get progress history via repository
        history = ProgressRepository.get_snapshots_for_student(user, course.problem_sets.all())

        # Calculate learning trajectory
        trajectory = []
        for snapshot in history:
            trajectory.append({
                'date': snapshot.snapshot_date.isoformat(),
                'completion_percentage': snapshot.completion_percentage,
                'average_score': snapshot.average_score,
                'problems_completed': snapshot.problems_completed,
            })

        # Format problem-level progress
        problem_progress = []
        for progress in progress_records:
            problem_progress.append({
                'problem_slug': progress.problem.slug,
                'problem_title': progress.problem.title,
                'problem_set': progress.problem_set.title if progress.problem_set else None,
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'hints_used': progress.hints_used,
                'time_spent_seconds': (
                    progress.total_time_spent.total_seconds()
                    if progress.total_time_spent else 0
                ),
                'is_completed': progress.is_completed,
            })

        # Format recent submissions
        recent_submissions = []
        for submission in submissions:
            recent_submissions.append({
                'submission_id': str(submission.submission_id),
                'problem_title': submission.problem.title,
                'submitted_at': submission.submitted_at.isoformat(),
                'score': submission.score,
                'passed_all_tests': submission.passed_all_tests,
                'submission_type': submission.submission_type,
            })

        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'problem_progress': problem_progress,
            'problem_set_progress': [
                {
                    'problem_set_slug': ps.problem_set.slug,
                    'problem_set_title': ps.problem_set.title,
                    'completion_percentage': ps.completion_percentage,
                    'completed_problems': ps.completed_problems,
                    'total_problems': ps.total_problems,
                    'avg_score': ps.average_score,
                }
                for ps in ps_progress
            ],
            'recent_submissions': recent_submissions,
            'hint_usage': {h['hint__hint_type']: h['usage_count'] for h in hint_usage},
            'learning_trajectory': trajectory,
        }

    @classmethod
    def get_problem_analytics(
        cls,
        course: Course,
        problem: Problem
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific problem in a course.

        Args:
            course: Course instance
            problem: Problem instance

        Returns:
            Problem analytics
        """
        # Get enrolled student IDs via repository
        from ..repositories import CourseEnrollmentRepository, ProgressRepository
        from purplex.submissions.repositories import SubmissionRepository

        student_ids = CourseEnrollmentRepository.get_active_student_ids(course)

        # Get progress for this problem via repository
        progress_records = ProgressRepository.get_for_problem_analytics(course, problem, student_ids)

        stats = progress_records.aggregate(
            total_students=Count('user', distinct=True),
            students_completed=Count('id', filter=Q(is_completed=True)),
            avg_score=Avg('best_score'),
            avg_attempts=Avg('attempts'),
            avg_time_spent=Avg('total_time_spent'),
            total_hints_used=Sum('hints_used'),
        )

        # Get score distribution
        score_distribution = progress_records.values_list(
            'best_score', flat=True
        )

        # Calculate buckets: 0-20, 21-40, 41-60, 61-80, 81-100
        buckets = {
            '0-20': 0,
            '21-40': 0,
            '41-60': 0,
            '61-80': 0,
            '81-100': 0,
        }

        for score in score_distribution:
            if score <= 20:
                buckets['0-20'] += 1
            elif score <= 40:
                buckets['21-40'] += 1
            elif score <= 60:
                buckets['41-60'] += 1
            elif score <= 80:
                buckets['61-80'] += 1
            else:
                buckets['81-100'] += 1

        # Get common errors via repository
        error_stats = SubmissionRepository.get_error_stats_for_problem(course, problem)

        return {
            'problem_slug': problem.slug,
            'problem_title': problem.title,
            'difficulty': problem.difficulty,
            'total_students': len(student_ids),
            'students_attempted': stats['total_students'] or 0,
            'students_completed': stats['students_completed'] or 0,
            'completion_rate': (
                (stats['students_completed'] / len(student_ids) * 100)
                if student_ids else 0
            ),
            'avg_score': round(stats['avg_score'] or 0, 2),
            'avg_attempts': round(stats['avg_attempts'] or 0, 2),
            'avg_time_spent_seconds': (
                stats['avg_time_spent'].total_seconds()
                if stats['avg_time_spent'] else 0
            ),
            'total_hints_used': stats['total_hints_used'] or 0,
            'score_distribution': buckets,
            'common_errors': [
                {'error_type': e['error_type'], 'count': e['count']}
                for e in error_stats
            ],
        }
