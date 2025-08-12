"""Views for managing and accessing problem hints."""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..services.hint_service import HintService, AdminHintService
from ..models import Course, CourseEnrollment
from purplex.users_app.permissions import IsAuthenticated, IsAdmin

logger = logging.getLogger(__name__)


class ProblemHintAvailabilityView(APIView):
    """Get hint availability for a problem based on user's attempts."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        user = request.user
        
        # Get optional course context parameters
        query_params = getattr(request, 'query_params', request.GET)
        course_id = query_params.get('course_id')
        problem_set_slug = query_params.get('problem_set_slug')
        
        # Validate course enrollment if provided
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
        
        # Use service layer for hint availability
        availability_data = HintService.get_hint_availability(
            user=user,
            problem_slug=slug,
            course_id=course_id,
            problem_set_slug=problem_set_slug
        )
        
        # Transform data to match expected response format
        available_hints = []
        for hint in availability_data.get('hints', []):
            # Get display title for hint type
            display_titles = {
                'variable_fade': 'Variable Fade',
                'subgoal_hints': 'Subgoal Highlighting',
                'subgoal_highlight': 'Subgoal Highlighting',
                'suggested_trace': 'Suggested Trace',
                'trace': 'Suggested Trace'
            }
            title = display_titles.get(hint['type'], hint['type'])
            
            available_hints.append({
                'type': hint['type'],
                'title': title,
                'description': f'Get help with {title.lower()}',
                'unlocked': hint['available'],
                'available': hint['available'],
                'attempts_needed': hint['attempts_needed']
            })
        
        return Response({
            'available_hints': available_hints,
            'hints_used': [],  # TODO: Track which hints the user has used
            'current_attempts': availability_data.get('user_attempts', 0)
        })


class ProblemHintDetailView(APIView):
    """Get specific hint content for a problem."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug, hint_type):
        user = request.user
        
        # Get optional course context parameters
        query_params = getattr(request, 'query_params', request.GET)
        course_id = query_params.get('course_id')
        problem_set_slug = query_params.get('problem_set_slug')
        
        # Use service layer to get hint content
        hint_data = HintService.get_hint_content(
            user=user,
            problem_slug=slug,
            hint_type=hint_type,
            course_id=course_id,
            problem_set_slug=problem_set_slug
        )
        
        # Handle different error types from service
        if 'error' in hint_data:
            error_type = hint_data['error']
            message = hint_data.get('message', 'An error occurred')
            
            if error_type == 'not_found':
                return Response({'error': message}, status=status.HTTP_404_NOT_FOUND)
            elif error_type == 'invalid_type':
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
            elif error_type == 'invalid_context':
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
            elif error_type == 'forbidden':
                return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
            elif error_type == 'disabled':
                return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
            elif error_type == 'insufficient_attempts':
                return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Return successful response
        return Response(hint_data)


class AdminProblemHintView(APIView):
    """Admin endpoint to manage hints for a problem."""
    permission_classes = [IsAdmin]
    
    def get(self, request, slug):
        """Get all hint configurations for a problem"""
        try:
            # Use service layer to get hint configurations
            hint_configs = AdminHintService.get_problem_hints_config(slug)
            return Response(hint_configs)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, slug):
        """Bulk update all hint types for a problem"""
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
        
        try:
            # Use service layer to bulk update hints
            result = AdminHintService.bulk_update_hints(slug, hints_data)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RuntimeError as e:
            logger.error(f"Failed to update hints for problem {slug}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )