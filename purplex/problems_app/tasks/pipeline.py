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
from purplex.utils.redis_client import get_pubsub_client
from django.db import transaction
from gevent.pool import Pool as GeventPool
from gevent import Greenlet

# Try to import sentry_sdk for monitoring (optional)
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

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
        client = get_pubsub_client()  # Use centralized client
        client.publish(channel, json.dumps(event_data))
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"⚠️ Redis connection failed while publishing progress event: {e}")
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
        client = get_pubsub_client()  # Use centralized client
        client.publish(channel, json.dumps(event_data))
        logger.info(f"Published completion event for task {task_id}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"⚠️ Redis connection failed while publishing completion event: {e}")
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
        client = get_pubsub_client()  # Use centralized client
        client.publish(channel, json.dumps(event_data))
        logger.error(f"Published error event: {error_message}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"⚠️ Redis connection failed while publishing error event: {e}")
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

    # DEBUG: Log raw Docker result to capture errors
    logger.warning(f"🔍 Variation {variation_index} Docker result: testsPassed={result.get('testsPassed')}, totalTests={result.get('totalTests')}, error={result.get('error', 'None')}, success={result.get('success', 'N/A')}")

    testsPassed = result.get('testsPassed', 0)
    totalTests = result.get('totalTests', 0)

    # Add test case IDs to results
    results_with_ids = []
    for idx, test_result in enumerate(result.get('results', [])):
        if idx < len(test_case_ids):
            test_result['test_case_id'] = test_case_ids[idx]
        results_with_ids.append(test_result)

    # CRITICAL BUG DETECTION: If we have summary counts but empty results, something is wrong
    if totalTests > 0 and len(results_with_ids) == 0:
        logger.error(
            f"🚨 CRITICAL: Docker returned testsPassed={testsPassed}, totalTests={totalTests} "
            f"but results array is EMPTY! This will cause missing TestExecution records. "
            f"Docker result keys: {result.keys()}, success={result.get('success')}, error={result.get('error')}"
        )

    # Build return dict with optional error field
    ret = {
        'variation_index': variation_index,
        'code': code,
        'testsPassed': testsPassed,
        'totalTests': totalTests,
        'success': testsPassed == totalTests and totalTests > 0,
        'test_results': results_with_ids
    }

    # Preserve error message if present (critical for debugging!)
    if 'error' in result:
        ret['error'] = result['error']

    return ret


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
        # Defensive: handle None segmentation_config
        config = problem.segmentation_config or {}
        threshold = config.get('threshold', 2)
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
        from django.core.cache import cache
        context_data = cache.get(f"eipl:context:{task_id}")
        if context_data:
            # Django cache already deserializes the data
            activated_hints = context_data.get('activated_hints', [])
            if activated_hints:
                logger.info(f"Retrieved {len(activated_hints)} activated hints from context")
    except Exception as e:
        logger.warning(f"Failed to retrieve hint context: {e}")
        activated_hints = None

    # PERFORMANCE: Single atomic transaction to reduce DB overhead
    # Previously: 3 separate transactions caused ~60% extra DB load
    with transaction.atomic():
        # Create submission using _no_transaction method to avoid nested transactions
        # The outer transaction.atomic() manages the entire pipeline as one unit
        submission = SubmissionService._create_submission_no_transaction(
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
                'model': 'gpt-4o-mini'
            })

        # PERFORMANCE: Bulk create variations instead of individual creates
        # Create variation objects in memory first
        variation_objects = [
            CodeVariation(
                submission=submission,
                variation_index=idx,
                generated_code=var_data['code'],
                tests_passed=var_data.get('tests_passed', 0),
                tests_total=var_data.get('tests_total', 0),
                score=var_data.get('score', 0),
                model_used=var_data.get('model', 'gpt-4o-mini')
            )
            for idx, var_data in enumerate(variation_data)
        ]

        # Bulk create all variations in one query
        created_variations = CodeVariation.objects.bulk_create(variation_objects)

        # Mark best variation only if we have results
        if test_results and created_variations:
            best_idx = max(range(len(test_results)), key=lambda i: test_results[i].get('testsPassed', 0))
            best_variation = created_variations[best_idx]
            best_variation.is_selected = True
            best_variation.save()

        # Prepare test execution data for ALL variations
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

        # Record test results using _no_transaction method (no nested transaction)
        SubmissionService._record_eipl_test_results_no_transaction(
            submission=submission,
            variations_with_tests=variations_with_tests
        )

        # Store the best code for reference (if we have variations)
        if created_variations:
            # If we marked a best variation, use it; otherwise use the first one
            best_variation = next((v for v in created_variations if v.is_selected), created_variations[0])
            submission.processed_code = best_variation.generated_code
        else:
            # No variations generated - store empty code
            submission.processed_code = ""

        submission.is_correct = submission.passed_all_tests
        submission.save()

        # Record segmentation if available (using internal method)
        if segmentation and segmentation.get('success'):
            segmentation_data = {
                'segment_count': segmentation.get('segment_count', 0),
                'comprehension_level': segmentation.get('comprehension_level', 'relational'),
                'segments': segmentation.get('segments', []),
                'code_mappings': segmentation.get('code_mappings', {}),
                'confidence': segmentation.get('confidence', 0.8),
                'processing_time_ms': int(segmentation.get('processing_time', 0) * 1000),
                'model': 'gpt-4o-mini',
                'feedback': segmentation.get('feedback', ''),
                'improvements': segmentation.get('suggestions', []),
                'passed': segmentation.get('passed', False)  # Include the passed field
            }

            SubmissionService._record_segmentation_no_transaction(submission, segmentation_data)

    # Only include segmentation data if it's enabled for the problem
    result_data = {
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
    }

    # Only include segmentation if enabled for this problem
    if problem.segmentation_enabled:
        result_data['segmentation'] = segmentation
    else:
        result_data['segmentation'] = None

    return result_data


@shared_task(bind=True, name='pipeline.execute_code_test')
def execute_code_test(
    self,
    code: str,
    problem_id: int,
    test_case_ids: List[int],
    include_hidden: bool = False,
    submission_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute code against test cases in Celery worker (uses shared Docker service).

    This task runs code execution in the Celery worker pool, which:
    - Uses the shared DockerExecutionService (one pool per Celery worker)
    - Prevents web workers from creating Docker pools
    - Enables proper resource management
    - Publishes real-time progress events via SSE
    - Optionally creates submission records

    Args:
        code: User's code to test
        problem_id: Problem ID
        test_case_ids: List of test case IDs to run
        include_hidden: Whether to include hidden test cases
        submission_context: Optional dict with submission metadata for creating records

    Returns:
        Test results in standard format
    """
    task_id = self.request.id
    logger.info(f"Executing code test {task_id} for problem {problem_id}")

    # CRITICAL: Allow Django ORM calls in gevent context
    # With gevent workers, Django detects greenlet as async context and blocks ORM
    # This tells Django it's safe to make synchronous database calls from this task
    import os
    os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

    try:
        # Publish initial progress
        publish_progress(task_id, 0, "Starting code execution...")

        # Get problem and test cases through services
        publish_progress(task_id, 10, "Loading problem and test cases...")
        problem = ProblemService.get_problem_by_id(problem_id)
        if not problem:
            raise Exception(f"Problem {problem_id} not found")

        # Get test cases
        test_cases = TestCaseService.get_test_cases_for_testing(
            problem,
            include_hidden=include_hidden,
            test_case_ids=test_case_ids if test_case_ids else None
        )

        # Execute code using shared Docker service
        publish_progress(task_id, 30, f"Running {len(test_cases)} test cases...")
        with SharedDockerServiceContext() as service:
            service.set_user_context(f"task_{task_id}")
            result = service.test_solution(code, problem.function_name, test_cases)

        tests_passed = result.get('testsPassed', 0)
        total_tests = result.get('totalTests', 0)

        logger.info(f"Code test {task_id} completed: {tests_passed}/{total_tests} passed")
        publish_progress(task_id, 70, f"Tests completed: {tests_passed}/{total_tests} passed")

        # If submission context provided, create submission record
        if submission_context:
            publish_progress(task_id, 80, "Saving submission...")

            # Get user and other objects
            user = UserService.get_user_by_id(submission_context['user_id'])
            problem_set = None
            if submission_context.get('problem_set_id'):
                problem_set = ProblemService.get_problem_set_by_id(submission_context['problem_set_id'])

            course = None
            if submission_context.get('course_id'):
                course = CourseService.get_course_by_pk(submission_context['course_id'])

            # Get test cases for submission
            from ..models import TestCase
            all_test_cases = TestCase.objects.filter(id__in=test_case_ids).order_by('id')

            # Create submission record
            time_spent_delta = None
            if submission_context.get('time_spent'):
                from datetime import timedelta
                time_spent_delta = timedelta(seconds=int(submission_context['time_spent']))

            submission = SubmissionService.create_submission(
                user=user,
                problem=problem,
                raw_input=submission_context.get('prompt') or code,
                submission_type='direct_code',
                problem_set=problem_set,
                course=course,
                time_spent=time_spent_delta,
                activated_hints=submission_context.get('activated_hints', [])
            )

            # Record test results
            test_execution_data = []
            for i, test_result in enumerate(result.get('results', [])):
                if i < len(all_test_cases):
                    test_case = all_test_cases[i]

                    # Get actual output
                    actual_output = test_result.get('actual_output')
                    if actual_output is None:
                        actual_output = test_result.get('output')
                    if actual_output is None:
                        actual_output = ''

                    # Check for success
                    test_passed = test_result.get('isSuccessful', False) or test_result.get('pass', False)

                    test_execution_data.append({
                        'test_case_id': test_case.id,
                        'passed': test_passed,
                        'inputs': test_case.inputs,
                        'expected': test_case.expected_output,
                        'actual': actual_output,
                        'error_type': 'none' if test_passed else 'wrong_output',
                        'error_message': test_result.get('error', '')
                    })

            SubmissionService.record_test_results(
                submission=submission,
                test_results=test_execution_data,
                processed_code=code,
                execution_time_ms=None,
                memory_used_mb=None
            )

            # Add submission info to result
            result['submission_id'] = str(submission.submission_id)
            result['score'] = submission.score

            # Get progress for response
            from ..services.progress_service import ProgressService
            progress = ProgressService.get_user_progress(
                user_id=user.id,
                problem_id=problem.id,
                course_id=course.id if course else None
            )

            result['progress'] = {
                'status': progress.status if progress else 'not_started',
                'best_score': progress.best_score if progress else 0,
                'attempts': progress.attempts if progress else 0,
                'is_completed': progress.is_completed if progress else False,
                'grade': getattr(progress, 'grade', None),
            }

            # Get grade
            from purplex.submissions.grading_service import GradingService
            result['grade'] = GradingService.calculate_grade(submission)

            publish_progress(task_id, 100, f"Submission complete! Score: {submission.score}%")
        else:
            publish_progress(task_id, 100, f"Tests complete: {tests_passed}/{total_tests} passed")

        # Publish completion event
        publish_completion(task_id, result)

        return result

    except Exception as e:
        logger.error(f"Code test {task_id} failed: {e}", exc_info=True)
        error_result = {
            'error': str(e),
            'testsPassed': 0,
            'totalTests': len(test_case_ids) if test_case_ids else 0,
            'results': [],
            'success': False
        }

        # Publish error event
        publish_error(task_id, str(e))

        return error_result


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
    Single orchestrator task for the entire EiPL pipeline with Sentry monitoring.

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
    logger.info(f"🚀 PIPELINE START: task_id={task_id}, problem_id={problem_id}, user_id={user_id}")
    logger.info(f"📝 Pipeline context: problem_set_id={problem_set_id}, course_id={course_id}, prompt_length={len(user_prompt)}")
    logger.info(f"🔧 Celery task info: retries={self.request.retries}")

    # CRITICAL: Publish initial progress immediately to confirm task is running
    publish_progress(task_id, 0, "🎬 Task received by Celery worker, initializing...")

    # CRITICAL: Allow Django ORM calls in gevent context
    # With gevent workers, Django detects greenlet as async context and blocks ORM
    # This tells Django it's safe to make synchronous database calls from this task
    import os
    os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

    # Ensure Django is properly initialized
    import django
    if not django.apps.apps.ready:
        logger.warning("Django apps not ready, calling setup()")
        django.setup()

    # Start Sentry transaction if available
    if SENTRY_AVAILABLE:
        transaction = sentry_sdk.start_transaction(
            op="celery.task",
            name="execute_eipl_pipeline",
            description=f"Process EiPL submission for problem {problem_id}"
        )
        transaction.set_tag("problem_id", problem_id)
        transaction.set_tag("user_id", user_id)
        if problem_set_id:
            transaction.set_tag("problem_set_id", problem_set_id)
        if course_id:
            transaction.set_tag("course_id", course_id)
    else:
        transaction = None

    try:
        # Initialize
        logger.info(f"⏱️  STEP 0: Initializing pipeline for task {task_id}")
        publish_progress(task_id, 0, "Starting pipeline...")

        # Step 1: Generate variations (0-20% progress)
        logger.info(f"⏱️  STEP 1: Starting AI code generation for task {task_id}")
        publish_progress(task_id, 5, "Generating code variations from your prompt...")

        if SENTRY_AVAILABLE and transaction:
            span = transaction.start_child(
                op="ai.generate",
                description="Generate code variations from prompt"
            )
        else:
            span = None

        try:
            variations = generate_variations_helper(problem_id, user_prompt)
            variation_count = len(variations)
            logger.info(f"✅ STEP 1 COMPLETE: Generated {variation_count} variations for task {task_id}")
        except Exception as gen_error:
            logger.error(f"❌ STEP 1 FAILED: AI generation failed for task {task_id}: {str(gen_error)}", exc_info=True)
            raise

        if SENTRY_AVAILABLE and span:
            span.set_data("variation_count", variation_count)
            span.finish()

        # Check if we got any variations
        if variation_count == 0:
            logger.warning(f"No variations generated for problem {problem_id}")
            publish_progress(task_id, 20, "No code variations could be generated")
        else:
            publish_progress(task_id, 20, f"Generated {variation_count} code variations")

        # Step 2: Test each variation in parallel (20-70% progress)
        # PERFORMANCE: GeventPool for parallel I/O-bound Docker operations (gevent-native, no deadlocks)
        # Previously: Sequential testing took ~15 seconds for 3 variations
        # Now: Parallel testing with greenlets takes ~0.2 seconds (99% faster!)
        logger.info(f"⏱️  STEP 2: Starting parallel code testing for {variation_count} variations (task {task_id})")

        if SENTRY_AVAILABLE and transaction:
            test_span = transaction.start_child(
                op="code.execution",
                description="Execute and test code variations in parallel"
            )
        else:
            test_span = None

        test_results = []

        # Use GeventPool for parallel execution (gevent-native, no threading conflicts)
        # With pool of 30 containers, we can safely run all variations in parallel
        # CRITICAL: GeventPool instead of ThreadPoolExecutor prevents deadlocks with gevent workers
        max_workers = min(variation_count, 6)  # Allow up to 6 concurrent tests (pool has 30 containers)

        # Create gevent pool for cooperative concurrency
        pool = GeventPool(size=max_workers)

        # Spawn greenlets for each variation test
        greenlet_to_index = {}
        for i, code in enumerate(variations):
            greenlet = pool.spawn(test_variation_helper, code, problem_id, i)
            greenlet_to_index[greenlet] = i

        # Collect results as they complete
        completed = 0
        results_by_index = {}

        # Wait for greenlets to complete (cooperative, no deadlock)
        for greenlet in greenlet_to_index:
            i = greenlet_to_index[greenlet]
            completed += 1

            try:
                # Greenlet.get() blocks cooperatively (gevent-aware)
                result = greenlet.get()
                results_by_index[i] = result

                # Calculate progress
                test_progress = 20 + (50 * completed / max(variation_count, 1))

                # Report result of this variation
                if result['success']:
                    publish_progress(
                        task_id,
                        test_progress,
                        f"Variation {i+1}: ✓ Passed all tests ({completed}/{variation_count} complete)"
                    )
                else:
                    # Include error message if present
                    error_msg = result.get('error', '')
                    if error_msg:
                        publish_progress(
                            task_id,
                            test_progress,
                            f"Variation {i+1}: ERROR - {error_msg[:80]} ({completed}/{variation_count} complete)"
                        )
                        logger.warning(f"Variation {i+1} failed: {error_msg}")
                    else:
                        publish_progress(
                            task_id,
                            test_progress,
                            f"Variation {i+1}: {result['testsPassed']}/{result['totalTests']} tests passed ({completed}/{variation_count} complete)"
                        )

            except Exception as e:
                # Enhanced error logging with full traceback
                import traceback
                error_details = traceback.format_exc()
                logger.error(
                    f"❌ Variation {i+1} testing FAILED with exception\n"
                    f"Problem ID: {problem_id}\n"
                    f"Variation Index: {i}\n"
                    f"Error: {str(e)}\n"
                    f"Traceback:\n{error_details}"
                )

                # Publish error to user
                publish_progress(
                    task_id,
                    20 + (50 * completed / max(variation_count, 1)),
                    f"⚠️ Variation {i+1}: Testing failed - {str(e)[:100]} ({completed}/{variation_count} complete)"
                )

                results_by_index[i] = {
                    'variation_index': i,
                    'code': variations[i],
                    'testsPassed': 0,
                    'totalTests': 0,
                    'success': False,
                    'test_results': [],
                    'error': str(e),
                    'error_traceback': error_details
                }

        # Kill the pool to clean up resources
        pool.kill()

        # Reconstruct results in original order
        test_results = [results_by_index[i] for i in range(variation_count)]

        successful_variations = sum(1 for r in test_results if r.get('success', False))
        logger.info(f"✅ STEP 2 COMPLETE: Tested {variation_count} variations, {successful_variations} passed (task {task_id})")

        if SENTRY_AVAILABLE and test_span:
            test_span.set_data("variations_tested", variation_count)
            test_span.set_data("variations_passed", successful_variations)
            test_span.set_data("parallel_workers", max_workers)
            test_span.finish()

        # Step 3: Aggregate results (70-80% progress)
        logger.info(f"⏱️  STEP 3: Aggregating results (task {task_id})")
        publish_progress(task_id, 70, "Aggregating test results...")
        score = int((successful_variations / variation_count * 100) if variation_count > 0 else 0)
        logger.info(f"📊 Score calculated: {score}% ({successful_variations}/{variation_count} passed)")
        publish_progress(task_id, 80, f"Score calculated: {score}%")

        # Step 4: Segment prompt if enabled (80-90% progress)
        # TWO-STAGE LEARNING: Only analyze comprehension AFTER correctness is achieved
        segmentation = None

        # Check if ALL variations passed ALL tests (100% correctness gate)
        all_variations_passed = all(r.get('success', False) for r in test_results)

        if all_variations_passed:
            # Stage 2: Comprehension Analysis - student has achieved correctness
            try:
                publish_progress(task_id, 85, "✓ All variations correct! Now analyzing comprehension level...")

                if SENTRY_AVAILABLE and transaction:
                    seg_span = transaction.start_child(
                        op="ai.analyze",
                        description="Segment and analyze prompt"
                    )
                else:
                    seg_span = None

                segmentation = segment_prompt_helper(user_prompt, problem_id)

                if SENTRY_AVAILABLE and seg_span:
                    if segmentation:
                        seg_span.set_data("segment_count", segmentation.get('segment_count', 0))
                    seg_span.finish()

                if segmentation:
                    logger.info(f"Segmentation complete: {segmentation.get('segment_count', 0)} segments")
                    publish_progress(task_id, 90, "Comprehension analysis complete")
                else:
                    publish_progress(task_id, 90, "Segmentation skipped (not enabled)")
            except Exception as e:
                logger.warning(f"Segmentation failed (non-critical): {e}")
                publish_progress(task_id, 90, "Segmentation skipped")
        else:
            # Stage 1: Correctness Gate - student should focus on getting it right first
            publish_progress(
                task_id,
                90,
                f"Focus on getting a correct solution first! {successful_variations}/{variation_count} variations passed all tests."
            )
            logger.info(f"Skipping segmentation - correctness gate not met: {successful_variations}/{variation_count} variations passed")
            # segmentation remains None - comprehension not analyzed until correctness achieved

        # Step 5: Save submission (90-100% progress)
        logger.info(f"⏱️  STEP 5: Saving submission to database (task {task_id})")
        publish_progress(task_id, 95, "Saving submission...")

        if SENTRY_AVAILABLE and transaction:
            save_span = transaction.start_child(
                op="db.update",
                description="Save submission and results"
            )
        else:
            save_span = None

        try:
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
            logger.info(f"✅ STEP 5 COMPLETE: Submission {submission_result['submission_id']} saved successfully (task {task_id})")
        except Exception as save_error:
            logger.error(f"❌ STEP 5 FAILED: Failed to save submission for task {task_id}: {str(save_error)}", exc_info=True)
            raise

        if SENTRY_AVAILABLE and save_span:
            save_span.set_data("submission_id", submission_result.get('submission_id'))
            save_span.finish()

        publish_progress(task_id, 100, f"Submission complete! Score: {score}%")

        # Publish completion event
        publish_completion(task_id, submission_result)

        # Mark transaction as successful
        if SENTRY_AVAILABLE and transaction:
            transaction.set_status("ok")
            transaction.set_data("final_score", score)
            transaction.finish()

        logger.info(f"🎉 PIPELINE COMPLETE: task_id={task_id}, score={score}%, submission_id={submission_result.get('submission_id')}")
        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"💥 PIPELINE FAILED: task_id={task_id}, error={error_msg}\n"
            f"   Problem ID: {problem_id}, User ID: {user_id}\n"
            f"   Problem Set ID: {problem_set_id}, Course ID: {course_id}",
            exc_info=True
        )
        publish_error(task_id, error_msg)

        # Mark transaction as failed and capture exception in Sentry
        if SENTRY_AVAILABLE:
            if transaction:
                transaction.set_status("error")
                transaction.finish()
            sentry_sdk.capture_exception(e, extras={
                "task_id": task_id,
                "problem_id": problem_id,
                "user_id": user_id,
                "problem_set_id": problem_set_id,
                "course_id": course_id,
                "phase": "pipeline_execution"
            })

        # Re-raise to mark task as failed in Celery
        raise
