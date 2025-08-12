"""Service layer for hint-related business logic."""

import logging
from typing import Dict, List, Optional, Any
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from ..models import Problem, ProblemHint, UserProgress

logger = logging.getLogger(__name__)


class HintService:
    """Handle all hint-related business logic."""
    
    # Hint type mappings
    HINT_TYPE_CHOICES = {
        'variable_fade': 'variable_fade',
        'subgoal': 'subgoal_hints',
        'trace': 'trace'
    }
    
    @staticmethod
    def get_hint_availability(
        user, 
        problem_slug: str,
        course_id: Optional[str] = None,
        problem_set_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check hint availability for a user on a specific problem.
        
        Args:
            user: User instance
            problem_slug: Problem slug
            course_id: Optional course ID for context
            problem_set_slug: Optional problem set slug for context
            
        Returns:
            Dictionary with hint availability information
        """
        from ..models import ProblemSet, Course
        
        problem = get_object_or_404(Problem, slug=problem_slug)
        
        # Get optional context
        problem_set = None
        course = None
        
        if problem_set_slug:
            problem_set = get_object_or_404(ProblemSet, slug=problem_set_slug)
            
        if course_id:
            course = get_object_or_404(Course, course_id=course_id)
        
        # Get user progress with context
        try:
            if problem_set:
                progress = UserProgress.objects.get(
                    user=user, 
                    problem=problem,
                    problem_set=problem_set,
                    course=course
                )
            else:
                progress = UserProgress.objects.get(user=user, problem=problem)
            attempts = progress.attempts
        except UserProgress.DoesNotExist:
            attempts = 0
        
        # Get all hints for the problem
        hints = ProblemHint.objects.filter(problem=problem).values(
            'id', 'hint_type', 'min_attempts', 'order'
        )
        
        # Build availability response
        availability = {
            'problem_slug': problem_slug,
            'user_attempts': attempts,
            'hints': []
        }
        
        for hint in hints:
            hint_info = {
                'id': hint['id'],
                'type': hint['hint_type'],
                'order': hint['order'],
                'min_attempts': hint['min_attempts'],
                'available': attempts >= hint['min_attempts'],
                'attempts_needed': max(0, hint['min_attempts'] - attempts)
            }
            availability['hints'].append(hint_info)
        
        # Sort by order
        availability['hints'].sort(key=lambda x: x['order'])
        
        return availability
    
    @staticmethod
    def get_hint_content(
        user, 
        problem_slug: str, 
        hint_type: str,
        course_id: Optional[str] = None,
        problem_set_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get specific hint content if user has access.
        
        Args:
            user: User instance
            problem_slug: Problem slug
            hint_type: Type of hint requested
            course_id: Optional course ID for context
            problem_set_slug: Optional problem set slug for context
            
        Returns:
            Dictionary with hint content or error information
        """
        from ..models import Problem, ProblemSet, Course, CourseEnrollment
        
        # Get the problem
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return {
                'error': 'not_found',
                'message': 'Problem not found'
            }
        
        # Validate hint type
        valid_hint_types = [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]
        if hint_type not in valid_hint_types:
            return {
                'error': 'invalid_type',
                'message': f'Invalid hint type. Must be one of: {", ".join(valid_hint_types)}'
            }
        
        # Validate course and problem set if provided
        course = None
        problem_set = None
        
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return {
                        'error': 'invalid_context',
                        'message': 'Problem does not belong to the specified problem set'
                    }
            except ProblemSet.DoesNotExist:
                return {
                    'error': 'not_found',
                    'message': 'Problem set not found'
                }
        
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                if not CourseEnrollment.objects.filter(user=user, course=course, is_active=True).exists():
                    return {
                        'error': 'forbidden',
                        'message': 'You are not enrolled in this course'
                    }
            except Course.DoesNotExist:
                return {
                    'error': 'not_found',
                    'message': 'Course not found'
                }
        
        # Get the hint
        try:
            hint = ProblemHint.objects.get(problem=problem, hint_type=hint_type)
        except ProblemHint.DoesNotExist:
            return {
                'error': 'not_found',
                'message': 'Hint not found for this problem'
            }
        
        # Check if hint is enabled
        if not hint.is_enabled:
            return {
                'error': 'disabled',
                'message': 'This hint is not enabled'
            }
        
        # Get user attempts with context
        user_attempts = 0
        if problem_set:
            try:
                progress = UserProgress.objects.get(
                    user=user,
                    problem=problem,
                    problem_set=problem_set,
                    course=course
                )
                user_attempts = progress.attempts
            except UserProgress.DoesNotExist:
                user_attempts = 0
        else:
            try:
                progress = UserProgress.objects.get(user=user, problem=problem)
                user_attempts = progress.attempts
            except UserProgress.DoesNotExist:
                user_attempts = 0
        
        # Check if user has enough attempts
        if user_attempts < hint.min_attempts:
            return {
                'error': 'insufficient_attempts',
                'message': f'You need {hint.min_attempts - user_attempts} more attempts before this hint is available',
                'attempts_needed': hint.min_attempts - user_attempts,
                'current_attempts': user_attempts,
                'min_attempts': hint.min_attempts
            }
        
        # Return hint content
        return {
            'type': hint.hint_type,
            'content': hint.content,
            'min_attempts': hint.min_attempts,
            'success': True
        }
    
    @staticmethod
    def record_hint_usage(user, problem_slug: str, hint_type: str) -> bool:
        """
        Record that a user has used a hint.
        
        Args:
            user: User instance
            problem_slug: Problem slug
            hint_type: Type of hint used
            
        Returns:
            True if recorded successfully
        """
        try:
            problem = Problem.objects.get(slug=problem_slug)
            hint = ProblemHint.objects.get(
                problem=problem,
                hint_type=HintService.HINT_TYPE_CHOICES.get(hint_type, hint_type)
            )
            
            # Record usage (could be extended to track in a separate model)
            logger.info(f"User {user.id} used {hint_type} hint for problem {problem_slug}")
            
            # Invalidate any cached hint data
            cache_key = f'hint_usage:{user.id}:{problem_slug}'
            cache.delete(cache_key)
            
            return True
            
        except (Problem.DoesNotExist, ProblemHint.DoesNotExist) as e:
            logger.error(f"Error recording hint usage: {e}")
            return False
    
    @staticmethod
    def get_cached_hint_availability(user, problem_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get cached hint availability or compute and cache it.
        
        Args:
            user: User instance
            problem_slug: Problem slug
            
        Returns:
            Hint availability data
        """
        cache_key = f'hint_availability:{user.id}:{problem_slug}'
        availability = cache.get(cache_key)
        
        if availability is None:
            availability = HintService.get_hint_availability(user, problem_slug)
            # Cache for 5 minutes
            cache.set(cache_key, availability, 300)
        
        return availability
    
    @staticmethod
    def invalidate_hint_cache(user, problem_slug: str):
        """
        Invalidate hint-related cache for a user and problem.
        
        Args:
            user: User instance
            problem_slug: Problem slug
        """
        cache_keys = [
            f'hint_availability:{user.id}:{problem_slug}',
            f'hint_usage:{user.id}:{problem_slug}'
        ]
        
        for key in cache_keys:
            cache.delete(key)


class AdminHintService:
    """Handle hint administration business logic."""
    
    @staticmethod
    def get_problem_hints_config(problem_slug: str) -> Dict[str, Any]:
        """
        Get all hint configurations for a problem, including defaults for missing types.
        
        Args:
            problem_slug: Problem slug
            
        Returns:
            Dictionary with problem slug and hint configurations
        """
        from ..models import Problem, ProblemHint
        
        try:
            problem = Problem.objects.get(slug=problem_slug)
        except Problem.DoesNotExist:
            raise ValueError(f"Problem with slug {problem_slug} not found")
        
        # Get all hints for this problem
        hints = ProblemHint.objects.filter(problem=problem)
        
        # Build response with all hint types
        hint_configs = []
        hint_types_found = set()
        
        # Add existing hints
        for hint in hints:
            hint_configs.append({
                'type': hint.hint_type,
                'is_enabled': hint.is_enabled,
                'min_attempts': hint.min_attempts,
                'content': hint.content
            })
            hint_types_found.add(hint.hint_type)
        
        # Add default configs for missing hint types
        for hint_type, display_name in ProblemHint.HINT_TYPE_CHOICES:
            if hint_type not in hint_types_found:
                default_content = {
                    'variable_fade': {'mappings': []},
                    'subgoal_highlight': {'subgoals': []},
                    'suggested_trace': {'suggested_call': '', 'explanation': ''}
                }
                hint_configs.append({
                    'type': hint_type,
                    'is_enabled': False,
                    'min_attempts': 3,
                    'content': default_content.get(hint_type, {})
                })
        
        return {
            'problem_slug': problem.slug,
            'hints': hint_configs
        }
    
    @staticmethod
    def bulk_update_hints(problem_slug: str, hints_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update all hint types for a problem.
        
        Args:
            problem_slug: Problem slug
            hints_data: List of hint configurations
            
        Returns:
            Dictionary with updated hint configurations
        """
        from django.db import transaction
        from django.core.exceptions import ValidationError
        from ..models import Problem, ProblemHint
        
        try:
            problem = Problem.objects.get(slug=problem_slug)
        except Problem.DoesNotExist:
            raise ValueError(f"Problem with slug {problem_slug} not found")
        
        if not isinstance(hints_data, list):
            raise ValueError("hints must be an array of hint configurations")
        
        # Validate hint types
        valid_hint_types = [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]
        
        try:
            with transaction.atomic():
                updated_hints = []
                
                for hint_data in hints_data:
                    # Validate required fields
                    hint_type = hint_data.get('type')
                    if not hint_type:
                        raise ValueError("Each hint must have a type field")
                    
                    if hint_type not in valid_hint_types:
                        raise ValueError(
                            f'Invalid hint type: {hint_type}. Must be one of: {", ".join(valid_hint_types)}'
                        )
                    
                    # Get or create the hint
                    hint, created = ProblemHint.objects.get_or_create(
                        problem=problem,
                        hint_type=hint_type,
                        defaults={
                            'is_enabled': hint_data.get('is_enabled', False),
                            'min_attempts': hint_data.get('min_attempts', 3),
                            'content': hint_data.get('content', {})
                        }
                    )
                    
                    # Update existing hint
                    if not created:
                        hint.is_enabled = hint_data.get('is_enabled', hint.is_enabled)
                        hint.min_attempts = hint_data.get('min_attempts', hint.min_attempts)
                        hint.content = hint_data.get('content', hint.content)
                    
                    # Validate the hint content structure
                    hint.clean()
                    hint.save()
                    
                    updated_hints.append({
                        'type': hint.hint_type,
                        'is_enabled': hint.is_enabled,
                        'min_attempts': hint.min_attempts,
                        'content': hint.content,
                        'created': created
                    })
                
                return {
                    'problem_slug': problem.slug,
                    'hints': updated_hints
                }
                
        except ValidationError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to update hints for problem {problem_slug}: {str(e)}")
            raise RuntimeError("Failed to update hints. Please check the hint configurations.")