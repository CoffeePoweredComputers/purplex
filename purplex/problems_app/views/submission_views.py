"""Views for handling code submissions and testing."""

import json
import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from ..models import Problem, ProblemSet, Course, CourseEnrollment, UserProgress
from ..services import CodeExecutionService, AITestGenerationService
from purplex.users_app.permissions import IsAuthenticated
from purplex.submissions_app.models import PromptSubmission, SegmentationResult
from celery.result import AsyncResult
from ..tasks.pipeline import execute_eipl_pipeline
import uuid

logger = logging.getLogger(__name__)


def create_error_response(error_message: str, http_status: int, **kwargs):
    """Create a consistent error response structure for EiPL submissions.
    
    Args:
        error_message: The error message to display
        http_status: HTTP status code
        **kwargs: Additional fields to include in the response
        
    Returns:
        Response object with consistent structure
    """
    response_data = {
        'error': error_message,
        'submission_id': kwargs.get('submission_id', None),
        'score': kwargs.get('score', 0),
        'variations': kwargs.get('variations', []),
        'results': kwargs.get('results', []),
        'passing_variations': kwargs.get('passing_variations', 0),
        'total_variations': kwargs.get('total_variations', 0)
    }
    
    # Add any additional fields passed in kwargs
    for key, value in kwargs.items():
        if key not in response_data:
            response_data[key] = value
            
    return Response(response_data, status=http_status)


@method_decorator(ratelimit(key='user', rate='30/m', method='POST'), name='post')
class TestSolutionView(APIView):
    """Test a solution without saving submission."""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='20/m', method='POST'))  # Higher limit for testing
    def post(self, request):
        # Check if rate limited
        if getattr(request, 'limited', False):
            return Response({
                'error': 'Rate limit exceeded. Please wait a moment before testing again.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        problem_slug = request.data.get('problem_slug')
        user_code = request.data.get('user_code')
        
        if not problem_slug or not user_code:
            return Response({
                'error': 'problem_slug and user_code are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user_code length
        if len(user_code) > 50000:  # 50KB limit for code
            return Response({
                'error': 'user_code must not exceed 50000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get test cases (only visible ones for students)
        test_cases = problem.test_cases.filter(is_hidden=False)
        test_data = [
            {
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in test_cases
        ]
        
        # Run tests with error handling
        try:
            code_service = CodeExecutionService()
            result = code_service.test_solution(user_code, problem.function_name, test_data)
            return Response(result)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'Code execution failed. Please check your solution and try again.',
                'testsPassed': 0,
                'totalTests': len(test_data),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitSolutionView(APIView):
    """Submit a solution and track progress."""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='10/m', method='POST'))
    def post(self, request):
        # Check if rate limited
        if getattr(request, 'limited', False):
            return Response({
                'error': 'Rate limit exceeded. Please wait a moment before submitting again.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        user_code = request.data.get('user_code')
        prompt = request.data.get('prompt', '')  # For EiPL problems
        time_spent = request.data.get('time_spent')  # Optional, in seconds
        course_id = request.data.get('course_id')  # Optional, for course context
        
        if not problem_slug or not user_code or not problem_set_slug:
            return Response({
                'error': 'problem_slug, problem_set_slug, and user_code are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user_code length
        if len(user_code) > 50000:  # 50KB limit for code
            return Response({
                'error': 'user_code must not exceed 50000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate optional prompt for EiPL problems
        if prompt and len(prompt) > 2000:
            return Response({
                'error': 'prompt must not exceed 2000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
            problem_set = ProblemSet.objects.get(slug=problem_set_slug)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ProblemSet.DoesNotExist:
            return Response({
                'error': 'Problem set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify problem belongs to the problem set
        if not problem.problem_sets.filter(id=problem_set.id).exists():
            return Response({
                'error': 'Problem does not belong to the specified problem set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate course context if provided
        course = None
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                
                # Verify user is enrolled in the course
                if not CourseEnrollment.objects.filter(
                    user=request.user,
                    course=course,
                    is_active=True
                ).exists():
                    return Response({
                        'error': 'You are not enrolled in this course'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Verify problem set belongs to the course
                if not course.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem set does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all test cases (including hidden ones for grading)
        all_test_cases = list(problem.test_cases.all())
        test_data = [
            {
                'id': tc.id,
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in all_test_cases
        ]
        
        # Run tests with error handling
        try:
            code_service = CodeExecutionService()
            result = code_service.test_solution(user_code, problem.function_name, test_data)
            
            # Calculate score based on all tests
            passed_tests = result.get('passed', 0)
            total_tests = result.get('total', 0)
            score = int((passed_tests / total_tests * 100) if total_tests > 0 else 0)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'Code execution failed. Please check your solution and try again.',
                'submission_id': None,
                'score': 0,
                'testsPassed': 0,
                'totalTests': len(test_data),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract passed test IDs
        passed_test_ids = []
        if 'results' in result:
            for i, test_result in enumerate(result['results']):
                if test_result.get('pass', False) and i < len(test_data):
                    passed_test_ids.append(test_data[i]['id'])
        
        # Convert time_spent to timedelta if provided
        time_spent_delta = None
        if time_spent:
            time_spent_delta = timedelta(seconds=int(time_spent))
        
        # Create submission record
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            score=score,
            prompt=prompt or user_code,  # Store code if no prompt provided
            test_results=result,
            course=course,  # Include course context
            time_spent=time_spent_delta
        )
        
        # Progress is automatically updated via the PromptSubmission model's save method
        # Get the updated progress for response
        progress = UserProgress.objects.get(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            course=course
        )
        
        # Return only visible test results to student
        visible_results = []
        if 'results' in result:
            visible_test_cases = list(problem.test_cases.filter(is_hidden=False))
            for i, tc in enumerate(all_test_cases):
                if not tc.is_hidden and i < len(result['results']):
                    visible_results.append(result['results'][i])
        
        return Response({
            'submission_id': submission.id,
            'score': score,
            'testsPassed': passed_tests,
            'totalTests': total_tests,
            'results': visible_results,  # Only visible test results
            'progress': {
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
            }
        })


@method_decorator(ratelimit(key='user', rate='10/m', method='POST'), name='post')
class EiPLSubmissionView(APIView):
    """Unified endpoint for EiPL (Explain in Plain Language) submissions.
    Generates AI variations, tests them, and saves submission with progress tracking."""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST'))
    def post(self, request):
        # Check if rate limited
        if getattr(request, 'limited', False):
            return Response({
                'error': 'Rate limit exceeded. Please wait a moment before submitting again.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        user_prompt = request.data.get('user_prompt', '')
        course_id = request.data.get('course_id')
        
        # Input validation
        if not problem_slug:
            return Response({
                'error': 'problem_slug is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_prompt or not user_prompt.strip():
            return Response({
                'error': 'user_prompt is required and cannot be empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate prompt length (max 5000 characters)
        if len(user_prompt) > 5000:
            return Response({
                'error': 'user_prompt exceeds maximum length of 5000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Sanitize user prompt
        user_prompt = user_prompt.strip()  # Optional, for course context
        
        if not problem_slug or not user_prompt:
            return Response({
                'error': 'problem_slug and user_prompt are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user_prompt length and content
        user_prompt = user_prompt.strip()
        if len(user_prompt) < 10:
            return Response({
                'error': 'user_prompt must be at least 10 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(user_prompt) > 2000:
            return Response({
                'error': 'user_prompt must not exceed 2000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Basic content validation - prevent potential injection attempts
        if any(char in user_prompt for char in ['<script', '<?php', '<%', '<jsp']):
            return Response({
                'error': 'Invalid characters detected in prompt'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Handle optional problem set
        problem_set = None
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                # Verify problem belongs to the problem set
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem does not belong to the specified problem set'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ProblemSet.DoesNotExist:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate course context if provided
        course = None
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                
                # Verify user is enrolled in the course
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
        
        # Log submission attempt
        logger.info(f"EiPL submission attempt for problem {problem_slug} by user {request.user.username}")
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Store submission context in Redis for later retrieval
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)
        
        submission_context = {
            'user_id': request.user.id,
            'username': request.user.username,
            'problem_id': problem.id,
            'problem_slug': problem.slug,
            'problem_set_id': problem_set.id if problem_set else None,
            'problem_set_slug': problem_set.slug if problem_set else None,
            'course_id': course.id if course else None,
            'course_name': course.name if course else None,
            'user_prompt': user_prompt,
            'request_id': request_id,
            'submitted_at': timezone.now().isoformat()
        }
        
        # Store context with 2 hour TTL
        redis_client.setex(
            f"eipl:context:{request_id}",
            7200,
            json.dumps(submission_context)
        )
        
        logger.debug(f"Stored submission context for request {request_id}")
        
        # Start the clean EiPL pipeline task
        try:
            logger.debug(f"Starting EiPL pipeline for problem {problem_slug} with request ID {request_id}")
            # Launch the single orchestrator task
            # Use request_id as the task_id so SSE can track it
            pipeline_task = execute_eipl_pipeline.apply_async(
                args=[
                    problem.id,
                    user_prompt,
                    request.user.id,
                    problem_set.id if problem_set else None,
                    course.id if course else None
                ],
                task_id=request_id  # Use request_id as the Celery task ID
            )
            # Store request_id in session for SSE authentication
            if not request.session.get('user_tasks'):
                request.session['user_tasks'] = []
            request.session['user_tasks'].append(request_id)
            request.session.save()
            # Return SSE streaming URL for real-time updates
            return Response({
                'request_id': request_id,
                'task_id': pipeline_task.id,  # This should be same as request_id
                'status': 'processing',
                'stream_url': f'/api/tasks/{request_id}/stream/',
                'message': 'Your submission is being processed. Connect to the stream URL for real-time updates.'
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to start AI generation task for problem {problem_slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start AI task. Please try again.',
                'request_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
