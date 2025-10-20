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

from ..services.ai_generation_service import AITestGenerationService
from ..services.submission_validation_service import SubmissionValidationService
from purplex.submissions.services import SubmissionService  # Use new submission service
from ..services.course_service import CourseService
from ..services.student_service import StudentService
from ..services.problem_service import ProblemService
from ..services.progress_service import ProgressService
from ..repositories import TestCaseRepository, ProblemRepository
from purplex.users_app.permissions import IsAuthenticated
from celery.result import AsyncResult
from ..tasks.pipeline import execute_eipl_pipeline, execute_code_test
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


@method_decorator(ratelimit(key='user', rate='50/m', method='POST'), name='post')
class TestSolutionView(APIView):
    """Test a solution without saving submission. Uses SSE for real-time results."""
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='50/m', method='POST'))  # Lenient for beta test
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
        test_case_ids = [tc.id for tc in test_cases]

        # Queue task for async execution with SSE
        try:
            # Generate task ID for tracking
            task_id = str(uuid.uuid4())

            # Queue task (no submission context for test-only)
            task = execute_code_test.apply_async(
                args=[user_code, problem.id, test_case_ids, False, None],  # None = no submission
                task_id=task_id,
                expires=30
            )

            # Store task_id in session for SSE authentication
            if not request.session.get('user_tasks'):
                request.session['user_tasks'] = []
            request.session['user_tasks'].append(task_id)
            request.session.save()

            # Return SSE streaming URL for real-time updates
            return Response({
                'task_id': task_id,
                'status': 'processing',
                'stream_url': f'/api/tasks/{task_id}/stream/',
                'message': 'Testing your code. Connect to stream URL for results.'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Failed to queue code test for problem {problem.slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start code test. Please try again.',
                'task_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitSolutionView(APIView):
    """Submit a solution and track progress."""
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='50/m', method='POST'))  # Lenient for beta test
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
        activated_hints = request.data.get('activated_hints', [])  # Optional hint tracking
        
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
        test_case_ids = [tc.id for tc in all_test_cases]

        # Log submission attempt
        logger.info(f"Code submission attempt for problem {problem.slug} by user {request.user.username}")

        # Generate task ID for tracking
        task_id = str(uuid.uuid4())

        # Store submission context in cache for task to retrieve (like EiPL pattern)
        from django.core.cache import cache

        submission_context = {
            'user_id': request.user.id,
            'username': request.user.username,
            'problem_id': problem.id,
            'problem_slug': problem.slug,
            'problem_set_id': problem_set.id,
            'problem_set_slug': problem_set.slug,
            'course_id': course.id if course else None,
            'course_name': course.name if course else None,
            'user_code': user_code,
            'prompt': prompt,
            'time_spent': time_spent,
            'activated_hints': activated_hints,
            'task_id': task_id,
            'submitted_at': timezone.now().isoformat()
        }

        # Store context with 1 hour TTL
        cache.set(
            f"submission:context:{task_id}",
            submission_context,
            timeout=3600
        )

        logger.debug(f"Stored submission context for task {task_id}")

        # Queue task with submission context
        try:
            task = execute_code_test.apply_async(
                args=[user_code, problem.id, test_case_ids, True, submission_context],  # include_hidden=True, submission_context
                task_id=task_id,
                expires=30
            )

            # Store task_id in session for SSE authentication
            if not request.session.get('user_tasks'):
                request.session['user_tasks'] = []
            request.session['user_tasks'].append(task_id)
            request.session.save()

            # Return SSE streaming URL for real-time updates
            return Response({
                'task_id': task_id,
                'status': 'processing',
                'stream_url': f'/api/tasks/{task_id}/stream/',
                'message': 'Submitting your code. Connect to stream URL for results.'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Failed to queue submission for problem {problem.slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start submission. Please try again.',
                'task_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(ratelimit(key='user', rate='50/m', method='POST'), name='post')
class EiPLSubmissionView(APIView):
    """Unified endpoint for EiPL (Explain in Plain Language) submissions.
    Generates AI variations, tests them, and saves submission with progress tracking."""
    permission_classes = [IsAuthenticated]

    # Increased rate limit for beta test - users may submit multiple times while testing
    @method_decorator(ratelimit(key='user', rate='50/m', method='POST'))
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
        activated_hints = request.data.get('activated_hints', [])  # Extract hint tracking data
        
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
        
        # Store submission context in cache for later retrieval
        from django.core.cache import cache
        
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
            'activated_hints': activated_hints,  # Store hints for pipeline
            'request_id': request_id,
            'submitted_at': timezone.now().isoformat()
        }
        
        # Store context with 2 hour TTL
        cache.set(
            f"eipl:context:{request_id}",
            submission_context,  # Django cache handles serialization
            timeout=7200
        )
        
        logger.debug(f"Stored submission context for request {request_id}")
        
        # Start the clean EiPL pipeline task
        try:
            logger.info(f"🚀 Starting EiPL pipeline for problem {problem.slug} with request ID {request_id}")
            logger.info(f"📝 Task args: problem_id={problem.id}, user_id={request.user.id}, problem_set_id={problem_set.id if problem_set else None}, course_id={course.id if course else None}")

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

            logger.info(f"✅ Task queued successfully: task_id={pipeline_task.id}, state={pipeline_task.state}")

            # Store request_id in session for SSE authentication
            if not request.session.get('user_tasks'):
                request.session['user_tasks'] = []
            request.session['user_tasks'].append(request_id)
            request.session.save()

            logger.info(f"💾 Stored request_id {request_id} in session for user {request.user.username}")
            logger.info(f"📋 Session user_tasks: {request.session.get('user_tasks', [])}")

            # Return SSE streaming URL for real-time updates
            return Response({
                'request_id': request_id,
                'task_id': pipeline_task.id,  # This should be same as request_id
                'status': 'processing',
                'stream_url': f'/api/tasks/{request_id}/stream/',
                'message': 'Your submission is being processed. Connect to the stream URL for real-time updates.'
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"❌ Failed to start AI generation task for problem {problem.slug}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start AI task. Please try again.',
                'request_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmissionHistoryView(APIView):
    """Get submission history for a specific problem and user."""
    permission_classes = [IsAuthenticated]

    def get(self, request, problem_slug):
        """
        Fetch all submission attempts for the current user and specified problem.
        Returns submissions with metadata for the attempt selector dropdown.
        """
        # Validate problem exists
        try:
            problem = ProblemRepository.get_problem_by_slug(problem_slug)
            if not problem:
                return Response({
                    'error': 'Problem not found'
                }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'Failed to fetch problem'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get filters
        problem_set_slug = request.query_params.get('problem_set_slug')
        course_id = request.query_params.get('course_id')
        limit = request.query_params.get('limit', 50)  # Default to last 50 attempts

        try:
            limit = int(limit)
            limit = min(limit, 100)  # Cap at 100 for performance
        except (ValueError, TypeError):
            limit = 50

        # Build query filters
        filters = {
            'user': request.user,
            'problem': problem
        }

        # Add problem_set filter if provided - important to prevent cross-set leakage
        if problem_set_slug:
            problem_set = ProblemService.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Verify problem belongs to this problem set
            if not problem_set.problems.filter(id=problem.id).exists():
                return Response({
                    'error': 'Problem does not belong to the specified problem set'
                }, status=status.HTTP_400_BAD_REQUEST)

            filters['problem_set'] = problem_set

        # Add course filter if provided
        if course_id:
            # Validate course enrollment
            validation_result = CourseService.validate_course_enrollment(request.user, course_id)
            if validation_result['success']:
                filters['course'] = validation_result['course']
                # Also verify problem set belongs to course if both are provided
                if problem_set_slug:
                    from ..repositories import CourseRepository
                    if problem_set.id not in CourseRepository.get_course_problem_set_ids(validation_result['course']):
                        return Response({
                            'error': 'Problem set does not belong to this course'
                        }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch submissions from the new Submission model
        from purplex.submissions.models import Submission, CodeVariation, TestExecution, SegmentationAnalysis

        submissions = Submission.objects.filter(
            **filters
        ).select_related(
            'problem', 'problem_set', 'course', 'segmentation'
        ).prefetch_related(
            'code_variations',
            'test_executions'
        ).order_by('-submitted_at')[:limit]

        # Find the best attempt
        best_score = 0
        best_attempt_id = None

        # Format submission data for frontend
        submission_history = []
        for index, submission in enumerate(submissions):
            # Get test execution summary
            test_executions = submission.test_executions.all()
            total_tests = test_executions.count()
            passed_tests = test_executions.filter(passed=True).count()

            # Get code variations
            variations = submission.code_variations.all()

            # Track best score
            if submission.score > best_score:
                best_score = submission.score
                best_attempt_id = str(submission.submission_id)

            # Get segmentation data only if segmentation is enabled for this problem
            segmentation_data = None
            if (hasattr(submission, 'segmentation') and submission.segmentation and
                submission.problem.segmentation_enabled):
                seg = submission.segmentation
                segmentation_data = {
                    'segment_count': seg.segment_count,
                    'comprehension_level': seg.comprehension_level,
                    'confidence_score': seg.confidence_score,
                    'feedback_message': seg.feedback_message,
                    'suggested_improvements': seg.suggested_improvements,
                    'segments': seg.segments,
                    'code_mappings': seg.code_mappings,
                }

            submission_data = {
                'id': str(submission.submission_id),
                'attempt_number': len(submissions) - index,  # Reverse numbering (oldest = 1)
                'submitted_at': submission.submitted_at.isoformat(),
                'score': submission.score,
                'passed_all_tests': submission.passed_all_tests,
                'completion_status': submission.completion_status,
                'execution_status': submission.execution_status,
                'submission_type': submission.submission_type,
                'tests_passed': passed_tests,
                'total_tests': total_tests,
                'execution_time_ms': submission.execution_time_ms,
                'is_best': False,  # Will be set later
                'variations_count': variations.count(),
                'comprehension_level': submission.comprehension_level if submission.submission_type == 'eipl' else None,
                'segmentation': segmentation_data,  # Include segmentation data

                # Include the actual submission data for switching
                'data': {
                    'raw_input': submission.raw_input,
                    'processed_code': submission.processed_code,
                    'variations': [
                        {
                            'code': var.generated_code,
                            'variation_number': var.variation_index,
                            'passed_all_tests': var.score >= 100,
                            'tests_passed': var.tests_passed,
                            'total_tests': var.tests_total,
                            # Include test results for this specific variation
                            # FALLBACK: Create placeholder results if TestExecution records missing
                            'test_results': (
                                lambda var_tests: var_tests if var_tests else [
                                    {
                                        'test_case_id': None,
                                        'passed': i < var.tests_passed,
                                        'expected': 'Test details not available',
                                        'actual': 'Passed' if i < var.tests_passed else 'Failed',
                                        'error_message': '' if i < var.tests_passed else 'Test failed (details not available)',
                                        'inputs': {}
                                    }
                                    for i in range(var.tests_total)
                                ] if var.tests_total > 0 else []
                            )([
                                {
                                    'test_case_id': te.test_case_id,
                                    'passed': te.passed,
                                    'expected': te.expected_output,
                                    'actual': te.actual_output,
                                    'error_message': te.error_message if hasattr(te, 'error_message') else '',
                                    'inputs': te.input_values
                                }
                                for te in test_executions.filter(code_variation=var)
                            ])
                        }
                        for var in variations
                    ],
                    # Keep test_results at top level for non-variation submissions
                    'test_results': [
                        {
                            'test_case_id': te.test_case_id,
                            'passed': te.passed,
                            'expected': te.expected_output,
                            'actual': te.actual_output,
                            'error_message': te.error_message if hasattr(te, 'error_message') else '',
                            'inputs': te.input_values
                        }
                        for te in test_executions if not variations.exists()
                    ] if not variations.exists() else []
                }
            }

            submission_history.append(submission_data)

        # Mark the best attempt
        for submission in submission_history:
            if submission['id'] == best_attempt_id:
                submission['is_best'] = True

        # Get current progress
        progress = ProgressService.get_user_progress(
            user_id=request.user.id,
            problem_id=problem.id,
            course_id=filters.get('course').id if filters.get('course') else None
        )

        return Response({
            'problem_slug': problem_slug,
            'total_attempts': len(submission_history),
            'best_score': best_score,
            'best_attempt_id': best_attempt_id,
            'current_progress': {
                'status': progress.status if progress else 'not_started',
                'best_score': progress.best_score if progress else 0,
                'attempts': progress.attempts if progress else 0,
                'is_completed': progress.is_completed if progress else False,
            } if progress else None,
            'submissions': submission_history
        })
