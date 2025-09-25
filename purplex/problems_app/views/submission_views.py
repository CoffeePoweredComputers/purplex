"""Views for handling code submissions and testing."""

import json
import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from ..services.docker_execution_service import DockerExecutionService as CodeExecutionService
from ..services.ai_generation_service import AITestGenerationService
from ..services.submission_validation_service import SubmissionValidationService
from purplex.submissions.services import SubmissionService  # Use new submission service
from ..services.course_service import CourseService
from ..services.student_service import StudentService
from ..services.problem_service import ProblemService
from ..services.progress_service import ProgressService
from ..repositories import TestCaseRepository
from purplex.users_app.permissions import IsAuthenticated
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
        # Use validation service to validate request data
        is_valid, error_message, validated_data = SubmissionValidationService.validate_code_submission(request.data)
        if not is_valid:
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        problem = validated_data['problem']
        user_code = validated_data['user_code']
        
        # Get test cases (only visible ones for students)
        test_cases = StudentService.get_visible_test_cases(problem)
        test_data = [
            {
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in test_cases
        ]
        
        # Run tests with error handling and proper resource cleanup
        try:
            with CodeExecutionService() as code_service:
                # Set user context for rate limiting
                code_service.set_user_context(str(request.user.id) if request.user.is_authenticated else None)
                result = code_service.test_solution(user_code, problem.function_name, test_data)
                return Response(result)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem.slug}: {str(e)}")
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
        # Validate required fields manually for SubmitSolutionView
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        
        if not problem_slug or not problem_set_slug:
            return Response({
                'error': 'problem_slug and problem_set_slug are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use validation service to validate code submission data
        is_valid, error_message, validated_data = SubmissionValidationService.validate_code_submission(request.data)
        if not is_valid:
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        problem = validated_data['problem']
        user_code = validated_data['user_code']
        course = validated_data.get('course')
        
        # Get problem set using problem service
        problem_set = ProblemService.get_problem_set_by_slug(problem_set_slug)
        if not problem_set:
            return Response({
                'error': 'Problem set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Extract additional optional fields
        prompt = request.data.get('prompt', '')  # For EiPL problems
        time_spent = request.data.get('time_spent')  # Optional, in seconds
        course_id = request.data.get('course_id')  # Optional course context
        
        # Validate optional prompt for EiPL problems
        if prompt and len(prompt) > 2000:
            return Response({
                'error': 'prompt must not exceed 2000 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify problem belongs to the problem set
        if not problem_set.problems.filter(id=problem.id).exists():
            return Response({
                'error': 'Problem does not belong to the specified problem set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate course context if provided
        course = None
        if course_id:
            # Use CourseService to validate enrollment and get course
            validation_result = CourseService.validate_course_enrollment(request.user, course_id)
            if not validation_result['success']:
                return Response({
                    'error': validation_result['error']
                }, status=validation_result['status_code'])
            
            course = validation_result['course']
            
            # Verify problem set belongs to the course
            # Using repository pattern to check relationship
            from ..repositories import CourseRepository
            if problem_set.id not in CourseRepository.get_course_problem_set_ids(course):
                return Response({
                    'error': 'Problem set does not belong to this course'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all test cases (including hidden ones for grading)
        all_test_cases = TestCaseRepository.get_problem_test_cases(problem, include_hidden=True)
        test_data = [
            {
                'id': tc.id,
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in all_test_cases
        ]
        
        # Run tests with error handling and proper resource cleanup
        try:
            with CodeExecutionService() as code_service:
                # Set user context for rate limiting
                code_service.set_user_context(str(request.user.id) if request.user.is_authenticated else None)
                result = code_service.test_solution(user_code, problem.function_name, test_data)

                # Calculate score based on all tests
                passed_tests = result.get('passed', 0)
                total_tests = result.get('total', 0)
                score = int((passed_tests / total_tests * 100) if total_tests > 0 else 0)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem.slug}: {str(e)}")
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

        # Create submission record using new service
        submission = SubmissionService.create_submission(
            user=request.user,
            problem=problem,
            raw_input=prompt or user_code,  # Store code if no prompt provided
            submission_type='direct_code',
            problem_set=problem_set,
            course=course,
            time_spent=time_spent_delta
        )

        # Record test results
        test_execution_data = []
        if 'results' in result:
            for i, (test_result, test_case) in enumerate(zip(result['results'], all_test_cases)):
                test_execution_data.append({
                    'test_case_id': test_case.id,
                    'passed': test_result.get('pass', False),
                    'inputs': test_case.inputs,
                    'expected': test_case.expected_output,
                    'actual': test_result.get('output', ''),
                    'error_type': 'none' if test_result.get('pass') else 'wrong_output',
                    'error_message': test_result.get('error', '')
                })

        SubmissionService.record_test_results(
            submission=submission,
            test_results=test_execution_data,
            processed_code=user_code,
            execution_time_ms=None,
            memory_used_mb=None
        )

        # Get the updated progress for response
        progress = ProgressService.get_user_progress(
            user_id=request.user.id,
            problem_id=problem.id,
            course_id=course.id if course else None
        )
        
        # Return only visible test results to student
        visible_results = []
        if 'results' in result:
            visible_test_cases = StudentService.get_visible_test_cases(problem)
            for i, tc in enumerate(all_test_cases):
                if not tc.is_hidden and i < len(result['results']):
                    visible_results.append(result['results'][i])
        
        # Import GradingService to calculate grade
        from purplex.submissions.grading_service import GradingService

        return Response({
            'submission_id': str(submission.submission_id),  # Use UUID
            'score': submission.score,
            'testsPassed': result.get('testsPassed', 0),
            'totalTests': result.get('totalTests', 0),
            'results': visible_results,  # Only visible test results
            'grade': GradingService.calculate_grade(submission),  # New grade field
            'progress': {
                'status': progress.status if progress else 'not_started',
                'best_score': progress.best_score if progress else 0,
                'attempts': progress.attempts if progress else 0,
                'is_completed': progress.is_completed if progress else False,
                'grade': getattr(progress, 'grade', None),  # Include grade in progress too
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
        
        # Use validation service to validate request data
        is_valid, error_message, validated_data = SubmissionValidationService.validate_eipl_submission(request.data)
        if not is_valid:
            return Response({
                'error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        problem = validated_data['problem']
        problem_set = validated_data.get('problem_set')
        course = validated_data.get('course')
        user_prompt = validated_data['user_prompt']
        
        # Additional validation for problem set membership
        if problem_set and not problem_set.problems.filter(id=problem.id).exists():
            return Response({
                'error': 'Problem does not belong to the specified problem set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Additional validation for course enrollment using service
        if course:
            enrollment_result = CourseService.validate_course_enrollment(
                request.user, 
                course.course_id
            )
            if not enrollment_result['success']:
                return Response({
                    'error': enrollment_result['error']
                }, status=enrollment_result['status_code'])
        
        # Log submission attempt
        logger.info(f"EiPL submission attempt for problem {problem.slug} by user {request.user.username}")
        
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
            logger.debug(f"Starting EiPL pipeline for problem {problem.slug} with request ID {request_id}")
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
            logger.error(f"Failed to start AI generation task for problem {problem.slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start AI task. Please try again.',
                'request_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
