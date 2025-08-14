"""Service for managing user progress with transaction safety and caching."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.db import transaction, models
from django.db.models import F, Q, Prefetch, Count, Avg
from django.core.cache import cache
from django.contrib.auth.models import User

from ..models import (
    UserProgress, UserProblemSetProgress, Problem, ProblemSet, 
    Course
)
from purplex.submissions_app.models import PromptSubmission as Submission

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for managing user progress with proper locking and caching."""
    
    @staticmethod
    @transaction.atomic
    def update_user_progress(
        user_id: int, 
        problem_id: int, 
        submission: 'Submission',
        problem_set_id: Optional[int] = None,
        course_id: Optional[int] = None
    ) -> UserProgress:
        """
        Update user progress for a problem with row-level locking.
        
        This method uses select_for_update to prevent race conditions when multiple
        submissions are processed concurrently.
        """
        try:
            # Get or create progress with locking
            progress, created = UserProgress.objects.select_for_update().get_or_create(
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
            
            # Update progress metrics
            progress.attempts = F('attempts') + 1
            progress.last_attempt = datetime.now()
            
            # Update score if better
            if submission.score > progress.best_score:
                progress.best_score = submission.score
                
            # Update status based on score
            if submission.score >= 100:
                progress.status = 'completed'
                progress.is_completed = True
                progress.completion_percentage = 100
                if not progress.completed_at:
                    progress.completed_at = datetime.now()
            elif submission.score > 0:
                progress.status = 'in_progress'
                progress.completion_percentage = submission.score
            
            progress.save()
            
            # Invalidate relevant caches
            ProgressService._invalidate_progress_cache(user_id, problem_id, problem_set_id)
            
            # Update problem set progress if applicable
            if problem_set_id:
                ProgressService._update_problem_set_progress(
                    user_id, problem_set_id, course_id
                )
            
            logger.info(
                f"Updated progress for user {user_id} on problem {problem_id}: "
                f"attempts={progress.attempts}, best_score={progress.best_score}"
            )
            
            return progress
            
        except Exception as e:
            logger.error(f"Error updating user progress: {str(e)}")
            raise
    
    @staticmethod
    def get_user_progress(
        user_id: int,
        problem_id: int,
        problem_set_id: Optional[int] = None,
        course_id: Optional[int] = None
    ) -> Optional[UserProgress]:
        """
        Get user progress for a specific problem.
        
        Args:
            user_id: User ID
            problem_id: Problem ID
            problem_set_id: Optional problem set ID for context
            course_id: Optional course ID for context
            
        Returns:
            UserProgress instance or None
        """
        try:
            return UserProgress.objects.get(
                user_id=user_id,
                problem_id=problem_id,
                problem_set_id=problem_set_id,
                course_id=course_id
            )
        except UserProgress.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def bulk_update_progress(
        user_id: int,
        updates: List[Dict[str, Any]]
    ) -> List[UserProgress]:
        """
        Bulk update multiple progress records with transaction safety.
        
        Args:
            user_id: User ID
            updates: List of dicts with problem_id, score, status, etc.
        """
        updated_progress = []
        
        for update in updates:
            problem_id = update.get('problem_id')
            if not problem_id:
                continue
                
            progress = UserProgress.objects.select_for_update().filter(
                user_id=user_id,
                problem_id=problem_id
            ).first()
            
            if progress:
                for field, value in update.items():
                    if field != 'problem_id' and hasattr(progress, field):
                        setattr(progress, field, value)
                progress.save()
                updated_progress.append(progress)
        
        # Clear user's progress cache
        cache_key = f'user_progress_all:{user_id}'
        cache.delete(cache_key)
        
        return updated_progress
    
    @staticmethod
    def get_cached_progress(
        user_id: int,
        problem_id: Optional[int] = None,
        problem_set_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached progress data with fallback to database.
        
        Returns:
            Progress data dict or None if not found
        """
        # Build cache key
        if problem_id:
            cache_key = f'user_progress:{user_id}:problem:{problem_id}'
        elif problem_set_id:
            cache_key = f'user_progress:{user_id}:set:{problem_set_id}'
        else:
            cache_key = f'user_progress_all:{user_id}'
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        if problem_id:
            progress = UserProgress.objects.filter(
                user_id=user_id,
                problem_id=problem_id
            ).select_related('problem').first()
            
            if progress:
                data = {
                    'problem_slug': progress.problem.slug,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                    'completed_at': progress.completed_at,
                }
                # Cache for 5 minutes
                cache.set(cache_key, data, 300)
                return data
                
        elif problem_set_id:
            progress = UserProblemSetProgress.objects.filter(
                user_id=user_id,
                problem_set_id=problem_set_id
            ).select_related('problem_set').first()
            
            if progress:
                data = {
                    'problem_set': progress.problem_set.slug,
                    'total_problems': progress.total_problems,
                    'completed_problems': progress.completed_problems,
                    'in_progress_problems': progress.in_progress_problems,
                    'completion_percentage': progress.completion_percentage,
                    'is_completed': progress.is_completed,
                    'average_score': progress.average_score,
                    'last_activity': progress.last_activity,
                }
                # Cache for 5 minutes
                cache.set(cache_key, data, 300)
                return data
        
        return None
    
    @staticmethod
    def get_all_user_progress(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all progress records for a user with caching.
        
        Args:
            user_id: User ID
            
        Returns:
            List of progress dictionaries
        """
        # Try cache first
        cache_key = f'user_progress_all:{user_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch from database with optimized query
        progress_list = UserProgress.objects.filter(
            user_id=user_id
        ).select_related('problem').prefetch_related('problem__categories')
        
        progress_data = []
        for progress in progress_list:
            progress_data.append({
                'problem_slug': progress.problem.slug,
                'problem_title': progress.problem.title,
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
                'completion_percentage': progress.completion_percentage,
                'last_attempt': progress.last_attempt,
                'completed_at': progress.completed_at
            })
        
        # Cache for 5 minutes
        cache.set(cache_key, progress_data, 300)
        
        return progress_data
    
    @staticmethod
    def get_problem_progress(user_id: int, problem_slug: str) -> Dict[str, Any]:
        """
        Get progress for a specific problem.
        
        Args:
            user_id: User ID
            problem_slug: Problem slug
            
        Returns:
            Progress dictionary or default values if not found
        """
        try:
            from ..models import Problem
            problem = Problem.objects.get(slug=problem_slug)
            
            try:
                progress = UserProgress.objects.get(user_id=user_id, problem=problem)
                return {
                    'problem_slug': problem.slug,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                    'completed_at': progress.completed_at,
                }
            except UserProgress.DoesNotExist:
                # Return default values
                return {
                    'problem_slug': problem.slug,
                    'status': 'not_started',
                    'best_score': 0,
                    'attempts': 0,
                    'is_completed': False,
                    'completion_percentage': 0,
                    'last_attempt': None,
                    'completed_at': None,
                }
        except Problem.DoesNotExist:
            raise ValueError(f"Problem with slug {problem_slug} not found")
    
    @staticmethod
    def _update_problem_set_progress(
        user_id: int,
        problem_set_id: int,
        course_id: Optional[int] = None
    ):
        """Update problem set progress based on individual problem progress."""
        try:
            # Get or create problem set progress with locking
            set_progress, _ = UserProblemSetProgress.objects.select_for_update().get_or_create(
                user_id=user_id,
                problem_set_id=problem_set_id,
                course_id=course_id,
                defaults={'total_problems': 0}
            )
            
            # Calculate aggregate metrics
            problem_progress = UserProgress.objects.filter(
                user_id=user_id,
                problem_set_id=problem_set_id,
                course_id=course_id
            ).aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(is_completed=True)),
                in_progress=Count('id', filter=Q(status='in_progress')),
                avg_score=Avg('best_score')
            )
            
            # Update set progress
            set_progress.total_problems = problem_progress['total'] or 0
            set_progress.completed_problems = problem_progress['completed'] or 0
            set_progress.in_progress_problems = problem_progress['in_progress'] or 0
            set_progress.average_score = problem_progress['avg_score'] or 0
            
            if set_progress.total_problems > 0:
                set_progress.completion_percentage = int(
                    (set_progress.completed_problems / set_progress.total_problems) * 100
                )
                set_progress.is_completed = (
                    set_progress.completed_problems == set_progress.total_problems
                )
            
            set_progress.last_activity = datetime.now()
            set_progress.save()
            
            # Invalidate problem set cache
            cache_key = f'user_progress:set:{problem_set_id}:{user_id}'
            cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error updating problem set progress: {str(e)}")
    
    @staticmethod
    def _invalidate_progress_cache(
        user_id: int,
        problem_id: Optional[int] = None,
        problem_set_id: Optional[int] = None
    ):
        """Invalidate relevant cache entries after progress update."""
        cache_keys = [
            f'user_progress_all:{user_id}',
        ]
        
        if problem_id:
            cache_keys.append(f'user_progress:{user_id}:problem:{problem_id}')
        
        if problem_set_id:
            cache_keys.append(f'user_progress:{user_id}:set:{problem_set_id}')
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def get_user_summary(user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive summary of user's progress across all courses.
        Uses caching to reduce database load.
        """
        cache_key = f'user_progress_summary:{user_id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            # Build summary from database
            course_progresses = UserProblemSetProgress.objects.filter(
                user_id=user_id,
                course__isnull=False
            ).select_related('problem_set', 'course').order_by(
                'course__course_id', 'problem_set__title'
            )
            
            course_data = {}
            total_problems = 0
            total_completed = 0
            
            for progress in course_progresses:
                course_id = progress.course.course_id
                if course_id not in course_data:
                    course_data[course_id] = {
                        'course_name': progress.course.name,
                        'problem_sets': []
                    }
                
                course_data[course_id]['problem_sets'].append({
                    'problem_set_slug': progress.problem_set.slug,
                    'problem_set_title': progress.problem_set.title,
                    'completed_problems': progress.completed_problems,
                    'total_problems': progress.total_problems,
                    'completion_percentage': progress.completion_percentage,
                    'is_completed': progress.is_completed,
                    'last_activity': progress.last_activity,
                })
                
                total_problems += progress.total_problems
                total_completed += progress.completed_problems
            
            summary = {
                'overall': {
                    'total_problems': total_problems,
                    'completed_problems': total_completed,
                    'completion_percentage': int(
                        (total_completed / total_problems * 100) if total_problems > 0 else 0
                    ),
                },
                'courses': course_data
            }
            
            # Cache for 10 minutes
            cache.set(cache_key, summary, 600)
        
        return summary