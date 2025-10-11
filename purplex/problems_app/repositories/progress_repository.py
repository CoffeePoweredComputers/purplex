"""
Repository for UserProgress and related model data access.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.contrib.auth.models import User
from django.utils import timezone

from purplex.problems_app.models import (
    UserProgress, UserProblemSetProgress, ProgressSnapshot,
    Problem, ProblemSet, Course
)
from .base_repository import BaseRepository


class ProgressRepository(BaseRepository):
    """
    Repository for all progress-related database queries.
    
    This repository handles all data access for user progress tracking,
    including individual problem progress, problem set progress, and snapshots.
    """
    
    model_class = UserProgress
    
    @classmethod
    def get_user_progress(cls, user: User, problem: Problem,
                         course: Optional[Course] = None,
                         problem_set: Optional[ProblemSet] = None) -> Optional[UserProgress]:
        """
        Get a user's progress for a specific problem.

        Args:
            user: The user
            problem: The problem
            course: Optional course context
            problem_set: Optional problem set context

        Returns:
            UserProgress instance or None
        """
        filters = {
            'user': user,
            'problem': problem
        }
        if course:
            filters['course'] = course
        if problem_set:
            filters['problem_set'] = problem_set

        return UserProgress.objects.filter(**filters).first()
    
    @classmethod
    def get_or_create_user_progress(cls, user: User, problem: Problem,
                                  course: Optional[Course] = None) -> tuple:
        """
        Get or create user progress for a problem.
        
        Returns:
            Tuple of (UserProgress, created)
        """
        defaults = {
            'attempts': 0,
            'hints_used': 0,
            'status': 'not_started'
        }
        
        return UserProgress.objects.get_or_create(
            user=user,
            problem=problem,
            course=course,
            defaults=defaults
        )
    
    @classmethod
    def get_user_attempts(cls, user: User, problem: Problem,
                        course: Optional[Course] = None,
                        problem_set: Optional[ProblemSet] = None) -> int:
        """Get the number of attempts a user has made on a problem."""
        progress = cls.get_user_progress(user, problem, course, problem_set)
        return progress.attempts if progress else 0
    
    @classmethod
    def get_user_all_progress(cls, user: User, course: Optional[Course] = None) -> List:
        """Get all progress records for a user."""
        filters = {'user': user}
        if course:
            filters['course'] = course
            
        return list(UserProgress.objects.filter(**filters).select_related(
            'problem', 'problem__category', 'course'
        ).order_by('-last_attempt'))
    
    @classmethod
    def get_user_completed_problems(cls, user: User, course: Optional[Course] = None) -> List:
        """Get all problems completed by a user."""
        filters = {
            'user': user,
            'status': 'completed'
        }
        if course:
            filters['course'] = course
            
        return list(UserProgress.objects.filter(**filters).select_related(
            'problem', 'problem__category'
        ))
    
    @classmethod
    def get_problem_set_progress(cls, user: User, problem_set: ProblemSet,
                                course: Optional[Course] = None) -> Optional[UserProblemSetProgress]:
        """Get user's progress for a problem set."""
        filters = {
            'user': user,
            'problem_set': problem_set
        }
        if course:
            filters['course'] = course
            
        return UserProblemSetProgress.objects.filter(**filters).first()
    
    @classmethod
    def get_or_create_problem_set_progress(cls, user: User, problem_set: ProblemSet,
                                         course: Optional[Course] = None) -> tuple:
        """Get or create problem set progress."""
        defaults = {
            'completed_problems': 0,
            'average_score': 0.0
        }

        return UserProblemSetProgress.objects.get_or_create(
            user=user,
            problem_set=problem_set,
            course=course,
            defaults=defaults
        )
    
    @classmethod
    def update_problem_set_progress(cls, user: User, problem_set: ProblemSet,
                                  updates: Dict[str, Any],
                                  course: Optional[Course] = None) -> bool:
        """Update problem set progress."""
        filters = {
            'user': user,
            'problem_set': problem_set
        }
        if course:
            filters['course'] = course
            
        updated = UserProblemSetProgress.objects.filter(**filters).update(**updates)
        return updated > 0
    
    @classmethod
    def get_user_problem_set_progresses(cls, user: User, course: Optional[Course] = None) -> List:
        """Get all problem set progress records for a user."""
        filters = {'user': user}
        if course:
            filters['course'] = course
            
        return list(UserProblemSetProgress.objects.filter(**filters).select_related(
            'problem_set', 'course'
        ).order_by('-last_updated'))
    
    @classmethod
    def get_course_progress_summary(cls, user: User, course: Course) -> Dict[str, Any]:
        """
        Get a summary of user's progress in a course.
        
        Returns:
            Dictionary with progress statistics
        """
        progress_qs = UserProgress.objects.filter(user=user, course=course)
        
        return {
            'total_problems': progress_qs.count(),
            'completed': progress_qs.filter(status='completed').count(),
            'in_progress': progress_qs.filter(status='in_progress').count(),
            'not_started': progress_qs.filter(status='not_started').count(),
            'total_attempts': progress_qs.aggregate(Sum('attempts'))['attempts__sum'] or 0,
            'total_hints': progress_qs.aggregate(Sum('hints_used'))['hints_used__sum'] or 0,
            'avg_score': progress_qs.filter(
                score__isnull=False
            ).aggregate(Avg('score'))['score__avg'] or 0.0
        }
    
    @classmethod
    def get_recent_activity(cls, user: User, days: int = 7) -> List:
        """Get user's recent activity within specified days."""
        cutoff_date = timezone.now() - timedelta(days=days)
        return list(UserProgress.objects.filter(
            user=user,
            last_attempt__gte=cutoff_date
        ).select_related('problem', 'course').order_by('-last_attempt'))
    
    @classmethod
    def create_progress_snapshot(cls, user: User, problem: Optional[Problem] = None,
                               problem_set: Optional[ProblemSet] = None,
                               course: Optional[Course] = None,
                               snapshot_data: Dict[str, Any] = None) -> ProgressSnapshot:
        """Create a progress snapshot for tracking history."""
        return ProgressSnapshot.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            snapshot_data=snapshot_data or {},
            snapshot_date=timezone.now()
        )
    
    @classmethod
    def get_progress_snapshots(cls, user: User, problem: Optional[Problem] = None,
                             problem_set: Optional[ProblemSet] = None,
                             course: Optional[Course] = None,
                             days_back: int = 30) -> List:
        """Get progress snapshots for a user."""
        filters = {'user': user}
        if problem:
            filters['problem'] = problem
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
            
        cutoff_date = timezone.now() - timedelta(days=days_back)
        filters['snapshot_date__gte'] = cutoff_date
        
        return list(ProgressSnapshot.objects.filter(**filters).order_by('snapshot_date'))
    
    @classmethod
    def get_problem_statistics(cls, problem: Problem) -> Dict[str, Any]:
        """
        Get statistics for a specific problem across all users.
        
        Returns:
            Dictionary with problem statistics
        """
        progress_qs = UserProgress.objects.filter(problem=problem)
        
        return {
            'total_attempts': progress_qs.aggregate(Sum('attempts'))['attempts__sum'] or 0,
            'unique_users': progress_qs.values('user').distinct().count(),
            'completion_rate': progress_qs.filter(
                status='completed'
            ).count() / max(progress_qs.count(), 1),
            'avg_attempts': progress_qs.filter(
                status='completed'
            ).aggregate(Avg('attempts'))['attempts__avg'] or 0.0,
            'avg_hints_used': progress_qs.aggregate(Avg('hints_used'))['hints_used__avg'] or 0.0,
            'avg_score': progress_qs.filter(
                score__isnull=False
            ).aggregate(Avg('score'))['score__avg'] or 0.0
        }
    
    @classmethod
    def get_user_statistics(cls, user: User) -> Dict[str, Any]:
        """
        Get overall statistics for a user.
        
        Returns:
            Dictionary with user statistics
        """
        progress_qs = UserProgress.objects.filter(user=user)
        
        return {
            'problems_attempted': progress_qs.filter(attempts__gt=0).count(),
            'problems_completed': progress_qs.filter(status='completed').count(),
            'total_attempts': progress_qs.aggregate(Sum('attempts'))['attempts__sum'] or 0,
            'total_hints_used': progress_qs.aggregate(Sum('hints_used'))['hints_used__sum'] or 0,
            'avg_attempts_per_problem': progress_qs.filter(
                status='completed'
            ).aggregate(Avg('attempts'))['attempts__avg'] or 0.0,
            'avg_score': progress_qs.filter(
                score__isnull=False
            ).aggregate(Avg('score'))['score__avg'] or 0.0,
            'courses_enrolled': Course.objects.filter(
                enrollments__user=user,
                enrollments__is_active=True
            ).count()
        }
    
    @classmethod
    def reset_problem_progress(cls, user: User, problem: Problem,
                             course: Optional[Course] = None) -> bool:
        """Reset a user's progress for a specific problem."""
        filters = {
            'user': user,
            'problem': problem
        }
        if course:
            filters['course'] = course
            
        deleted, _ = UserProgress.objects.filter(**filters).delete()
        return deleted > 0
    
    @classmethod
    def get_or_create_with_lock(cls, user_id: int, problem_id: int,
                               problem_set_id: Optional[int] = None,
                               course_id: Optional[int] = None) -> tuple:
        """
        Get or create user progress with row-level locking.
        
        This method uses select_for_update to prevent race conditions.
        
        Returns:
            Tuple of (UserProgress, created)
        """
        return UserProgress.objects.select_for_update().get_or_create(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id,
            defaults={
                'attempts': 0,
                'best_score': 0,
                'status': 'not_started'
            }
        )
    
    @classmethod
    def get_with_lock(cls, user_id: int, problem_id: int,
                     problem_set_id: Optional[int] = None,
                     course_id: Optional[int] = None) -> Optional[UserProgress]:
        """
        Get user progress with row-level locking.
        
        Returns:
            UserProgress instance or None
        """
        return UserProgress.objects.select_for_update().filter(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id
        ).first()
    
    @classmethod
    def get_by_ids(cls, user_id: int, problem_id: int,
                   problem_set_id: Optional[int] = None,
                   course_id: Optional[int] = None) -> Optional[UserProgress]:
        """
        Get user progress by IDs.
        
        Returns:
            UserProgress instance or None
        """
        filters = {
            'user_id': user_id,
            'problem_id': problem_id
        }
        if problem_set_id:
            filters['problem_set_id'] = problem_set_id
        if course_id:
            filters['course_id'] = course_id
            
        return UserProgress.objects.filter(**filters).first()
    
    @classmethod
    def filter_by_ids(cls, user_id: int, problem_id: Optional[int] = None,
                     problem_set_id: Optional[int] = None,
                     course_id: Optional[int] = None):
        """
        Filter progress records by IDs.

        Returns:
            QuerySet of UserProgress (not evaluated - allows chaining)
        """
        filters = {'user_id': user_id}
        if problem_id:
            filters['problem_id'] = problem_id
        if problem_set_id:
            filters['problem_set_id'] = problem_set_id
        if course_id:
            filters['course_id'] = course_id

        return UserProgress.objects.filter(**filters)
    
    @classmethod
    def get_or_create_problem_set_with_lock(cls, user_id: int, problem_set_id: int,
                                           course_id: Optional[int] = None) -> tuple:
        """
        Get or create problem set progress with row-level locking.
        
        Returns:
            Tuple of (UserProblemSetProgress, created)
        """
        return UserProblemSetProgress.objects.select_for_update().get_or_create(
            user_id=user_id,
            problem_set_id=problem_set_id,
            course_id=course_id,
            defaults={
                'completed_problems': 0,
                'average_score': 0.0
            }
        )
    
    @classmethod
    def filter_problem_set_by_ids(cls, user_id: int, problem_set_id: Optional[int] = None,
                                 course_id: Optional[int] = None) -> List:
        """
        Filter problem set progress by IDs.
        
        Returns:
            QuerySet of UserProblemSetProgress
        """
        filters = {'user_id': user_id}
        if problem_set_id:
            filters['problem_set_id'] = problem_set_id
        if course_id:
            filters['course_id'] = course_id
            
        return list(UserProblemSetProgress.objects.filter(**filters))
    
    @classmethod
    def get_problem_set_progress_with_relations(cls, user_id: int, problem_set_id: int) -> Optional[Dict[str, Any]]:
        """
        Get problem set progress with related data.
        
        Returns:
            Dictionary with progress data or None
        """
        progress = UserProblemSetProgress.objects.filter(
            user_id=user_id,
            problem_set_id=problem_set_id
        ).select_related('problem_set').first()
        
        if not progress:
            return None
        
        return {
            'problem_set': progress.problem_set.slug,
            'total_problems': progress.total_problems,
            'completed_problems': progress.completed_problems,
            'in_progress_problems': progress.in_progress_problems,
            'completion_percentage': progress.completion_percentage,
            'is_completed': progress.is_completed,
            'average_score': progress.average_score,
            'last_activity': progress.last_activity
        }
    
    @classmethod
    def get_course_progress_summary_data(cls, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all course progress data for user summary.
        
        Returns:
            List of dictionaries with course progress data
        """
        course_progresses = UserProblemSetProgress.objects.filter(
            user_id=user_id,
            course__isnull=False
        ).select_related('problem_set', 'course').order_by(
            'course__course_id', 'problem_set__title'
        )
        
        result = []
        for progress in course_progresses:
            result.append({
                'course_id': progress.course.course_id,
                'course_name': progress.course.name,
                'problem_set_slug': progress.problem_set.slug,
                'problem_set_title': progress.problem_set.title,
                'completed_problems': progress.completed_problems,
                'total_problems': progress.total_problems,
                'completion_percentage': progress.completion_percentage,
                'is_completed': progress.is_completed,
                'last_activity': progress.last_activity,
            })
        
        return result
    
    @classmethod
    def get_problem_set_by_ids(cls, user_id: int, problem_set_id: int,
                              course_id: Optional[int] = None) -> Optional[UserProblemSetProgress]:
        """
        Get problem set progress by IDs.
        
        Returns:
            UserProblemSetProgress instance or None
        """
        filters = {
            'user_id': user_id,
            'problem_set_id': problem_set_id
        }
        if course_id:
            filters['course_id'] = course_id
            
        return UserProblemSetProgress.objects.filter(**filters).first()
    
    @classmethod
    def get_user_course_progress(cls, user: User, course: Course) -> List:
        """
        Get all user progress records for a specific course.
        
        Args:
            user: The user
            course: The course
            
        Returns:
            QuerySet of UserProgress records
        """
        return list(UserProgress.objects.filter(
            user=user,
            course=course
        ).select_related('problem', 'problem_set'))
    
    @classmethod
    def get_user_problem_set_progress_bulk(cls, user: User, problem_set_ids: List[int], 
                                          courses: List[Course]) -> List:
        """
        Get user's progress for multiple problem sets across multiple courses.
        
        Args:
            user: The user
            problem_set_ids: List of problem set IDs
            courses: List of courses
            
        Returns:
            QuerySet of UserProblemSetProgress records
        """
        course_ids = [course.id for course in courses]
        return list(UserProblemSetProgress.objects.filter(
            user=user,
            problem_set_id__in=problem_set_ids,
            course_id__in=course_ids
        ).select_related('problem_set', 'course'))
    
    @classmethod
    def get_user_course_progress_by_id(cls, user_id: int, course_id: int) -> List[Dict[str, Any]]:
        """
        Get user's progress for all problems in a course.
        
        Args:
            user_id: ID of the user
            course_id: ID of the course
            
        Returns:
            List of dicts with progress data
        """
        progress_records = UserProgress.objects.filter(
            user_id=user_id,
            course_id=course_id
        ).select_related('problem', 'problem_set')
        
        return [
            {
                'problem_id': p.problem_id,
                'problem_set_id': p.problem_set_id,
                'problem_set_title': p.problem_set.title if p.problem_set else '',
                'total_problems': p.problem_set.problems.count() if p.problem_set else 0,
                'attempts': p.attempts,
                'is_completed': p.is_completed,
                'best_score': p.best_score,
                'last_submission_at': p.last_submission_at
            }
            for p in progress_records
        ]
    
    @classmethod
    def get_user_problem_set_progress_for_course(cls, user_id: int, problem_set_ids: List[int], 
                                                 course_id: int) -> List[Dict[str, Any]]:
        """
        Get user's progress for specific problem sets in a course.
        
        Args:
            user_id: ID of the user
            problem_set_ids: List of problem set IDs
            course_id: ID of the course
            
        Returns:
            List of dicts with problem set progress data
        """
        if not problem_set_ids:
            return []
        
        progress_records = UserProblemSetProgress.objects.filter(
            user_id=user_id,
            problem_set_id__in=problem_set_ids,
            course_id=course_id
        ).select_related('problem_set')
        
        return [
            {
                'problem_set_id': p.problem_set_id,
                'completed_problems': p.completed_problems,
                'total_problems': p.total_problems,
                'is_completed': p.is_completed,
                'completion_percentage': p.completion_percentage,
                'last_activity': p.last_activity
            }
            for p in progress_records
        ]
    
    @classmethod
    def get_user_problem_set_progress_by_course(cls, user: User, problem_set_ids: List[int], 
                                               course: Course) -> List:
        """
        Get user's progress for multiple problem sets within a specific course.
        
        Args:
            user: The user
            problem_set_ids: List of problem set IDs
            course: The course
            
        Returns:
            List of UserProblemSetProgress records
        """
        return list(UserProblemSetProgress.objects.filter(
            user=user,
            problem_set_id__in=problem_set_ids,
            course=course
        ).select_related('problem_set'))