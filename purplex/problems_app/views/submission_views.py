"""Views for handling code submissions and testing."""

import json
import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
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
from celery import group, chain, chord
from ..tasks import (
    generate_eipl_variations,
    segment_prompt,
    execute_code,
    test_single_variation,
    update_progress
)
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
    
    def post(self, request):
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
                'passed': 0,
                'total': len(test_data),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(ratelimit(key='user', rate='20/m', method='POST'), name='post')
class SubmitSolutionView(APIView):
    """Submit a solution and track progress."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
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
                'passed': 0,
                'total': len(test_data),
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
            'passed': passed_tests,
            'total': total_tests,
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
    
    def post(self, request):
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        user_prompt = request.data.get('user_prompt', '')
        course_id = request.data.get('course_id')  # Optional, for course context
        
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
        
        # Start AI generation task
        try:
            logger.debug(f"Starting AI generation for problem {problem_slug} with request ID {request_id}")
            
            # Launch the AI generation task
            generation_task = generate_eipl_variations.apply_async(
                args=[problem.id, user_prompt],
                task_id=f"{request_id}-generation"
            )
            
            # Start segmentation in parallel if enabled
            segmentation_task = None
            if problem.segmentation_enabled:
                segmentation_task = segment_prompt.apply_async(
                    args=[problem.id, user_prompt],
                    task_id=f"{request_id}-segmentation"
                )
            
            # Always return immediately with task IDs for async polling
            # This prevents blocking and deadlocks
            return Response({
                'request_id': request_id,
                'generation_task_id': generation_task.id,
                'segmentation_task_id': segmentation_task.id if segmentation_task else None,
                'status': 'processing',
                'status_url': f'/api/tasks/{request_id}/status/',
                'message': 'Your submission is being processed. Please poll the status URL for results.'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Failed to start AI generation task for problem {problem_slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start AI task. Please try again.',
                'request_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskStatusView(APIView):
    """Check Celery task status and retrieve results."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, task_id):
        """Get the status and result of a Celery task.
        
        Args:
            request: HTTP request
            task_id: The Celery task ID
            
        Returns:
            JSON response with task status and result
        """
        from django.core.cache import cache
        
        # Check cache first for completed results
        cached_result = cache.get(f"task:result:{task_id}")
        if cached_result:
            return Response(cached_result)
        
        # Get task result from Celery
        result = AsyncResult(task_id)
        
        if result.ready():
            # Task completed
            if result.successful():
                data = {
                    'status': 'completed',
                    'result': result.result
                }
                # Cache successful results for 1 hour
                cache.set(f"task:result:{task_id}", data, timeout=3600)
                return Response(data)
            else:
                # Task failed
                return Response({
                    'status': 'failed',
                    'error': str(result.info) if result.info else 'Unknown error'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        elif result.state == 'PENDING':
            # Task hasn't started yet
            return Response({
                'status': 'pending',
                'message': 'Task is queued and waiting to start'
            })
        
        elif result.state == 'RETRY':
            # Task is being retried
            return Response({
                'status': 'retrying',
                'message': 'Task failed and is being retried',
                'retry_count': result.info.get('retries', 0) if isinstance(result.info, dict) else 0
            })
        
        else:
            # Task is running or in other state
            progress_info = {}
            if result.info and isinstance(result.info, dict):
                progress_info = {
                    'current': result.info.get('current', 0),
                    'total': result.info.get('total', 100),
                    'description': result.info.get('description', '')
                }
            
            return Response({
                'status': result.state.lower(),
                'progress': progress_info
            })


class EiPLSubmissionStatusView(APIView):
    """Check EiPL submission status and retrieve results from Redis."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, request_id):
        """Get the status and results of an EiPL submission.
        
        Args:
            request_id: The unique request ID returned from submission
            
        Returns:
            Current status and results if available
        """
        import redis
        import json
        
        # Get Redis client
        redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)
        
        # Check for completed results first
        result_key = f"eipl:result:{request_id}"
        result_data = redis_client.get(result_key)
        
        if result_data:
            # Results are ready
            result = json.loads(result_data)
            
            # If completed successfully, create submission record
            if result.get('status') == 'completed' and result.get('success'):
                # TODO: Create submission record with results
                pass
            
            return Response({
                'status': result.get('status', 'completed'),
                'success': result.get('success', False),
                'variations': result.get('variations', []),
                'test_results': result.get('test_results', []),
                'problem_id': result.get('problem_id'),
                'total_variations': result.get('total_variations', 0),
                'error': result.get('error')
            })
        
        # Check generation task status
        generation_task_id = f"{request_id}-generation"
        result = AsyncResult(generation_task_id)
        
        if result.state == 'PENDING':
            return Response({
                'status': 'pending',
                'message': 'Task is queued and waiting to start'
            })
        elif result.state == 'STARTED':
            return Response({
                'status': 'processing',
                'message': 'Generating code variations...'
            })
        elif result.state == 'SUCCESS':
            # Generation completed but tests not yet done
            return Response({
                'status': 'testing',
                'message': 'Testing code variations...'
            })
        elif result.state == 'FAILURE':
            return Response({
                'status': 'failed',
                'error': str(result.info) if result.info else 'Task failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'status': result.state.lower(),
                'message': 'Processing...'
            })


class AsyncEiPLSubmissionView(APIView):
    """Async version of EiPL submission that returns task IDs immediately."""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='10/m', method='POST'))
    def post(self, request):
        """Submit EiPL problem solution asynchronously.
        
        Returns task IDs immediately for the client to poll status.
        """
        problem_slug = request.data.get('problem_slug')
        user_prompt = request.data.get('user_prompt', '')
        course_id = request.data.get('course_id')
        
        # Validation
        if not problem_slug:
            return Response({
                'error': 'problem_slug is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get problem
        problem = get_object_or_404(Problem, slug=problem_slug)
        
        # Check course enrollment if course_id provided
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
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
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Get test data
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
        
        # Create task chain:
        # 1. Generate variations
        # 2. Test all variations in parallel
        # 3. Update user progress
        from celery import chain, group
        
        # Build the workflow
        workflow = chain(
            # Generate AI variations
            generate_eipl_variations.si(problem.id, user_prompt),
            
            # Test variations (this task will create a group internally)
            # We pass the test data so it doesn't need to query again
            group(
                test_single_variation.s(var, problem.function_name, problem.id)
                for var in []  # This will be replaced with actual variations
            ),
            
            # Update progress with results
            update_progress.s(request.user.id, problem.id, {
                'course_id': course_id,
                'user_prompt': user_prompt
            })
        )
        
        # Execute workflow
        result = workflow.apply_async(task_id=request_id)
        
        # Start segmentation if enabled
        segmentation_task_id = None
        if problem.segmentation_enabled:
            seg_task = segment_prompt.apply_async(
                args=[problem.id, user_prompt],
                task_id=f"{request_id}-segmentation"
            )
            segmentation_task_id = seg_task.id
        
        # Return task IDs for polling
        return Response({
            'request_id': request_id,
            'workflow_task_id': result.id,
            'segmentation_task_id': segmentation_task_id,
            'status': 'processing',
            'status_url': f'/api/tasks/{request_id}/status/',
            'message': 'Your submission is being processed. You can check the status using the provided URL.'
        }, status=status.HTTP_202_ACCEPTED)