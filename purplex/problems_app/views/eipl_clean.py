"""
Clean EiPL submission endpoint.

This replaces the overengineered submission view with a simple,
maintainable implementation.
"""

import uuid
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from ..tasks.pipeline_clean import execute_eipl_pipeline
from ..models import Problem, ProblemSet, Course, CourseEnrollment

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key='user', rate='10/m', method='POST'), name='post')
class CleanEiPLSubmissionView(APIView):
    """
    Clean, simple endpoint for EiPL submissions.
    
    This endpoint:
    1. Validates the request
    2. Launches the Celery pipeline
    3. Returns a task ID for tracking
    
    No Redis manipulation, no complex state management.
    """
    
    def post(self, request):
        """
        Process an EiPL submission.
        
        Expected payload:
        {
            "problem_slug": "two-sum",
            "user_prompt": "I would iterate through the array...",
            "problem_set_slug": "arrays-101",  # optional
            "course_id": "CS101"  # optional
        }
        """
        # Extract and validate input
        problem_slug = request.data.get('problem_slug')
        user_prompt = request.data.get('user_prompt', '').strip()
        problem_set_slug = request.data.get('problem_set_slug')
        course_id = request.data.get('course_id')
        
        # Basic validation
        if not problem_slug or not user_prompt:
            return Response({
                'error': 'problem_slug and user_prompt are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(user_prompt) < 10:
            return Response({
                'error': 'user_prompt must be at least 10 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(user_prompt) > 2000:
            return Response({
                'error': 'user_prompt must not exceed 2000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get problem
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Optional: Get problem set
        problem_set = None
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                # Verify problem belongs to set
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem does not belong to this problem set'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ProblemSet.DoesNotExist:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Optional: Validate course enrollment
        course = None
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True)
                # Check enrollment
                if not CourseEnrollment.objects.filter(
                    user=request.user,
                    course=course,
                    is_active=True
                ).exists():
                    return Response({
                        'error': 'You are not enrolled in this course'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Build and execute the pipeline
        result = self._create_pipeline(
            problem_id=problem.id,
            user_prompt=user_prompt,
            user_id=request.user.id,
            problem_set_id=problem_set.id if problem_set else None,
            course_id=course.id if course else None
        )
        
        logger.info(f"Started EiPL pipeline {result.id} for user {request.user.username}")
        
        # Return format expected by frontend (request_id, not task_id)
        return Response({
            'request_id': result.id,  # Frontend expects request_id
            'generation_task_id': result.id,  # For compatibility
            'status': 'processing',
            'stream_url': f'/api/tasks/{result.id}/stream/',
            'message': 'Your submission is being processed'
        }, status=status.HTTP_202_ACCEPTED)
    
    def _create_pipeline(self, problem_id, user_prompt, user_id, 
                        problem_set_id=None, course_id=None):
        """
        Create and execute the EiPL processing task.
        
        This uses a single orchestrator task that manages the entire pipeline
        and publishes consistent progress events to one Redis channel.
        """
        # Execute the single orchestrator task
        result = execute_eipl_pipeline.apply_async(
            args=[problem_id, user_prompt, user_id, problem_set_id, course_id]
        )
        return result


class TaskStatusView(APIView):
    """
    Simple endpoint to check task status.
    
    No Redis manipulation, just uses Celery's built-in result backend.
    """
    
    def get(self, request, task_id):
        """Get the status of a task."""
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready()
        }
        
        if result.ready():
            if result.successful():
                response_data['result'] = result.result
            else:
                response_data['error'] = str(result.info)
        
        return Response(response_data)