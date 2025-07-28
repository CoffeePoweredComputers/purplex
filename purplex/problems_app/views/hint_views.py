"""Views for managing and accessing problem hints."""

import logging
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import Problem, ProblemSet, Course, CourseEnrollment, UserProgress, ProblemHint
from purplex.users_app.permissions import IsAuthenticated, IsAdmin

logger = logging.getLogger(__name__)


class ProblemHintAvailabilityView(APIView):
    """Get hint availability for a problem based on user's attempts."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug, is_active=True)
        user = request.user
        
        # Get optional course context parameters
        query_params = getattr(request, 'query_params', request.GET)
        course_id = query_params.get('course_id')
        problem_set_slug = query_params.get('problem_set_slug')
        
        # Validate course and problem set if provided
        course = None
        problem_set = None
        
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                # Verify user is enrolled
                if not CourseEnrollment.objects.filter(user=user, course=course, is_active=True).exists():
                    return Response({
                        'error': 'You are not enrolled in this course'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                # Verify problem belongs to problem set
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem does not belong to the specified problem set'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ProblemSet.DoesNotExist:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get user's progress
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
        
        # Get only enabled hints for the problem
        hints = ProblemHint.objects.filter(problem=problem, is_enabled=True)
        
        # Build hint availability response - only for enabled hints
        available_hints = []
        for hint in hints:
            available_hints.append({
                'type': hint.hint_type,
                'title': hint.get_hint_type_display(),
                'description': f'Get help with {hint.get_hint_type_display().lower()}',
                'unlocked': user_attempts >= hint.min_attempts,
                'available': user_attempts >= hint.min_attempts,
                'attempts_needed': max(0, hint.min_attempts - user_attempts)
            })
        
        # TODO: Track which hints the user has used (for future implementation)
        hints_used = []
        
        return Response({
            'available_hints': available_hints,
            'hints_used': hints_used,
            'current_attempts': user_attempts
        })


class ProblemHintDetailView(APIView):
    """Get specific hint content for a problem."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug, hint_type):
        problem = get_object_or_404(Problem, slug=slug, is_active=True)
        user = request.user
        
        # Validate hint type
        valid_hint_types = [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]
        if hint_type not in valid_hint_types:
            return Response({
                'error': f'Invalid hint type. Must be one of: {", ".join(valid_hint_types)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get optional course context parameters
        query_params = getattr(request, 'query_params', request.GET)
        course_id = query_params.get('course_id')
        problem_set_slug = query_params.get('problem_set_slug')
        
        # Validate course and problem set if provided
        course = None
        problem_set = None
        
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem does not belong to the specified problem set'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ProblemSet.DoesNotExist:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                if not CourseEnrollment.objects.filter(user=user, course=course, is_active=True).exists():
                    return Response({
                        'error': 'You are not enrolled in this course'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get the hint
        try:
            hint = ProblemHint.objects.get(problem=problem, hint_type=hint_type)
        except ProblemHint.DoesNotExist:
            return Response({
                'error': 'Hint not found for this problem'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if hint is enabled
        if not hint.is_enabled:
            return Response({
                'error': 'This hint is not enabled'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user has enough attempts
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
        
        if user_attempts < hint.min_attempts:
            return Response({
                'error': f'You need {hint.min_attempts - user_attempts} more attempts before this hint is available'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Return hint content
        return Response({
            'type': hint.hint_type,
            'content': hint.content,
            'min_attempts': hint.min_attempts
        })


class AdminProblemHintView(APIView):
    """Admin endpoint to manage hints for a problem."""
    permission_classes = [IsAdmin]
    
    def get(self, request, slug):
        """Get all hint configurations for a problem"""
        problem = get_object_or_404(Problem, slug=slug)
        
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
        
        return Response({
            'problem_slug': problem.slug,
            'hints': hint_configs
        })
    
    def put(self, request, slug):
        """Bulk update all hint types for a problem"""
        problem = get_object_or_404(Problem, slug=slug)
        
        # Expect data in format:
        # {
        #   "hints": [
        #     {
        #       "type": "variable_fade",
        #       "is_enabled": true,
        #       "min_attempts": 3,
        #       "content": {...}
        #     },
        #     ...
        #   ]
        # }
        
        hints_data = request.data.get('hints', [])
        if not isinstance(hints_data, list):
            return Response({
                'error': 'hints must be an array of hint configurations'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate hint types
        valid_hint_types = [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]
        
        try:
            with transaction.atomic():
                updated_hints = []
                
                for hint_data in hints_data:
                    # Validate required fields
                    hint_type = hint_data.get('type')
                    if not hint_type:
                        return Response({
                            'error': 'Each hint must have a type field'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    if hint_type not in valid_hint_types:
                        return Response({
                            'error': f'Invalid hint type: {hint_type}. Must be one of: {", ".join(valid_hint_types)}'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
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
                
                return Response({
                    'problem_slug': problem.slug,
                    'hints': updated_hints
                })
                
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to update hints for problem {slug}: {str(e)}")
            return Response({
                'error': 'Failed to update hints. Please check the hint configurations.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)