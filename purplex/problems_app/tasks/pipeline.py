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
from purplex.submissions.services import SubmissionService  # Use new submission service
from purplex.submissions.models import CodeVariation
from purplex.problems_app.services.ai_generation_service import AITestGenerationService
from purplex.problems_app.services.docker_service_factory import SharedDockerServiceContext
from purplex.problems_app.services.segmentation_service import SegmentationService
from purplex.problems_app.services.course_service import CourseService
from purplex.users_app.services.user_service import UserService

# Import models only for type hints
if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from purplex.problems_app.models import Problem, ProblemSet, Course
    from purplex.submissions.models import Submission, SegmentationAnalysis

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

    # Store original test case IDs for later mapping
    test_case_ids = [tc.get('id') for tc in test_cases]

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

    # Test the code using shared Docker service (no cleanup needed)
    with SharedDockerServiceContext() as service:
        # Set user context for async task (no user context in celery tasks)
        service.set_user_context(f"task_{variation_index}")
        result = service.test_solution(code, problem.function_name, test_cases)

    testsPassed = result.get('testsPassed', 0)
    totalTests = result.get('totalTests', 0)

    # Add test case IDs to results
    results_with_ids = []
    for idx, test_result in enumerate(result.get('results', [])):
        if idx < len(test_case_ids):
            test_result['test_case_id'] = test_case_ids[idx]
        results_with_ids.append(test_result)

    return {
        'variation_index': variation_index,
        'code': code,
        'testsPassed': testsPassed,
        'totalTests': totalTests,
        'success': testsPassed == totalTests and totalTests > 0,
        'test_results': results_with_ids
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

    # Add the 'passed' field based on segment count <= threshold
    if segmentation_result:
        threshold = problem.segmentation_config.get('threshold', 2)
        segment_count = segmentation_result.get('segment_count', 0)
        segmentation_result['passed'] = segment_count <= threshold

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
    """Helper function to save the submission using new service layer."""
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
        course = CourseService.get_course_by_pk(course_id)
        if not course:
            logger.error(f"Course {course_id} not found in Celery task")
            raise Exception(f"Course {course_id} not found")

    # Calculate score from test results
    successful_variations = sum(1 for r in test_results if r.get('success', False))
    total_variations = len(test_results)

    # Retrieve hint data from Redis context if available
    activated_hints = None
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=7, decode_responses=True)
        context_data = redis_client.get(f"eipl:context:{task_id}")
        if context_data:
            context = json.loads(context_data)
            activated_hints = context.get('activated_hints', [])
            if activated_hints:
                logger.info(f"Retrieved {len(activated_hints)} activated hints from context")
    except Exception as e:
        logger.warning(f"Failed to retrieve hint context: {e}")
        activated_hints = None

    with transaction.atomic():
        # Create submission using new service
        submission = SubmissionService.create_submission(
            user=user,
            problem=problem,
            raw_input=user_prompt,
            submission_type='eipl',
            problem_set=problem_set,
            course=course,
            time_spent=None,  # Could be passed from frontend in future
            activated_hints=activated_hints  # Now tracking hints from frontend
        )

        # Set the celery task ID
        submission.celery_task_id = task_id
        submission.save()

        # Record code variations for EiPL
        variation_data = []
        for idx, (code, result) in enumerate(zip(variations, test_results)):
            variation_data.append({
                'code': code,
                'tests_passed': result.get('testsPassed', 0),
                'tests_total': result.get('totalTests', 0),
                'score': int((result.get('testsPassed', 0) / result.get('totalTests', 1) * 100)),
                'model': 'gpt-5'
            })

        # Create variations first
        created_variations = []
        for var_data in variation_data:
            variation = CodeVariation.objects.create(
                submission=submission,
                variation_index=len(created_variations),
                generated_code=var_data['code'],
                tests_passed=var_data.get('tests_passed', 0),
                tests_total=var_data.get('tests_total', 0),
                score=var_data.get('score', 0),
                model_used=var_data.get('model', 'gpt-5')
            )
            created_variations.append(variation)

        # Mark best variation
        best_idx = max(range(len(test_results)), key=lambda i: test_results[i].get('testsPassed', 0))
        best_variation = created_variations[best_idx]
        best_variation.is_selected = True
        best_variation.save()

        # Record test results for ALL variations
        variations_with_tests = []
        for variation, result in zip(created_variations, test_results):
            test_execution_data = []
            for test_result in result.get('test_results', []):
                test_case_id = test_result.get('test_case_id')
                if test_case_id:
                    # Get actual output - handle False and other falsy values correctly
                    actual_output = test_result.get('actual_output')
                    if actual_output is None:
                        actual_output = test_result.get('output')
                    if actual_output is None:
                        actual_output = ''

                    test_execution_data.append({
                        'test_case_id': test_case_id,
                        'passed': test_result.get('pass', False) or test_result.get('isSuccessful', False),
                        'inputs': test_result.get('inputs', {}),
                        'expected': test_result.get('expected_output', ''),
                        'actual': actual_output,  # Preserve False, 0, and other falsy values
                        'error_type': 'none' if (test_result.get('pass', False) or test_result.get('isSuccessful', False)) else 'wrong_output',
                        'error_message': test_result.get('error', '')
                    })
                else:
                    logger.warning(f"Skipping test result without test_case_id")
            variations_with_tests.append({
                'variation': variation,
                'test_results': test_execution_data
            })

        SubmissionService.record_eipl_test_results(
            submission=submission,
            variations_with_tests=variations_with_tests
        )

        # Store the best code for reference
        submission.processed_code = best_variation.generated_code
        submission.is_correct = submission.passed_all_tests
        submission.save()

        # Record segmentation if available
        if segmentation and segmentation.get('success'):
            segmentation_data = {
                'segment_count': segmentation.get('segment_count', 0),
                'comprehension_level': segmentation.get('comprehension_level', 'relational'),
                'segments': segmentation.get('segments', []),
                'code_mappings': segmentation.get('code_mappings', {}),
                'confidence': segmentation.get('confidence', 0.8),
                'processing_time_ms': int(segmentation.get('processing_time', 0) * 1000),
                'model': 'gpt-5',
                'feedback': segmentation.get('feedback', ''),
                'improvements': segmentation.get('suggestions', [])
            }

            SubmissionService.record_segmentation(submission, segmentation_data)

    return {
        'submission_id': str(submission.submission_id),  # Use UUID
        'variations': variations,
        'test_results': test_results,
        'score': submission.score,
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
    
    try:
        
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
        publish_progress(task_id, 100, f"Submission complete! Score: {score}%")
        
        # Publish completion event
        publish_completion(task_id, submission_result)
        
        return submission_result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Pipeline failed: {error_msg}", exc_info=True)
        publish_error(task_id, error_msg)
        
        # Re-raise to mark task as failed in Celery
        raise
