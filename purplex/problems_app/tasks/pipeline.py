"""
Clean, single-task pipeline for EiPL submissions.

This replaces the complex chain architecture with a single orchestrator task
that manages the entire pipeline and publishes consistent progress events.
"""

import json
import logging
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import redis
from celery import shared_task
from django.db import transaction
from gevent.pool import Pool as GeventPool

from purplex.utils.redis_client import get_pubsub_client


@contextmanager
def managed_gevent_pool(size: int):
    """Context manager for GeventPool that ensures cleanup on exit."""
    pool = GeventPool(size=size)
    try:
        yield pool
    finally:
        pool.kill()


# Try to import sentry_sdk for monitoring (optional)
try:
    import sentry_sdk

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# Import services and repositories
from purplex.problems_app.repositories import ProblemRepository
from purplex.problems_app.services.ai_generation_service import AITestGenerationService
from purplex.problems_app.services.course_service import CourseService
from purplex.problems_app.services.docker_service_factory import (
    SharedDockerServiceContext,
)
from purplex.problems_app.services.segmentation_service import SegmentationService
from purplex.problems_app.services.test_case_service import TestCaseService
from purplex.submissions.models import CodeVariation
from purplex.submissions.services import SubmissionService  # Use new submission service
from purplex.users_app.services.user_service import UserService

# Import models only for type hints
if TYPE_CHECKING:
    from purplex.problems_app.handlers.base import ActivityHandler
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


def _publish_to_redis(
    channel: str, event_data: dict, event_type: str, max_retries: int = 3
) -> bool:
    """
    Publish to Redis with retry logic for transient failures.

    Returns True if published successfully, False otherwise.
    Never raises - failures are logged but don't break the task.
    """
    for attempt in range(max_retries):
        try:
            client = get_pubsub_client()
            client.publish(channel, json.dumps(event_data))
            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Redis publish retry {attempt + 1}/{max_retries} for {event_type}: {e}"
                )
                time.sleep(0.1 * (attempt + 1))  # Brief backoff: 0.1s, 0.2s
            else:
                logger.error(
                    f"Redis publish failed after {max_retries} attempts for {event_type}: {e}"
                )
        except Exception as e:
            logger.error(f"Unexpected error publishing {event_type}: {e}")
            break

    return False


def publish_progress(
    task_id: str, progress: float, message: str, extra_data: dict = None
):
    """Publish a progress event to the Redis channel."""
    event_data = {
        "type": "update",
        "timestamp": time.time(),
        "status": "processing",
        "progress": progress / 100.0,  # Convert to 0-1 range
        "message": message,
    }
    if extra_data:
        event_data.update(extra_data)

    _publish_to_redis(f"task:{task_id}", event_data, "progress")


def publish_completion(task_id: str, result: dict):
    """Publish completion event with full results."""
    event_data = {
        "type": "completed",
        "timestamp": time.time(),
        "status": "completed",
        "message": f"Submission complete! Score: {result.get('score', 0)}%",
        "result": result,
    }

    if _publish_to_redis(f"task:{task_id}", event_data, "completion"):
        logger.info(f"Published completion event for task {task_id}")


def publish_error(task_id: str, error_message: str):
    """Publish error event."""
    event_data = {
        "type": "failed",
        "timestamp": time.time(),
        "status": "failed",
        "error": error_message,
        "message": f"Task failed: {error_message}",
    }

    if _publish_to_redis(f"task:{task_id}", event_data, "error"):
        logger.error(f"Published error event: {error_message}")


def build_completion_result(
    submission: "Submission",
    handler: "ActivityHandler",
    user_input: str,
    legacy_fields: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Build unified completion result using handler's serialize_result().

    This ensures all activity types emit the same envelope structure,
    enabling a single frontend SSE handler.

    Args:
        submission: The saved Submission instance
        handler: The ActivityHandler for this submission type
        user_input: The original user input/prompt
        legacy_fields: Optional dict of legacy fields for backward compatibility

    Returns:
        Unified envelope with common metadata and type-specific result
    """
    envelope = {
        # Common metadata (all types)
        "submission_id": str(submission.submission_id),
        "problem_type": handler.type_name,
        "score": submission.score,
        "is_correct": submission.passed_all_tests,
        "completion_status": submission.completion_status or "incomplete",
        "problem_slug": submission.problem.slug,
        "user_input": user_input,
        # Type-specific payload from handler
        "result": handler.serialize_result(submission),
    }

    # Merge legacy fields for backward compatibility during migration
    if legacy_fields:
        envelope.update(legacy_fields)

    return envelope


def _build_cached_eipl_result(submission: "Submission") -> dict[str, Any]:
    """
    Build result dict from an existing submission for idempotent retries.

    This is called when a task retry detects the submission already exists
    (due to worker crash with task_acks_late=True).

    Args:
        submission: Existing Submission instance

    Returns:
        Complete result dict matching normal pipeline output
    """
    from purplex.problems_app.handlers import get_handler

    # Ensure we have all the needed data
    submission = (
        submission.__class__.objects.select_related("problem")
        .prefetch_related("code_variations", "code_variations__test_executions")
        .get(pk=submission.pk)
    )

    handler = get_handler("eipl")

    # Build legacy fields from code variations
    legacy_fields = {
        "variations": [cv.generated_code for cv in submission.code_variations.all()],
        "test_results": [],  # Will be populated by handler.serialize_result
        "segmentation": None,
        "successful_variations": sum(
            1
            for cv in submission.code_variations.all()
            if cv.tests_passed == cv.tests_total
        ),
        "total_variations": submission.code_variations.count(),
        "passing_variations": sum(
            1
            for cv in submission.code_variations.all()
            if cv.tests_passed == cv.tests_total
        ),
    }

    # Check for segmentation data
    if hasattr(submission, "segmentation") and submission.segmentation:
        seg = submission.segmentation
        threshold = submission.problem.get_segmentation_threshold
        legacy_fields["segmentation"] = {
            "segment_count": seg.segment_count,
            "comprehension_level": seg.comprehension_level,
            "segments": seg.segments,
            "passed": seg.segment_count <= threshold,
            "threshold": threshold,
            "feedback": seg.feedback_message,
            "improvements": seg.suggested_improvements,
        }

    return build_completion_result(
        submission=submission,
        handler=handler,
        user_input=submission.raw_input,
        legacy_fields=legacy_fields,
    )


def _build_cached_mcq_result(submission: "Submission") -> dict[str, Any]:
    """
    Build result dict from an existing MCQ submission for idempotent retries.

    Args:
        submission: Existing Submission instance

    Returns:
        Complete result dict matching normal MCQ pipeline output
    """
    from purplex.problems_app.handlers import get_handler

    # Re-fetch submission to ensure all relationships are fresh
    # NOTE: 'problem' excluded from select_related for django-polymorphic to resolve subclass
    submission = submission.__class__.objects.get(pk=submission.pk)

    handler = get_handler("mcq")

    return build_completion_result(
        submission=submission,
        handler=handler,
        user_input=submission.raw_input,
        legacy_fields={},
    )


def generate_variations_helper(
    problem_id: int, user_prompt: str, user_id: int | None = None
) -> list[str]:
    """Helper function to generate code variations using repository layer."""
    # AI consent gate: block generation if user hasn't consented
    if user_id is not None:
        from django.conf import settings as django_settings

        if getattr(django_settings, "PRIVACY_ENABLE_AI_CONSENT_GATE", False):
            from django.contrib.auth.models import User

            from purplex.users_app.services.consent_service import (
                AIConsentNotGrantedError,
                ConsentService,
            )

            try:
                user = User.objects.get(id=user_id)
                ConsentService.check_ai_consent(user)
            except User.DoesNotExist:
                pass
            except AIConsentNotGrantedError:
                logger.info(
                    f"Blocking AI generation for user {user_id}: AI consent not granted"
                )
                raise Exception("AI processing consent not granted")

    # Get problem through repository
    problem = ProblemRepository.get_by_id(problem_id)
    if not problem or not problem.is_active:
        raise Exception(f"Problem {problem_id} not found or not active")

    ai_service = AITestGenerationService()
    result = ai_service.generate_eipl_variations(problem, user_prompt)

    if not result["success"]:
        raise Exception(f"AI generation failed: {result.get('error', 'Unknown error')}")

    return result.get("variations", [])


def test_variation_helper(
    code: str, problem_id: int, variation_index: int
) -> dict[str, Any]:
    """Helper function to test a single variation using repository layer."""
    # Get problem through repository
    problem = ProblemRepository.get_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")

    # Get test cases formatted for testing through service
    test_cases = TestCaseService.get_test_cases_for_testing(
        problem, include_hidden=True
    )

    # Store original test case IDs for later mapping
    test_case_ids = [tc.get("id") for tc in test_cases]

    # Parse JSON fields if needed
    for tc in test_cases:
        if isinstance(tc["inputs"], str):
            try:
                tc["inputs"] = json.loads(tc["inputs"])
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(tc["expected_output"], str):
            try:
                tc["expected_output"] = json.loads(tc["expected_output"])
            except (json.JSONDecodeError, TypeError):
                pass

    # Test the code using shared Docker service (no cleanup needed)
    with SharedDockerServiceContext() as service:
        # Set user context for async task (no user context in celery tasks)
        service.set_user_context(f"task_{variation_index}")
        result = service.test_solution(code, problem.function_name, test_cases)

    # DEBUG: Log raw Docker result to capture errors
    logger.warning(
        f"🔍 Variation {variation_index} Docker result: testsPassed={result.get('testsPassed')}, totalTests={result.get('totalTests')}, error={result.get('error', 'None')}, success={result.get('success', 'N/A')}"
    )

    testsPassed = result.get("testsPassed", 0)
    totalTests = result.get("totalTests", 0)

    # Add test case IDs to results
    results_with_ids = []
    for idx, test_result in enumerate(result.get("results", [])):
        if idx < len(test_case_ids):
            test_result["test_case_id"] = test_case_ids[idx]
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
        "variation_index": variation_index,
        "code": code,
        "testsPassed": testsPassed,
        "totalTests": totalTests,
        "success": testsPassed == totalTests and totalTests > 0,
        "test_results": results_with_ids,
    }

    # Preserve error message if present (critical for debugging!)
    if "error" in result:
        ret["error"] = result["error"]

    return ret


def segment_prompt_helper(
    user_prompt: str, problem_id: int, user_id: int | None = None
) -> dict[str, Any] | None:
    """Helper function for prompt segmentation using service layer."""
    # AI consent gate: skip segmentation if user hasn't consented
    if user_id is not None:
        from django.conf import settings

        if getattr(settings, "PRIVACY_ENABLE_AI_CONSENT_GATE", False):
            from django.contrib.auth.models import User

            from purplex.users_app.services.consent_service import (
                AIConsentNotGrantedError,
                ConsentService,
            )

            try:
                user = User.objects.get(id=user_id)
                ConsentService.check_ai_consent(user)
            except User.DoesNotExist:
                pass  # Anonymized user — allow processing
            except AIConsentNotGrantedError:
                logger.info(
                    f"Skipping segmentation for user {user_id}: AI consent not granted"
                )
                return None

    # Get problem through service
    problem = ProblemRepository.get_problem_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")

    if not problem.segmentation_enabled:
        return None

    # Build config with threshold from authoritative source (DB field takes priority)
    problem_config = (
        problem.segmentation_config.copy() if problem.segmentation_config else {}
    )
    problem_config["threshold"] = problem.get_segmentation_threshold

    # Look up user's language preference for localised AI output
    language = "en"
    if user_id is not None:
        from purplex.users_app.models import UserProfile

        try:
            profile = UserProfile.objects.get(user_id=user_id)
            language = profile.language_preference or "en"
        except UserProfile.DoesNotExist:
            pass

    service = SegmentationService()
    segmentation_result = service.segment_prompt(
        user_prompt=user_prompt,
        reference_code=problem.reference_solution,
        problem_config=problem_config,
        language=language,
    )

    # Add threshold and 'passed' field to result for frontend display
    if segmentation_result:
        threshold = problem.get_segmentation_threshold
        segment_count = segmentation_result.get("segment_count", 0)
        segmentation_result["threshold"] = threshold
        segmentation_result["passed"] = segment_count <= threshold

    return segmentation_result


def save_submission_helper(
    user_id: int,
    problem_id: int,
    problem_set_id: int,
    course_id: int | None,
    user_prompt: str,
    variations: list[str],
    test_results: list[dict],
    segmentation: dict | None,
    task_id: str | None = None,
    submission_id: str | None = None,
) -> dict[str, Any]:
    """
    Helper function to save/update the submission using new service layer.

    Args:
        user_id: ID of the user making the submission
        problem_id: Database ID of the problem
        problem_set_id: Optional problem set ID
        course_id: Optional course ID
        user_prompt: User's explanation/code input
        variations: List of code variations generated
        test_results: Test results for each variation
        segmentation: Segmentation analysis results (if applicable)
        task_id: Celery task ID for idempotency
        submission_id: UUID of existing submission to UPDATE instead of creating new
                       (CRITICAL: prevents duplicate submission bug)

    Returns:
        Complete submission result dictionary
    """
    from django.db import IntegrityError

    from purplex.submissions.models import Submission

    # Get objects through services/repositories
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise Exception(f"User {user_id} not found")
    if not user.is_active:
        raise Exception(f"User {user_id} is inactive (deletion in progress)")

    problem = ProblemRepository.get_problem_by_id(problem_id)
    if not problem:
        raise Exception(f"Problem {problem_id} not found")

    problem_set = None
    if problem_set_id:
        problem_set = ProblemRepository.get_problem_set_by_id(problem_set_id)
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
    successful_variations = sum(1 for r in test_results if r.get("success", False))
    total_variations = len(test_results)

    # Retrieve hint data from Redis context if available
    activated_hints = None
    try:
        from django.core.cache import cache

        context_data = cache.get(f"eipl:context:{task_id}")
        if context_data:
            # Django cache already deserializes the data
            activated_hints = context_data.get("activated_hints", [])
            if activated_hints:
                logger.info(
                    f"Retrieved {len(activated_hints)} activated hints from context"
                )
    except Exception as e:
        logger.warning(f"Failed to retrieve hint context: {e}")
        activated_hints = None

    # PERFORMANCE: Single atomic transaction to reduce DB overhead
    # Previously: 3 separate transactions caused ~60% extra DB load
    # IDEMPOTENCY: Handle race condition where another worker beat us to creating the submission

    # FIX: If submission_id is provided, UPDATE existing submission instead of creating new
    # This prevents the duplicate submission bug where view creates one and pipeline creates another
    if submission_id:
        try:
            submission = Submission.objects.get(submission_id=submission_id)
            logger.info(f"✅ Updating existing submission {submission_id}")
            # Update celery_task_id for tracking
            submission.celery_task_id = task_id
            submission.save(update_fields=["celery_task_id"])
        except Submission.DoesNotExist:
            logger.warning(
                f"⚠️ Submission {submission_id} not found, creating new submission"
            )
            submission_id = None  # Fall through to create new

    if not submission_id:
        # Create new submission (legacy path or when submission_id not provided)
        try:
            with transaction.atomic():
                # Create submission using _no_transaction method to avoid nested transactions
                # The outer transaction.atomic() manages the entire pipeline as one unit
                # IDEMPOTENCY: Pass celery_task_id atomically with submission creation
                # This eliminates the race window where submission exists without task_id
                submission = SubmissionService._create_submission_no_transaction(
                    user=user,
                    problem=problem,
                    raw_input=user_prompt,
                    submission_type="eipl",
                    problem_set=problem_set,
                    course=course,
                    time_spent=None,  # Could be passed from frontend in future
                    activated_hints=activated_hints,  # Now tracking hints from frontend
                    celery_task_id=task_id,  # For idempotency on task retry
                )
        except IntegrityError as e:
            # Another worker beat us - fetch and return existing submission
            if "celery_task_id" in str(e):
                logger.info(
                    f"🔄 Race condition: another worker already created submission for task {task_id}"
                )
                existing = Submission.objects.get(celery_task_id=task_id)
                # Return minimal result that signals to use cached result
                return {
                    "submission_id": str(existing.submission_id),
                    "score": existing.score,
                    "idempotent_hit": True,
                }
            raise  # Re-raise if it's not a celery_task_id uniqueness error

    with transaction.atomic():
        # Record code variations for EiPL
        variation_data = []
        for code, result in zip(variations, test_results, strict=False):
            variation_data.append(
                {
                    "code": code,
                    "tests_passed": result.get("testsPassed", 0),
                    "tests_total": result.get("totalTests", 0),
                    "score": int(
                        result.get("testsPassed", 0) / result.get("totalTests", 1) * 100
                    ),
                    "model": "gpt-4o-mini",
                }
            )

        # PERFORMANCE: Bulk create variations instead of individual creates
        # Create variation objects in memory first
        variation_objects = [
            CodeVariation(
                submission=submission,
                variation_index=idx,
                generated_code=var_data["code"],
                tests_passed=var_data.get("tests_passed", 0),
                tests_total=var_data.get("tests_total", 0),
                score=var_data.get("score", 0),
                model_used=var_data.get("model", "gpt-4o-mini"),
            )
            for idx, var_data in enumerate(variation_data)
        ]

        # Bulk create all variations in one query
        created_variations = CodeVariation.objects.bulk_create(variation_objects)

        # Mark best variation only if we have results
        if test_results and created_variations:
            best_idx = max(
                range(len(test_results)),
                key=lambda i: test_results[i].get("testsPassed", 0),
            )
            best_variation = created_variations[best_idx]
            best_variation.is_selected = True
            best_variation.save()

        # Prepare test execution data for ALL variations
        variations_with_tests = []
        for variation, result in zip(created_variations, test_results, strict=False):
            test_execution_data = []
            for test_result in result.get("test_results", []):
                test_case_id = test_result.get("test_case_id")
                if test_case_id:
                    # Get actual output - handle False and other falsy values correctly
                    actual_output = test_result.get("actual_output")
                    if actual_output is None:
                        actual_output = test_result.get("output")
                    if actual_output is None:
                        actual_output = ""

                    test_execution_data.append(
                        {
                            "test_case_id": test_case_id,
                            "passed": test_result.get("pass", False)
                            or test_result.get("isSuccessful", False),
                            "inputs": test_result.get("inputs", {}),
                            "expected": test_result.get("expected_output", ""),
                            "actual": actual_output,  # Preserve False, 0, and other falsy values
                            "error_type": (
                                "none"
                                if (
                                    test_result.get("pass", False)
                                    or test_result.get("isSuccessful", False)
                                )
                                else "wrong_output"
                            ),
                            "error_message": test_result.get("error", ""),
                        }
                    )
                else:
                    logger.warning("Skipping test result without test_case_id")
            variations_with_tests.append(
                {"variation": variation, "test_results": test_execution_data}
            )

        # Record test results using _no_transaction method (no nested transaction)
        SubmissionService._record_eipl_test_results_no_transaction(
            submission=submission, variations_with_tests=variations_with_tests
        )

        # Store the best code for reference (if we have variations)
        if created_variations:
            # If we marked a best variation, use it; otherwise use the first one
            best_variation = next(
                (v for v in created_variations if v.is_selected), created_variations[0]
            )
            submission.processed_code = best_variation.generated_code
        else:
            # No variations generated - store empty code
            submission.processed_code = ""

        submission.is_correct = submission.passed_all_tests
        submission.save()

        # Record segmentation if available (using internal method)
        if segmentation and segmentation.get("success"):
            segmentation_data = {
                "segment_count": segmentation.get("segment_count", 0),
                "comprehension_level": segmentation.get(
                    "comprehension_level", "relational"
                ),
                "segments": segmentation.get("segments", []),
                "code_mappings": segmentation.get("code_mappings", {}),
                "confidence": segmentation.get("confidence", 0.8),
                "processing_time_ms": int(
                    segmentation.get("processing_time", 0) * 1000
                ),
                "model": "gpt-4o-mini",
                "feedback": segmentation.get("feedback", ""),
                "improvements": segmentation.get("suggestions", []),
                "passed": segmentation.get("passed", False),  # Include the passed field
            }

            SubmissionService._record_segmentation_no_transaction(
                submission, segmentation_data
            )

    # Only include segmentation data if it's enabled for the problem
    result_data = {
        "submission_id": str(submission.submission_id),  # Use UUID
        "variations": variations,
        "test_results": test_results,
        "score": submission.score,
        "successful_variations": successful_variations,
        "total_variations": total_variations,
        "passing_variations": successful_variations,
        "user_prompt": user_prompt,
        "problem_slug": problem.slug,
        "user": user.username,
    }

    # Only include segmentation if enabled for this problem
    if problem.segmentation_enabled:
        result_data["segmentation"] = segmentation
    else:
        result_data["segmentation"] = None

    return result_data


@shared_task(bind=True, name="pipeline.execute_eipl")
def execute_eipl_pipeline(
    self,
    problem_id: int,
    user_prompt: str,
    user_id: int,
    problem_set_id: int | None = None,
    course_id: int | None = None,
    submission_id: str | None = None,
) -> dict[str, Any]:
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
        submission_id: UUID of existing submission created by the view
                       (CRITICAL: pass this to prevent duplicate submissions)

    Returns:
        Complete submission result
    """
    task_id = self.request.id
    logger.info(
        f"🚀 PIPELINE START: task_id={task_id}, problem_id={problem_id}, user_id={user_id}"
    )
    logger.info(
        f"📝 Pipeline context: problem_set_id={problem_set_id}, course_id={course_id}, prompt_length={len(user_prompt)}"
    )
    logger.info(f"🔧 Celery task info: retries={self.request.retries}")

    # CRITICAL: Publish initial progress immediately to confirm task is running
    publish_progress(task_id, 0, "🎬 Task received by Celery worker, initializing...")

    # CRITICAL: Allow Django ORM calls in gevent context
    # With gevent workers, Django detects greenlet as async context and blocks ORM
    # This tells Django it's safe to make synchronous database calls from this task
    import os

    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    # Ensure Django is properly initialized
    import django

    if not django.apps.apps.ready:
        logger.warning("Django apps not ready, calling setup()")
        django.setup()

    # IDEMPOTENCY CHECK - early exit if task was already processed
    # This handles retries caused by worker crashes with task_acks_late=True
    from purplex.submissions.models import Submission

    existing = Submission.objects.filter(celery_task_id=task_id).first()
    if existing:
        logger.info(
            f"🔄 Task {task_id} already processed (submission {existing.submission_id}), returning cached result"
        )
        publish_progress(
            task_id, 100, "Submission already processed (idempotent retry)"
        )
        return _build_cached_eipl_result(existing)

    # Start Sentry transaction if available
    if SENTRY_AVAILABLE:
        transaction = sentry_sdk.start_transaction(
            op="celery.task",
            name="execute_eipl_pipeline",
            description=f"Process EiPL submission for problem {problem_id}",
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
                op="ai.generate", description="Generate code variations from prompt"
            )
        else:
            span = None

        try:
            variations = generate_variations_helper(
                problem_id, user_prompt, user_id=user_id
            )
            variation_count = len(variations)
            logger.info(
                f"✅ STEP 1 COMPLETE: Generated {variation_count} variations for task {task_id}"
            )
        except Exception as gen_error:
            logger.error(
                f"❌ STEP 1 FAILED: AI generation failed for task {task_id}: {str(gen_error)}",
                exc_info=True,
            )
            raise

        if SENTRY_AVAILABLE and span:
            span.set_data("variation_count", variation_count)
            span.finish()

        # Check if we got any variations
        if variation_count == 0:
            logger.warning(f"No variations generated for problem {problem_id}")
            publish_progress(task_id, 20, "No code variations could be generated")
        else:
            publish_progress(
                task_id, 20, f"Generated {variation_count} code variations"
            )

        # Step 2: Test each variation in parallel (20-70% progress)
        # PERFORMANCE: GeventPool for parallel I/O-bound Docker operations (gevent-native, no deadlocks)
        # Previously: Sequential testing took ~15 seconds for 3 variations
        # Now: Parallel testing with greenlets takes ~0.2 seconds (99% faster!)
        logger.info(
            f"⏱️  STEP 2: Starting parallel code testing for {variation_count} variations (task {task_id})"
        )

        if SENTRY_AVAILABLE and transaction:
            test_span = transaction.start_child(
                op="code.execution",
                description="Execute and test code variations in parallel",
            )
        else:
            test_span = None

        test_results = []

        # Use GeventPool for parallel execution (gevent-native, no threading conflicts)
        # With pool of 30 containers, we can safely run all variations in parallel
        # CRITICAL: GeventPool instead of ThreadPoolExecutor prevents deadlocks with gevent workers
        max_workers = min(
            variation_count, 6
        )  # Allow up to 6 concurrent tests (pool has 30 containers)

        # Create gevent pool with automatic cleanup via context manager
        with managed_gevent_pool(max_workers) as pool:
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
                    if result["success"]:
                        publish_progress(
                            task_id,
                            test_progress,
                            f"Variation {i + 1}: ✓ Passed all tests ({completed}/{variation_count} complete)",
                        )
                    else:
                        # Include error message if present
                        error_msg = result.get("error", "")
                        if error_msg:
                            publish_progress(
                                task_id,
                                test_progress,
                                f"Variation {i + 1}: ERROR - {error_msg[:80]} ({completed}/{variation_count} complete)",
                            )
                            logger.warning(f"Variation {i + 1} failed: {error_msg}")
                        else:
                            publish_progress(
                                task_id,
                                test_progress,
                                f"Variation {i + 1}: {result['testsPassed']}/{result['totalTests']} tests passed ({completed}/{variation_count} complete)",
                            )

                except Exception as e:
                    # Enhanced error logging with full traceback
                    import traceback

                    error_details = traceback.format_exc()
                    logger.error(
                        f"❌ Variation {i + 1} testing FAILED with exception\n"
                        f"Problem ID: {problem_id}\n"
                        f"Variation Index: {i}\n"
                        f"Error: {str(e)}\n"
                        f"Traceback:\n{error_details}"
                    )

                    # Publish error to user
                    publish_progress(
                        task_id,
                        20 + (50 * completed / max(variation_count, 1)),
                        f"⚠️ Variation {i + 1}: Testing failed - {str(e)[:100]} ({completed}/{variation_count} complete)",
                    )

                    results_by_index[i] = {
                        "variation_index": i,
                        "code": variations[i],
                        "testsPassed": 0,
                        "totalTests": 0,
                        "success": False,
                        "test_results": [],
                        "error": str(e),
                        "error_traceback": error_details,
                    }

        # Pool cleanup handled by context manager

        # Reconstruct results in original order
        test_results = [results_by_index[i] for i in range(variation_count)]

        successful_variations = sum(1 for r in test_results if r.get("success", False))
        logger.info(
            f"✅ STEP 2 COMPLETE: Tested {variation_count} variations, {successful_variations} passed (task {task_id})"
        )

        if SENTRY_AVAILABLE and test_span:
            test_span.set_data("variations_tested", variation_count)
            test_span.set_data("variations_passed", successful_variations)
            test_span.set_data("parallel_workers", max_workers)
            test_span.finish()

        # Step 3: Aggregate results (70-80% progress)
        logger.info(f"⏱️  STEP 3: Aggregating results (task {task_id})")
        publish_progress(task_id, 70, "Aggregating test results...")
        score = int(
            (successful_variations / variation_count * 100)
            if variation_count > 0
            else 0
        )
        logger.info(
            f"📊 Score calculated: {score}% ({successful_variations}/{variation_count} passed)"
        )
        publish_progress(task_id, 80, f"Score calculated: {score}%")

        # Step 4: Segment prompt if enabled (80-90% progress)
        # TWO-STAGE LEARNING: Only analyze comprehension AFTER correctness is achieved
        segmentation = None

        # Check if ALL variations passed ALL tests (100% correctness gate)
        all_variations_passed = all(r.get("success", False) for r in test_results)

        if all_variations_passed:
            # Stage 2: Comprehension Analysis - student has achieved correctness
            try:
                publish_progress(
                    task_id,
                    85,
                    "✓ All variations correct! Now analyzing comprehension level...",
                )

                if SENTRY_AVAILABLE and transaction:
                    seg_span = transaction.start_child(
                        op="ai.analyze", description="Segment and analyze prompt"
                    )
                else:
                    seg_span = None

                segmentation = segment_prompt_helper(
                    user_prompt, problem_id, user_id=user_id
                )

                if SENTRY_AVAILABLE and seg_span:
                    if segmentation:
                        seg_span.set_data(
                            "segment_count", segmentation.get("segment_count", 0)
                        )
                    seg_span.finish()

                if segmentation:
                    logger.info(
                        f"Segmentation complete: {segmentation.get('segment_count', 0)} segments"
                    )
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
                f"Focus on getting a correct solution first! {successful_variations}/{variation_count} variations passed all tests.",
            )
            logger.info(
                f"Skipping segmentation - correctness gate not met: {successful_variations}/{variation_count} variations passed"
            )
            # segmentation remains None - comprehension not analyzed until correctness achieved

        # Step 5: Save submission (90-100% progress)
        logger.info(f"⏱️  STEP 5: Saving submission to database (task {task_id})")
        publish_progress(task_id, 95, "Saving submission...")

        if SENTRY_AVAILABLE and transaction:
            save_span = transaction.start_child(
                op="db.update", description="Save submission and results"
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
                task_id=task_id,
                submission_id=submission_id,  # Pass existing submission to update (no duplicates)
            )
            logger.info(
                f"✅ STEP 5 COMPLETE: Submission {submission_result['submission_id']} saved successfully (task {task_id})"
            )

            # Record submission for cooldown tracking (ProbeableSpec problems)
            problem = ProblemRepository.get_by_id(problem_id)
            if problem and problem.problem_type == "probeable_spec":
                from purplex.problems_app.services.probe_service import ProbeService

                ProbeService.record_submission(problem.id, user_id)
                logger.info(
                    f"Recorded ProbeableSpec submission for cooldown tracking (problem={problem_id}, user={user_id})"
                )
        except Exception as save_error:
            logger.error(
                f"❌ STEP 5 FAILED: Failed to save submission for task {task_id}: {str(save_error)}",
                exc_info=True,
            )
            raise

        if SENTRY_AVAILABLE and save_span:
            save_span.set_data("submission_id", submission_result.get("submission_id"))
            save_span.finish()

        publish_progress(task_id, 100, f"Submission complete! Score: {score}%")

        # Build unified completion result using handler
        from purplex.problems_app.handlers import get_handler
        from purplex.submissions.models import Submission

        handler = get_handler("eipl")
        # NOTE: 'problem' excluded from select_related for django-polymorphic to resolve subclass
        submission = Submission.objects.prefetch_related(
            "code_variations", "code_variations__test_executions"
        ).get(submission_id=submission_result["submission_id"])

        # Legacy fields for backward compatibility during migration
        legacy_fields = {
            "variations": submission_result.get("variations", []),
            "test_results": submission_result.get("test_results", []),
            "segmentation": submission_result.get("segmentation"),
            "successful_variations": submission_result.get("successful_variations", 0),
            "total_variations": submission_result.get("total_variations", 0),
            "passing_variations": submission_result.get("passing_variations", 0),
        }

        unified_result = build_completion_result(
            submission=submission,
            handler=handler,
            user_input=user_prompt,
            legacy_fields=legacy_fields,
        )

        # Publish completion event
        publish_completion(task_id, unified_result)

        # Return unified result (keep submission_result reference for logging)
        submission_result = unified_result

        # Mark transaction as successful
        if SENTRY_AVAILABLE and transaction:
            transaction.set_status("ok")
            transaction.set_data("final_score", score)
            transaction.finish()

        logger.info(
            f"🎉 PIPELINE COMPLETE: task_id={task_id}, score={score}%, submission_id={submission_result.get('submission_id')}"
        )
        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"💥 PIPELINE FAILED: task_id={task_id}, error={error_msg}\n"
            f"   Problem ID: {problem_id}, User ID: {user_id}\n"
            f"   Problem Set ID: {problem_set_id}, Course ID: {course_id}",
            exc_info=True,
        )
        publish_error(task_id, error_msg)

        # Mark transaction as failed and capture exception in Sentry
        if SENTRY_AVAILABLE:
            if transaction:
                transaction.set_status("error")
                transaction.finish()
            sentry_sdk.capture_exception(
                e,
                extras={
                    "task_id": task_id,
                    "problem_id": problem_id,
                    "user_id": user_id,
                    "problem_set_id": problem_set_id,
                    "course_id": course_id,
                    "phase": "pipeline_execution",
                },
            )

        # Re-raise to mark task as failed in Celery
        raise


# ─────────────────────────────────────────────────────────────────────────────
# MCQ Pipeline - Synchronous processing for Multiple Choice Questions
# ─────────────────────────────────────────────────────────────────────────────


@shared_task(bind=True, max_retries=1)
def execute_mcq_pipeline(
    self,
    problem_id: int,
    selected_option: str,
    user_id: int,
    problem_set_id: int | None = None,
    course_id: int | None = None,
):
    """
    Execute MCQ submission pipeline.

    MCQ processing is synchronous and simple:
    1. Load problem and user
    2. Check if selected answer matches correct answer
    3. Create submission record
    4. Update progress

    Args:
        problem_id: The Problem primary key
        selected_option: The selected option ID
        user_id: The User primary key
        problem_set_id: Optional ProblemSet primary key
        course_id: Optional Course primary key
    """
    task_id = self.request.id
    logger.info(f"🚀 MCQ PIPELINE START: task_id={task_id}, problem_id={problem_id}")

    # IDEMPOTENCY CHECK - early exit if task was already processed
    # This handles retries caused by worker crashes with task_acks_late=True
    from purplex.submissions.models import Submission

    existing = Submission.objects.filter(celery_task_id=task_id).first()
    if existing:
        logger.info(
            f"🔄 Task {task_id} already processed (submission {existing.submission_id}), returning cached result"
        )
        publish_progress(
            task_id, 100, "Submission already processed (idempotent retry)"
        )
        return _build_cached_mcq_result(existing)

    try:
        # ─── Phase 1: Load entities ─────────────────────────────────
        publish_progress(task_id, 10, "Loading problem...")

        problem = ProblemRepository.get_problem_by_id(problem_id)
        if not problem:
            raise ValueError(f"Problem not found: {problem_id}")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        problem_set = None
        if problem_set_id:
            problem_set = ProblemRepository.get_problem_set_by_id(problem_set_id)

        course = None
        if course_id:
            course = CourseService.get_course_by_id(course_id)

        publish_progress(task_id, 30, "Checking answer...")

        # ─── Phase 2: Check answer ──────────────────────────────────
        # Get the actual McqProblem instance for MCQ-specific fields
        from purplex.problems_app.models import McqProblem

        if isinstance(problem, McqProblem):
            mcq = problem
        else:
            mcq = McqProblem.objects.get(pk=problem.pk)

        mcq_options = mcq.options or []

        if not mcq_options:
            raise ValueError(f"MCQ problem {mcq.slug} has no options configured")

        # Find correct answer
        correct_option = next(
            (opt for opt in mcq_options if opt.get("is_correct", False)), None
        )

        if not correct_option:
            raise ValueError(
                f"MCQ problem {problem.slug} has no correct answer defined"
            )

        is_correct = selected_option.strip() == str(correct_option.get("id", ""))
        score = 100 if is_correct else 0

        publish_progress(task_id, 60, "Saving submission...")

        # ─── Phase 3: Create submission ─────────────────────────────
        # IDEMPOTENCY: Pass celery_task_id atomically with submission creation
        # Handle race condition where another worker beat us to creating the submission
        from django.db import IntegrityError

        from purplex.submissions.models import Submission as SubmissionModel

        try:
            with transaction.atomic():
                submission = SubmissionService.create_submission(
                    user=user,
                    problem=problem,
                    raw_input=selected_option,
                    submission_type="mcq",
                    problem_set=problem_set,
                    course=course,
                    celery_task_id=task_id,  # For idempotency on task retry
                )

                # Update submission with results
                submission.processed_code = (
                    selected_option  # For MCQ, same as raw_input
                )
                submission.score = score
                submission.passed_all_tests = is_correct
                submission.is_correct = is_correct
                submission.completion_status = (
                    "complete" if is_correct else "incomplete"
                )
                submission.execution_status = "completed"
                submission.save()

        except IntegrityError as e:
            # Another worker beat us - fetch and return existing submission
            if "celery_task_id" in str(e):
                logger.info(
                    f"🔄 Race condition: another worker already created submission for task {task_id}"
                )
                existing = SubmissionModel.objects.get(celery_task_id=task_id)
                publish_progress(
                    task_id, 100, "Submission already processed (idempotent retry)"
                )
                return _build_cached_mcq_result(existing)
            raise  # Re-raise if it's not a celery_task_id uniqueness error

        # Update progress (outside transaction — does its own atomic + Redis/network calls)
        from purplex.problems_app.services.progress_service import (
            ProgressService,
        )

        ProgressService.process_submission(submission)

        publish_progress(
            task_id, 100, f"Complete! {'Correct!' if is_correct else 'Incorrect.'}"
        )

        # ─── Phase 4: Build result using unified helper ─────────────
        from purplex.problems_app.handlers import get_handler

        handler = get_handler("mcq")

        # Legacy fields for backward compatibility during migration
        selected_opt = next(
            (
                opt
                for opt in mcq_options
                if str(opt.get("id", "")) == selected_option.strip()
            ),
            None,
        )
        legacy_fields = {
            "selected_option": {
                "id": selected_option,
                "text": selected_opt.get("text", "") if selected_opt else "",
            },
            "correct_option": {
                "id": str(correct_option.get("id", "")),
                "text": correct_option.get("text", ""),
                "explanation": correct_option.get("explanation", ""),
            },
        }

        submission_result = build_completion_result(
            submission=submission,
            handler=handler,
            user_input=selected_option,
            legacy_fields=legacy_fields,
        )

        # Publish completion
        publish_completion(task_id, submission_result)

        logger.info(
            f"🎉 MCQ PIPELINE COMPLETE: task_id={task_id}, score={score}%, correct={is_correct}"
        )
        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"💥 MCQ PIPELINE FAILED: task_id={task_id}, error={error_msg}",
            exc_info=True,
        )
        publish_error(task_id, error_msg)

        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(
                e,
                extras={
                    "task_id": task_id,
                    "problem_id": problem_id,
                    "user_id": user_id,
                },
            )

        raise


# -----------------------------------------------------------------------------
# Debug Fix Pipeline - Execute student's fixed code against test cases
# -----------------------------------------------------------------------------


def _build_cached_debug_fix_result(existing: "Submission") -> dict[str, Any]:
    """Build result from an existing debug fix submission (for idempotent retries)."""
    from purplex.problems_app.handlers import get_handler

    handler = get_handler("debug_fix")

    return {
        "submission_id": str(existing.submission_id),
        "score": existing.score,
        "is_correct": existing.passed_all_tests,
        "completion_status": existing.completion_status or "incomplete",
        "idempotent_hit": True,
        "result": handler.serialize_result(existing),
    }


@shared_task(bind=True, name="pipeline.execute_debug_fix")
def execute_debug_fix_pipeline(
    self,
    problem_id: int,
    fixed_code: str,
    user_id: int,
    problem_set_id: int | None = None,
    course_id: int | None = None,
    submission_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Debug Fix submission pipeline.

    This task executes the student's fixed code against test cases.
    Simpler than EiPL - no LLM generation, no segmentation.

    Args:
        problem_id: Database ID of the problem
        fixed_code: Student's fixed code to test
        user_id: ID of the user making the submission
        problem_set_id: Optional problem set ID
        course_id: Optional course ID
        submission_id: UUID of existing submission created by the view
                       (CRITICAL: pass this to prevent duplicate submissions)

    Returns:
        Complete submission result
    """
    task_id = self.request.id
    logger.info(
        f"DEBUG_FIX PIPELINE START: task_id={task_id}, problem_id={problem_id}, user_id={user_id}"
    )

    # Publish initial progress
    publish_progress(task_id, 0, "Task received, initializing...")

    # Allow Django ORM calls in gevent context
    import os

    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    # Ensure Django is properly initialized
    import django

    if not django.apps.apps.ready:
        logger.warning("Django apps not ready, calling setup()")
        django.setup()

    # IDEMPOTENCY CHECK
    from purplex.submissions.models import Submission

    existing = Submission.objects.filter(celery_task_id=task_id).first()
    if existing:
        logger.info(
            f"Task {task_id} already processed (submission {existing.submission_id}), returning cached result"
        )
        publish_progress(
            task_id, 100, "Submission already processed (idempotent retry)"
        )
        return _build_cached_debug_fix_result(existing)

    # Start Sentry transaction if available
    if SENTRY_AVAILABLE:
        sentry_txn = sentry_sdk.start_transaction(
            op="celery.task",
            name="execute_debug_fix_pipeline",
            description=f"Process Debug Fix submission for problem {problem_id}",
        )
        sentry_txn.set_tag("problem_id", problem_id)
        sentry_txn.set_tag("user_id", user_id)
    else:
        sentry_txn = None

    try:
        # Step 1: Load entities (0-10% progress)
        publish_progress(task_id, 5, "Loading problem and test cases...")

        problem = ProblemRepository.get_by_id(problem_id)
        if not problem:
            raise Exception(f"Problem {problem_id} not found")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise Exception(f"User {user_id} not found")

        problem_set = None
        if problem_set_id:
            problem_set = ProblemRepository.get_problem_set_by_id(problem_set_id)

        course = None
        if course_id:
            course = CourseService.get_course_by_pk(course_id)

        # Step 2: Test the fixed code (10-70% progress)
        publish_progress(task_id, 10, "Testing your code against test cases...")

        if SENTRY_AVAILABLE and sentry_txn:
            test_span = sentry_txn.start_child(
                op="code.execution", description="Execute fixed code against test cases"
            )
        else:
            test_span = None

        # Get test cases formatted for testing
        test_cases = TestCaseService.get_test_cases_for_testing(
            problem, include_hidden=True
        )
        test_case_ids = [tc.get("id") for tc in test_cases]

        # Parse JSON fields if needed
        for tc in test_cases:
            if isinstance(tc["inputs"], str):
                try:
                    tc["inputs"] = json.loads(tc["inputs"])
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(tc["expected_output"], str):
                try:
                    tc["expected_output"] = json.loads(tc["expected_output"])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Execute code in Docker
        with SharedDockerServiceContext() as service:
            service.set_user_context(f"debug_fix_{user_id}")
            result = service.test_solution(
                fixed_code, problem.function_name, test_cases
            )

        publish_progress(
            task_id,
            70,
            f"Testing complete: {result.get('testsPassed', 0)}/{result.get('totalTests', 0)} passed",
        )

        # Build test results with IDs
        tests_passed = result.get("testsPassed", 0)
        tests_total = result.get("totalTests", 0)
        all_passed = tests_passed == tests_total and tests_total > 0

        test_results_list = []
        for idx, test_result in enumerate(result.get("results", [])):
            if idx < len(test_case_ids):
                test_result["test_case_id"] = test_case_ids[idx]
            test_results_list.append(test_result)

        if SENTRY_AVAILABLE and test_span:
            test_span.set_data("tests_passed", tests_passed)
            test_span.set_data("tests_total", tests_total)
            test_span.finish()

        # Step 3: Save submission (70-100% progress)
        publish_progress(task_id, 80, "Saving submission...")

        score = int((tests_passed / tests_total * 100) if tests_total > 0 else 0)

        # Create submission
        from django.db import IntegrityError

        # FIX: If submission_id is provided, UPDATE existing submission instead of creating new
        # This prevents the duplicate submission bug where view creates one and pipeline creates another
        if submission_id:
            try:
                submission = Submission.objects.get(submission_id=submission_id)
                logger.info(f"✅ Updating existing submission {submission_id}")
                # Update celery_task_id for tracking
                submission.celery_task_id = task_id
                submission.save(update_fields=["celery_task_id"])
            except Submission.DoesNotExist:
                logger.warning(
                    f"⚠️ Submission {submission_id} not found, creating new submission"
                )
                submission_id = None  # Fall through to create new

        if not submission_id:
            # Create new submission (legacy path or when submission_id not provided)
            try:
                with transaction.atomic():
                    submission = SubmissionService._create_submission_no_transaction(
                        user=user,
                        problem=problem,
                        raw_input=fixed_code,
                        submission_type="debug_fix",
                        problem_set=problem_set,
                        course=course,
                        time_spent=None,
                        activated_hints=None,
                        celery_task_id=task_id,
                    )
            except IntegrityError as e:
                if "celery_task_id" in str(e):
                    logger.info(
                        f"Race condition: another worker already created submission for task {task_id}"
                    )
                    existing = Submission.objects.get(celery_task_id=task_id)
                    return _build_cached_debug_fix_result(existing)
                raise

        # Use regular transaction.atomic for the rest
        with transaction.atomic():
            # Create a single CodeVariation to store results (reuse EiPL structure)
            variation = CodeVariation.objects.create(
                submission=submission,
                variation_index=0,
                generated_code=fixed_code,
                tests_passed=tests_passed,
                tests_total=tests_total,
                score=score,
                model_used="student_fix",  # Not LLM-generated
                is_selected=True,
            )

            # Record test execution results
            test_execution_data = []
            for test_result in test_results_list:
                test_case_id = test_result.get("test_case_id")
                if test_case_id:
                    actual_output = test_result.get("actual_output")
                    if actual_output is None:
                        actual_output = test_result.get("output", "")

                    test_execution_data.append(
                        {
                            "test_case_id": test_case_id,
                            "passed": test_result.get("pass", False)
                            or test_result.get("isSuccessful", False),
                            "inputs": test_result.get("inputs", {}),
                            "expected": test_result.get("expected_output", ""),
                            "actual": actual_output,
                            "error_type": (
                                "none"
                                if (
                                    test_result.get("pass", False)
                                    or test_result.get("isSuccessful", False)
                                )
                                else "wrong_output"
                            ),
                            "error_message": test_result.get("error", ""),
                        }
                    )

            # Record test results
            if test_execution_data:
                # Set processed_code before service call (will be saved by service)
                submission.processed_code = fixed_code
                SubmissionService._record_eipl_test_results_no_transaction(
                    submission=submission,
                    variations_with_tests=[
                        {"variation": variation, "test_results": test_execution_data}
                    ],
                )
            else:
                # No test data edge case - update submission manually
                submission.processed_code = fixed_code
                submission.score = score
                submission.passed_all_tests = all_passed
                submission.is_correct = all_passed
                submission.execution_status = "completed"
                submission.completion_status = (
                    "complete" if all_passed else "incomplete"
                )
                submission.save()

        # Update progress (outside transaction — does its own atomic + Redis/network calls)
        if not test_execution_data:
            from purplex.problems_app.services.progress_service import (
                ProgressService,
            )

            ProgressService.process_submission(submission)

        publish_progress(task_id, 100, f"Complete! Score: {score}%")

        # Build result using unified helper
        from purplex.problems_app.handlers import get_handler

        handler = get_handler("debug_fix")

        # Reload submission with relations
        submission = Submission.objects.prefetch_related(
            "code_variations", "code_variations__test_executions"
        ).get(submission_id=submission.submission_id)

        submission_result = build_completion_result(
            submission=submission,
            handler=handler,
            user_input=fixed_code,
            legacy_fields={
                "fixed_code": fixed_code,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
            },
        )

        # Publish completion
        publish_completion(task_id, submission_result)

        if SENTRY_AVAILABLE and sentry_txn:
            sentry_txn.set_status("ok")
            sentry_txn.finish()

        logger.info(f"DEBUG_FIX PIPELINE COMPLETE: task_id={task_id}, score={score}%")
        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"DEBUG_FIX PIPELINE FAILED: task_id={task_id}, error={error_msg}",
            exc_info=True,
        )
        publish_error(task_id, error_msg)

        if SENTRY_AVAILABLE:
            if sentry_txn:
                sentry_txn.set_status("error")
                sentry_txn.finish()
            sentry_sdk.capture_exception(
                e,
                extras={
                    "task_id": task_id,
                    "problem_id": problem_id,
                    "user_id": user_id,
                },
            )

        raise


# ==============================================================================
# PROBEABLE CODE PIPELINE
# ==============================================================================


def _build_cached_probeable_code_result(existing: "Submission") -> dict[str, Any]:
    """Build result from an existing probeable code submission (for idempotent retries)."""
    from purplex.problems_app.handlers import get_handler

    handler = get_handler("probeable_code")

    return {
        "submission_id": str(existing.submission_id),
        "score": existing.score,
        "is_correct": existing.passed_all_tests,
        "completion_status": existing.completion_status or "incomplete",
        "idempotent_hit": True,
        "result": handler.serialize_result(existing),
    }


@shared_task(bind=True, name="pipeline.execute_probeable_code")
def execute_probeable_code_pipeline(
    self,
    problem_id: int,
    student_code: str,
    user_id: int,
    problem_set_id: int | None = None,
    course_id: int | None = None,
    submission_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Probeable Code submission pipeline.

    This task executes the student's implementation code against test cases.
    Similar to Debug Fix - no LLM generation, no segmentation.
    Additionally records the submission for cooldown tracking.

    Args:
        problem_id: Database ID of the problem
        student_code: Student's implementation code to test
        user_id: ID of the user making the submission
        problem_set_id: Optional problem set ID
        course_id: Optional course ID
        submission_id: UUID of existing submission created by the view
                       (CRITICAL: pass this to prevent duplicate submissions)

    Returns:
        Complete submission result
    """
    task_id = self.request.id
    logger.info(
        f"PROBEABLE_CODE PIPELINE START: task_id={task_id}, problem_id={problem_id}, user_id={user_id}"
    )

    # Publish initial progress
    publish_progress(task_id, 0, "Task received, initializing...")

    # Allow Django ORM calls in gevent context
    import os

    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    # Ensure Django is properly initialized
    import django

    if not django.apps.apps.ready:
        logger.warning("Django apps not ready, calling setup()")
        django.setup()

    # IDEMPOTENCY CHECK
    from purplex.submissions.models import Submission

    existing = Submission.objects.filter(celery_task_id=task_id).first()
    if existing:
        logger.info(
            f"Task {task_id} already processed (submission {existing.submission_id}), returning cached result"
        )
        publish_progress(
            task_id, 100, "Submission already processed (idempotent retry)"
        )
        return _build_cached_probeable_code_result(existing)

    # Start Sentry transaction if available
    if SENTRY_AVAILABLE:
        sentry_txn = sentry_sdk.start_transaction(
            op="celery.task",
            name="execute_probeable_code_pipeline",
            description=f"Process Probeable Code submission for problem {problem_id}",
        )
        sentry_txn.set_tag("problem_id", problem_id)
        sentry_txn.set_tag("user_id", user_id)
    else:
        sentry_txn = None

    try:
        # Step 1: Load entities (0-10% progress)
        publish_progress(task_id, 5, "Loading problem and test cases...")

        problem = ProblemRepository.get_by_id(problem_id)
        if not problem:
            raise Exception(f"Problem {problem_id} not found")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise Exception(f"User {user_id} not found")

        problem_set = None
        if problem_set_id:
            problem_set = ProblemRepository.get_problem_set_by_id(problem_set_id)

        course = None
        if course_id:
            course = CourseService.get_course_by_pk(course_id)

        # Step 2: Test the student's code (10-70% progress)
        publish_progress(task_id, 10, "Testing your code against test cases...")

        if SENTRY_AVAILABLE and sentry_txn:
            test_span = sentry_txn.start_child(
                op="code.execution",
                description="Execute student code against test cases",
            )
        else:
            test_span = None

        # Get test cases formatted for testing
        test_cases = TestCaseService.get_test_cases_for_testing(
            problem, include_hidden=True
        )
        test_case_ids = [tc.get("id") for tc in test_cases]

        # Parse JSON fields if needed
        for tc in test_cases:
            if isinstance(tc["inputs"], str):
                try:
                    tc["inputs"] = json.loads(tc["inputs"])
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(tc["expected_output"], str):
                try:
                    tc["expected_output"] = json.loads(tc["expected_output"])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Execute code in Docker
        with SharedDockerServiceContext() as service:
            service.set_user_context(f"probeable_code_{user_id}")
            result = service.test_solution(
                student_code, problem.function_name, test_cases
            )

        publish_progress(
            task_id,
            70,
            f"Testing complete: {result.get('testsPassed', 0)}/{result.get('totalTests', 0)} passed",
        )

        # Build test results with IDs
        tests_passed = result.get("testsPassed", 0)
        tests_total = result.get("totalTests", 0)
        all_passed = tests_passed == tests_total and tests_total > 0

        test_results_list = []
        for idx, test_result in enumerate(result.get("results", [])):
            if idx < len(test_case_ids):
                test_result["test_case_id"] = test_case_ids[idx]
            test_results_list.append(test_result)

        if SENTRY_AVAILABLE and test_span:
            test_span.set_data("tests_passed", tests_passed)
            test_span.set_data("tests_total", tests_total)
            test_span.finish()

        # Step 3: Save submission (70-100% progress)
        publish_progress(task_id, 80, "Saving submission...")

        score = int((tests_passed / tests_total * 100) if tests_total > 0 else 0)

        # Create submission
        from django.db import IntegrityError

        # FIX: If submission_id is provided, UPDATE existing submission instead of creating new
        # This prevents the duplicate submission bug where view creates one and pipeline creates another
        if submission_id:
            try:
                submission = Submission.objects.get(submission_id=submission_id)
                logger.info(f"✅ Updating existing submission {submission_id}")
                # Update celery_task_id for tracking
                submission.celery_task_id = task_id
                submission.save(update_fields=["celery_task_id"])
            except Submission.DoesNotExist:
                logger.warning(
                    f"⚠️ Submission {submission_id} not found, creating new submission"
                )
                submission_id = None  # Fall through to create new

        if not submission_id:
            # Create new submission (legacy path or when submission_id not provided)
            try:
                with transaction.atomic():
                    submission = SubmissionService._create_submission_no_transaction(
                        user=user,
                        problem=problem,
                        raw_input=student_code,
                        submission_type="probeable_code",
                        problem_set=problem_set,
                        course=course,
                        time_spent=None,
                        activated_hints=None,
                        celery_task_id=task_id,
                    )
            except IntegrityError as e:
                if "celery_task_id" in str(e):
                    logger.info(
                        f"Race condition: another worker already created submission for task {task_id}"
                    )
                    existing = Submission.objects.get(celery_task_id=task_id)
                    return _build_cached_probeable_code_result(existing)
                raise

        # Use regular transaction.atomic for the rest
        with transaction.atomic():
            # Create a single CodeVariation to store results (reuse EiPL structure)
            variation = CodeVariation.objects.create(
                submission=submission,
                variation_index=0,
                generated_code=student_code,
                tests_passed=tests_passed,
                tests_total=tests_total,
                score=score,
                model_used="student_implementation",  # Not LLM-generated
                is_selected=True,
            )

            # Record test execution results
            test_execution_data = []
            for test_result in test_results_list:
                test_case_id = test_result.get("test_case_id")
                if test_case_id:
                    actual_output = test_result.get("actual_output")
                    if actual_output is None:
                        actual_output = test_result.get("output", "")

                    test_execution_data.append(
                        {
                            "test_case_id": test_case_id,
                            "passed": test_result.get("pass", False)
                            or test_result.get("isSuccessful", False),
                            "inputs": test_result.get("inputs", {}),
                            "expected": test_result.get("expected_output", ""),
                            "actual": actual_output,
                            "error_type": (
                                "none"
                                if (
                                    test_result.get("pass", False)
                                    or test_result.get("isSuccessful", False)
                                )
                                else "wrong_output"
                            ),
                            "error_message": test_result.get("error", ""),
                        }
                    )

            # Record test results
            if test_execution_data:
                # Set processed_code before service call (will be saved by service)
                submission.processed_code = student_code
                SubmissionService._record_eipl_test_results_no_transaction(
                    submission=submission,
                    variations_with_tests=[
                        {"variation": variation, "test_results": test_execution_data}
                    ],
                )
            else:
                # No test data edge case - update submission manually
                submission.processed_code = student_code
                submission.score = score
                submission.passed_all_tests = all_passed
                submission.is_correct = all_passed
                submission.execution_status = "completed"
                submission.completion_status = (
                    "complete" if all_passed else "incomplete"
                )
                submission.save()

        # Update progress (outside transaction — does its own atomic + Redis/network calls)
        if not test_execution_data:
            from purplex.problems_app.services.progress_service import (
                ProgressService,
            )

            ProgressService.process_submission(submission)

        # Record submission for cooldown tracking (Redis call — outside transaction)
        from purplex.problems_app.services.probe_service import ProbeService

        ProbeService.record_submission(problem.id, user.id)

        publish_progress(task_id, 100, f"Complete! Score: {score}%")

        # Build result using unified helper
        from purplex.problems_app.handlers import get_handler

        handler = get_handler("probeable_code")

        # Reload submission with relations
        submission = Submission.objects.prefetch_related(
            "code_variations", "code_variations__test_executions"
        ).get(submission_id=submission.submission_id)

        submission_result = build_completion_result(
            submission=submission,
            handler=handler,
            user_input=student_code,
            legacy_fields={
                "student_code": student_code,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
            },
        )

        # Publish completion
        publish_completion(task_id, submission_result)

        if SENTRY_AVAILABLE and sentry_txn:
            sentry_txn.set_status("ok")
            sentry_txn.finish()

        logger.info(
            f"PROBEABLE_CODE PIPELINE COMPLETE: task_id={task_id}, score={score}%"
        )
        return submission_result

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"PROBEABLE_CODE PIPELINE FAILED: task_id={task_id}, error={error_msg}",
            exc_info=True,
        )
        publish_error(task_id, error_msg)

        if SENTRY_AVAILABLE:
            if sentry_txn:
                sentry_txn.set_status("error")
                sentry_txn.finish()
            sentry_sdk.capture_exception(
                e,
                extras={
                    "task_id": task_id,
                    "problem_id": problem_id,
                    "user_id": user_id,
                },
            )

        raise
