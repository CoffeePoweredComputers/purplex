"""
Clean, single-task pipeline for EiPL submissions.

This replaces the complex chain architecture with a single orchestrator task
that manages the entire pipeline and publishes consistent progress events.
"""

from celery import shared_task
import json
import logging
import os
import time
import redis
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from django.conf import settings
from django.db import transaction

# Import services only (not repositories directly)
from purplex.problems_app.services.problem_service import ProblemService
from purplex.problems_app.services.test_case_service import TestCaseService
from purplex.problems_app.services.submission_service import SubmissionService
from purplex.problems_app.services.ai_generation_service import AITestGenerationService
from purplex.problems_app.services.docker_execution_service import DockerExecutionService as CodeExecutionService
from purplex.problems_app.services.segmentation_service import SegmentationService
from purplex.problems_app.services.course_service import CourseService
from purplex.users_app.services.user_service import UserService

# Import models only for type hints
if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from purplex.problems_app.models import Problem, ProblemSet, Course
    from purplex.submissions_app.models import PromptSubmission, SegmentationResult

logger = logging.getLogger(__name__)

# Redis client for publishing events
redis_client = redis.Redis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=0,
    decode_responses=True
)


def publish_progress(task_id: str, progress: float, message: str, extra_data: dict = None):
    """Publish a progress event to the Redis channel."""
    channel = f'task:{task_id}'
    event_data = {
        'type': 'update',
        'timestamp': time.time(),
        'status': 'processing',
        'progress': progress / 100.0,  # Convert to 0-1 range
        'message': message
    }
    if extra_data:
        event_data.update(extra_data)
    
    try:
        redis_client.publish(channel, json.dumps(event_data))
        logger.debug(f"Published progress {progress}%: {message}")
    except Exception as e:
        logger.error(f"Failed to publish progress event: {e}")


def publish_completion(task_id: str, result: dict):
    """Publish completion event with full results."""
    channel = f'task:{task_id}'
    event_data = {
        'type': 'completed',
        'timestamp': time.time(),
        'status': 'completed',
        'message': f"Submission complete! Score: {result.get('score', 0)}%",
        'result': result
    }
    
    try:
        redis_client.publish(channel, json.dumps(event_data))
        logger.info(f"Published completion event for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to publish completion event: {e}")


def publish_error(task_id: str, error_message: str):
    """Publish error event."""
    channel = f'task:{task_id}'
    event_data = {
        'type': 'failed',
        'timestamp': time.time(),
        'status': 'failed',
        'error': error_message,
        'message': f"Task failed: {error_message}"
    }
    
    try:
        redis_client.publish(channel, json.dumps(event_data))
        logger.error(f"Published error event: {error_message}")
    except Exception as e:
        logger.error(f"Failed to publish error event: {e}")


def generate_variations_helper(problem_id: int, user_prompt: str) -> List[str]:
    """Helper function to generate code variations using service layer."""
    # Get problem through service
    problem = ProblemService.get_problem_by_id(problem_id)
    if not problem or not problem.is_active:
        raise Exception(f"Problem {problem_id} not found or not active")
    
    ai_service = AITestGenerationService()
    result = ai_service.generate_eipl_variations(problem, user_prompt)
    
    if not result['success']:
        raise Exception(f"AI generation failed: {result.get('error', 'Unknown error')}")
    
    return result.get('variations', [])


def test_variation_helper(code: str, problem_id: int, variation_index: int) -> Dict[str, Any]:
    """Helper function to test a single variation using service layer."""
    # Get problem through service
    problem = ProblemService.get_problem_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")
    
    # Get test cases formatted for testing through service
    test_cases = TestCaseService.get_test_cases_for_testing(problem, include_hidden=True)
    
    logger.debug(f"Testing variation {variation_index} with {len(test_cases)} test cases")
    
    # Parse JSON fields if needed
    for tc in test_cases:
        if isinstance(tc['inputs'], str):
            try:
                tc['inputs'] = json.loads(tc['inputs'])
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(tc['expected_output'], str):
            try:
                tc['expected_output'] = json.loads(tc['expected_output'])
            except (json.JSONDecodeError, TypeError):
                pass
    
    # Test the code
    service = CodeExecutionService()
    # Set user context for async task (no user context in celery tasks)
    service.set_user_context(f"task_{variation_index}")
    result = service.test_solution(code, problem.function_name, test_cases)
    
    logger.debug(f"Test result keys: {list(result.keys())}")
    logger.debug(f"Test result: {result}")
    
    testsPassed = result.get('testsPassed', 0)
    totalTests = result.get('totalTests', 0)
    
    logger.debug(f"Variation {variation_index}: {testsPassed}/{totalTests} tests passed")
    
    return {
        'variation_index': variation_index,
        'code': code,
        'testsPassed': testsPassed,
        'totalTests': totalTests,
        'success': testsPassed == totalTests and totalTests > 0,
        'test_results': result.get('results', [])
    }


def segment_prompt_helper(user_prompt: str, problem_id: int) -> Optional[Dict[str, Any]]:
    """Helper function for prompt segmentation using service layer."""
    # Get problem through service
    problem = ProblemService.get_problem_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")
    
    if not problem.segmentation_enabled:
        return None
    
    service = SegmentationService()
    segmentation_result = service.segment_prompt(
        user_prompt=user_prompt,
        reference_code=problem.reference_solution,
        problem_config=problem.segmentation_config or {}
    )
    
    return segmentation_result


def save_submission_helper(
    user_id: int,
    problem_id: int,
    problem_set_id: int,
    course_id: Optional[int],
    user_prompt: str,
    variations: List[str],
    test_results: List[Dict],
    segmentation: Optional[Dict],
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper function to save the submission using service layer."""
    # Get objects through services/repositories
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise Exception(f"User {user_id} not found")
    
    problem = ProblemService.get_problem_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")
    
    problem_set = None
    if problem_set_id:
        problem_set = ProblemService.get_problem_set_by_id(problem_set_id)
        if not problem_set:
            raise Exception(f"Problem set {problem_set_id} not found")
    
    course = None
    if course_id:
        # Use get_course_by_pk for integer IDs
        logger.info(f"Attempting to fetch course with ID: {course_id}")
        course = CourseService.get_course_by_pk(course_id)
        if not course:
            # Add diagnostic information
            logger.error(f"Course {course_id} not found in Celery task")
            logger.error(f"Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE', 'NOT SET')}")
            logger.error(f"PURPLEX_ENV: {os.environ.get('PURPLEX_ENV', 'NOT SET')}")
            from django.conf import settings
            logger.error(f"Database engine: {settings.DATABASES['default']['ENGINE']}")
            logger.error(f"Database name: {settings.DATABASES['default'].get('NAME', 'UNKNOWN')}")
            raise Exception(f"Course {course_id} not found")
    
    # Calculate score
    successful_variations = sum(1 for r in test_results if r.get('success', False))
    total_variations = len(test_results)
    score = int((successful_variations / total_variations * 100) if total_variations > 0 else 0)
    
    with transaction.atomic():
        # Create submission
        submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            prompt=user_prompt,
            course=course,
            problem_set=problem_set,
            score=score,
            code_variations=variations,
            test_results=test_results,
            passing_variations=successful_variations,
            total_variations=total_variations,
            task_id=task_id
        )
        
        # Create segmentation record if available
        if segmentation and segmentation.get('success'):
            comp_level = segmentation.get('comprehension_level', 'relational')
            if comp_level not in ['relational', 'multi_structural']:
                comp_level = 'relational'
            
            SubmissionService.create_segmentation_result(
                submission=submission,
                analysis=segmentation,
                segment_count=segmentation.get('segment_count', 0),
                comprehension_level=comp_level
            )
    
    return {
        'submission_id': submission.id,
        'variations': variations,
        'test_results': test_results,
        'score': score,
        'successful_variations': successful_variations,
        'total_variations': total_variations,
        'passing_variations': successful_variations,
        'user_prompt': user_prompt,
        'problem_slug': problem.slug,
        'user': user.username,
        'segmentation': segmentation  # Include segmentation data
    }


@shared_task(bind=True, name='pipeline.execute_eipl')
def execute_eipl_pipeline(
    self,
    problem_id: int,
    user_prompt: str,
    user_id: int,
    problem_set_id: Optional[int] = None,
    course_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Single orchestrator task for the entire EiPL pipeline.
    
    This task manages all pipeline stages and publishes consistent
    progress events to a single Redis channel.
    
    Args:
        problem_id: Database ID of the problem
        user_prompt: User's explanation of their approach
        user_id: ID of the user making the submission
        problem_set_id: Optional problem set ID
        course_id: Optional course ID
        
    Returns:
        Complete submission result
    """
    task_id = self.request.id
    logger.info(f"Starting EiPL pipeline {task_id} for problem {problem_id}")
    
    # Ensure Django is properly initialized
    import django
    if not django.apps.apps.ready:
        logger.warning("Django apps not ready, calling setup()")
        django.setup()
    
    # Log current settings module for debugging
    from django.conf import settings
    logger.info(f"Task using Django settings: {os.environ.get('DJANGO_SETTINGS_MODULE', 'NOT SET')}")
    logger.info(f"PURPLEX_ENV: {os.environ.get('PURPLEX_ENV', 'NOT SET')}")
    logger.info(f"Database engine: {settings.DATABASES['default']['ENGINE']}")
    logger.info(f"Database name: {settings.DATABASES['default'].get('NAME', 'UNKNOWN')}")
    
    try:
        # Verify database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            logger.info("Database connection verified successfully")
        
        # Initialize
        publish_progress(task_id, 0, "Starting pipeline...")
        
        # Step 1: Generate variations (0-20% progress)
        publish_progress(task_id, 5, "Generating code variations from your prompt...")
        variations = generate_variations_helper(problem_id, user_prompt)
        variation_count = len(variations)
        logger.info(f"Generated {variation_count} variations")
        publish_progress(task_id, 20, f"Generated {variation_count} code variations")
        
        # Step 2: Test each variation (20-70% progress)
        test_results = []
        for i, code in enumerate(variations):
            # Calculate progress within testing phase
            test_progress = 20 + (50 * i / variation_count)
            publish_progress(
                task_id, 
                test_progress,
                f"Testing variation {i+1} of {variation_count}..."
            )
            
            result = test_variation_helper(code, problem_id, i)
            test_results.append(result)
            
            # Report result of this variation
            if result['success']:
                publish_progress(
                    task_id,
                    20 + (50 * (i+1) / variation_count),
                    f"Variation {i+1}: ✓ Passed all tests"
                )
            else:
                publish_progress(
                    task_id,
                    20 + (50 * (i+1) / variation_count),
                    f"Variation {i+1}: {result['testsPassed']}/{result['totalTests']} tests passed"
                )
        
        # Step 3: Aggregate results (70-80% progress)
        publish_progress(task_id, 70, "Aggregating test results...")
        successful_variations = sum(1 for r in test_results if r.get('success', False))
        score = int((successful_variations / variation_count * 100) if variation_count > 0 else 0)
        logger.info(f"Score: {score}% ({successful_variations}/{variation_count} passed)")
        publish_progress(task_id, 80, f"Score calculated: {score}%")
        
        # Step 4: Segment prompt if enabled (80-90% progress)
        segmentation = None
        try:
            publish_progress(task_id, 85, "Analyzing comprehension level...")
            segmentation = segment_prompt_helper(user_prompt, problem_id)
            if segmentation:
                logger.info(f"Segmentation complete: {segmentation.get('segment_count', 0)} segments")
                publish_progress(task_id, 90, "Comprehension analysis complete")
            else:
                publish_progress(task_id, 90, "Segmentation skipped (not enabled)")
        except Exception as e:
            logger.warning(f"Segmentation failed (non-critical): {e}")
            publish_progress(task_id, 90, "Segmentation skipped")
        
        # Step 5: Save submission (90-100% progress)
        publish_progress(task_id, 95, "Saving submission...")
        
        submission_result = save_submission_helper(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id,
            user_prompt=user_prompt,
            variations=variations,
            test_results=test_results,
            segmentation=segmentation,
            task_id=task_id
        )
        
        logger.info(f"Submission {submission_result['submission_id']} saved successfully")
        logger.info(f"Submission result includes segmentation: {bool(submission_result.get('segmentation'))}")
        if submission_result.get('segmentation'):
            logger.info(f"Segmentation data: {submission_result['segmentation']}")
        publish_progress(task_id, 100, f"Submission complete! Score: {score}%")
        
        # Publish completion event
        publish_completion(task_id, submission_result)
        
        return submission_result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Pipeline failed: {error_msg}", exc_info=True)
        
        # Include more details in the error message
        detailed_error = {
            'error': error_msg,
            'task_id': task_id,
            'problem_id': problem_id,
            'user_id': user_id,
            'settings_module': os.environ.get('DJANGO_SETTINGS_MODULE', 'NOT SET'),
            'database_engine': settings.DATABASES['default'].get('ENGINE', 'UNKNOWN')
        }
        
        logger.error(f"Pipeline failure details: {json.dumps(detailed_error)}")
        publish_error(task_id, error_msg)
        
        # Re-raise to mark task as failed in Celery
        raise