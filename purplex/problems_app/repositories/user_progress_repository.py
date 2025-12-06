"""
Repository for UserProgress model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Count, Avg, Sum, Max
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from purplex.problems_app.models import UserProgress, Problem, ProblemSet, Course
from .base_repository import BaseRepository


class UserProgressRepository(BaseRepository):
    """
    Repository for all UserProgress-related database queries.
    
    This repository handles all data access for user progress tracking,
    including problem completion, scoring, and timing analytics.
    """
    
    model_class = UserProgress
    
    @classmethod
    def get_user_problem_progress(cls, user: User, problem: Problem, 
                                 problem_set: Optional[ProblemSet] = None, 
                                 course: Optional[Course] = None) -> Optional[UserProgress]:
        """Get progress for a specific user-problem combination."""
        return UserProgress.objects.filter(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course
        ).first()
    
    @classmethod
    def get_or_create_progress(cls, user: User, problem: Problem, 
                              problem_set: Optional[ProblemSet] = None,
                              course: Optional[Course] = None) -> tuple:
        """Get or create progress record for a user-problem combination."""
        return UserProgress.objects.get_or_create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            defaults={
                'problem_version': problem.version,
                'status': 'not_started'
            }
        )
    
    @classmethod
    def get_user_progress_in_problem_set(cls, user: User, problem_set: ProblemSet,
                                        course: Optional[Course] = None) -> List:
        """Get all progress records for a user in a specific problem set."""
        return list(UserProgress.objects.filter(
            user=user,
            problem_set=problem_set,
            course=course
        ).order_by('problem__title'))
    
    @classmethod
    def get_user_progress_in_course(cls, user: User, course: Course) -> List:
        """Get all progress records for a user in a specific course."""
        return list(UserProgress.objects.filter(
            user=user,
            course=course
        ).select_related('problem_set').order_by('-last_attempt'))
    
    @classmethod
    def get_completed_problems(cls, user: User, problem_set: Optional[ProblemSet] = None,
                              course: Optional[Course] = None) -> List:
        """Get all completed problems for a user."""
        filters = {
            'user': user,
            'is_completed': True
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters))

    @classmethod
    def get_in_progress_problems(cls, user: User, problem_set: Optional[ProblemSet] = None,
                                course: Optional[Course] = None) -> List:
        """Get all in-progress problems for a user."""
        filters = {
            'user': user,
            'status': 'in_progress'
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters))

    @classmethod
    def get_user_statistics(cls, user: User, problem_set: Optional[ProblemSet] = None,
                           course: Optional[Course] = None) -> Dict[str, Any]:
        """Get comprehensive statistics for a user's progress."""
        filters = {'user': user}
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        stats = UserProgress.objects.filter(**filters).aggregate(
            total_problems=Count('id'),
            completed_problems=Count('id', filter=Q(is_completed=True)),
            in_progress_problems=Count('id', filter=Q(status='in_progress')),
            average_score=Avg('best_score'),
            total_attempts=Sum('attempts'),
            total_time_spent=Sum('total_time_spent'),
            best_score=Max('best_score'),
            hints_used_total=Sum('hints_used'),
            avg_completion_percentage=Avg('completion_percentage')
        )
        
        # Calculate completion rate
        total = stats['total_problems'] or 0
        completed = stats['completed_problems'] or 0
        stats['completion_rate'] = (completed / total * 100) if total > 0 else 0
        
        return stats
    
    @classmethod
    def get_recent_activity(cls, user: User, days: int = 7,
                           problem_set: Optional[ProblemSet] = None,
                           course: Optional[Course] = None) -> List:
        """Get user's recent progress activity."""
        since_date = timezone.now() - timedelta(days=days)
        filters = {
            'user': user,
            'last_attempt__gte': since_date
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters).select_related(
            'problem_set'
        ).order_by('-last_attempt'))
    
    @classmethod
    def get_struggling_problems(cls, user: User, min_attempts: int = 5,
                               max_score: int = 50,
                               problem_set: Optional[ProblemSet] = None,
                               course: Optional[Course] = None) -> List:
        """Get problems where user is struggling (many attempts, low scores)."""
        filters = {
            'user': user,
            'attempts__gte': min_attempts,
            'best_score__lte': max_score,
            'is_completed': False
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters).order_by(
            '-attempts', 'best_score'
        ))
    
    @classmethod
    def get_progress_by_difficulty(cls, user: User, difficulty: str,
                                  problem_set: Optional[ProblemSet] = None,
                                  course: Optional[Course] = None) -> List:
        """Get user progress filtered by problem difficulty."""
        filters = {
            'user': user,
            'problem__difficulty': difficulty
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters))

    @classmethod
    def get_fastest_completions(cls, user: User, limit: int = 10,
                               problem_set: Optional[ProblemSet] = None,
                               course: Optional[Course] = None) -> List:
        """Get user's fastest problem completions."""
        filters = {
            'user': user,
            'is_completed': True,
            'days_to_complete__isnull': False
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters).order_by(
            'days_to_complete'
        )[:limit])
    
    @classmethod
    def get_high_scorers(cls, problem: Problem, limit: int = 10,
                        problem_set: Optional[ProblemSet] = None,
                        course: Optional[Course] = None) -> List:
        """Get top scorers for a specific problem."""
        filters = {
            'problem': problem,
            'is_completed': True
        }
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        return list(UserProgress.objects.filter(**filters).select_related(
            'user'
        ).order_by('-best_score', 'completed_at')[:limit])
    
    @classmethod
    def get_problem_statistics(cls, problem: Problem,
                              problem_set: Optional[ProblemSet] = None,
                              course: Optional[Course] = None) -> Dict[str, Any]:
        """Get statistics for a specific problem across all users."""
        filters = {'problem': problem}
        if problem_set:
            filters['problem_set'] = problem_set
        if course:
            filters['course'] = course
        
        stats = UserProgress.objects.filter(**filters).aggregate(
            total_users=Count('user', distinct=True),
            completed_users=Count('user', filter=Q(is_completed=True)),
            average_score=Avg('best_score'),
            average_attempts=Avg('attempts'),
            total_attempts=Sum('attempts'),
            average_time=Avg('total_time_spent'),
            average_hints_used=Avg('hints_used')
        )
        
        # Calculate completion rate
        total = stats['total_users'] or 0
        completed = stats['completed_users'] or 0
        stats['completion_rate'] = (completed / total * 100) if total > 0 else 0
        
        return stats
    
    @classmethod
    def bulk_update_completion_status(cls, user: User, problem_set: ProblemSet,
                                     course: Optional[Course] = None) -> int:
        """
        Bulk update completion status for all problems in a set with proper locking.

        FIXED: Now uses transaction.atomic and select_for_update to prevent race conditions.
        """
        from django.db import transaction

        filters = {
            'user': user,
            'problem_set': problem_set
        }
        if course:
            filters['course'] = course

        # FIXED: Wrap in atomic transaction with locking
        with transaction.atomic():
            # Lock all relevant records upfront
            progress_records = UserProgress.objects.select_for_update().filter(**filters)
            updated_count = 0

            for progress in progress_records:
                old_completed = progress.is_completed
                threshold = progress.problem.completion_threshold or 100
                progress.is_completed = progress.best_score >= threshold
                progress.completion_percentage = progress.best_score

                if progress.is_completed != old_completed:
                    if progress.is_completed and not progress.completed_at:
                        progress.completed_at = timezone.now()
                    progress.save()
                    updated_count += 1

        return updated_count
    
    @classmethod
    def get_learning_path_progress(cls, user: User, course: Course) -> List[Dict[str, Any]]:
        """Get structured progress data for learning path visualization."""
        progress_records = UserProgress.objects.filter(
            user=user,
            course=course
        ).select_related('problem_set').order_by('problem_set__order', 'problem__title')
        
        learning_path = []
        for progress in progress_records:
            learning_path.append({
                'problem_set': progress.problem_set.title,
                'problem': progress.problem.title,
                'problem_slug': progress.problem.slug,
                'status': progress.status,
                'best_score': progress.best_score,
                'completion_percentage': progress.completion_percentage,
                'attempts': progress.attempts,
                'last_attempt': progress.last_attempt,
                'is_completed': progress.is_completed,
                'hints_used': progress.hints_used
            })
        
        return learning_path
    
    @classmethod
    def reset_user_progress(cls, user: User, problem: Problem,
                           problem_set: Optional[ProblemSet] = None,
                           course: Optional[Course] = None) -> bool:
        """
        Reset progress for a specific user-problem combination with proper locking.

        FIXED: Now uses select_for_update() within atomic transaction to prevent race conditions.
        """
        from django.db import transaction

        try:
            with transaction.atomic():
                # FIXED: Lock the record before modifying
                progress = cls.get_user_problem_progress(user, problem, problem_set, course)
                if progress:
                    # Re-fetch with lock to ensure exclusive access
                    progress = UserProgress.objects.select_for_update().get(pk=progress.pk)

                    # Reset to initial state
                    progress.status = 'not_started'
                    progress.best_score = 0
                    progress.average_score = 0
                    progress.attempts = 0
                    progress.successful_attempts = 0
                    progress.first_attempt = None
                    progress.last_attempt = None
                    progress.completed_at = None
                    progress.total_time_spent = timedelta(0)
                    progress.hints_used = 0
                    progress.consecutive_successes = 0
                    progress.days_to_complete = None
                    progress.is_completed = False
                    progress.completion_percentage = 0
                    progress.save()
                    return True
        except Exception:
            pass
        return False
    
    @classmethod
    def get_user_statistics(cls, user: User) -> Dict[str, Any]:
        """
        Get aggregate statistics for a user's progress.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with user statistics
        """
        stats = UserProgress.objects.filter(user=user).aggregate(
            problems_attempted=Count('id'),
            problems_solved=Count('id', filter=Q(is_completed=True)),
            avg_attempts=Avg('attempts')
        )
        
        # Handle None values
        stats['problems_attempted'] = stats['problems_attempted'] or 0
        stats['problems_solved'] = stats['problems_solved'] or 0
        stats['avg_attempts'] = stats['avg_attempts'] or 0.0
        
        return stats