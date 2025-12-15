"""Views for handling code submissions and testing."""

import logging
import uuid

from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.submissions.services import SubmissionService
from purplex.users_app.permissions import IsAuthenticated

from ..handlers import get_handler, get_registered_types, is_registered
from ..repositories import ProblemRepository
from ..services.course_service import CourseService
from ..services.progress_service import ProgressService
from ..services.submission_validation_service import SubmissionValidationService

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key="user", rate="50/m", method="POST"), name="post")
class ActivitySubmissionView(APIView):
    """
    Unified submission endpoint for all activity types.

    Delegates to handler.submit() which owns the execution model:
    - Synchronous handlers (MCQ): process inline, return immediate result
    - Asynchronous handlers (EiPL, Prompt): queue Celery task, return task_id
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="50/m", method="POST"))
    def post(self, request):
        # Check if rate limited
        if getattr(request, "limited", False):
            return Response(
                {
                    "error": "Rate limit exceeded. Please wait a moment before submitting again."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Use generic validation service
        is_valid, error_message, validated_data = (
            SubmissionValidationService.validate_submission(request.data)
        )
        if not is_valid:
            return Response(
                {"error": error_message}, status=status.HTTP_400_BAD_REQUEST
            )

        # Extract validated data
        problem = validated_data["problem"]
        problem_set = validated_data.get("problem_set")
        course = validated_data.get("course")
        raw_input = validated_data["raw_input"]
        activated_hints = request.data.get("activated_hints", [])

        # Additional validation for problem set membership
        if problem_set and not problem_set.problems.filter(id=problem.id).exists():
            return Response(
                {"error": "Problem does not belong to the specified problem set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Additional validation for course enrollment
        if course:
            enrollment_result = CourseService.validate_course_enrollment(
                request.user, course.course_id
            )
            if not enrollment_result["success"]:
                return Response(
                    {"error": enrollment_result["error"]},
                    status=enrollment_result["status_code"],
                )

        # Get handler for this problem type
        problem_type = problem.problem_type
        if not is_registered(problem_type):
            return Response(
                {"error": f"No handler registered for activity type: {problem_type}"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        handler = get_handler(problem_type)

        logger.info(
            f"Activity submission for {problem_type} problem {problem.slug} by user {request.user.username}"
        )

        # Generate request ID for tracking
        request_id = str(uuid.uuid4())

        # Store submission context in cache (for async handlers)
        from django.core.cache import cache

        submission_context = {
            "user_id": request.user.id,
            "username": request.user.username,
            "problem_id": problem.id,
            "problem_slug": problem.slug,
            "problem_type": problem_type,
            "problem_set_id": problem_set.id if problem_set else None,
            "problem_set_slug": problem_set.slug if problem_set else None,
            "course_id": course.id if course else None,
            "course_name": course.name if course else None,
            "raw_input": raw_input,
            "activated_hints": activated_hints,
            "request_id": request_id,
            "submitted_at": timezone.now().isoformat(),
        }

        cache.set(f"submission:context:{request_id}", submission_context, timeout=7200)

        try:
            # Create submission record
            submission = SubmissionService.create_submission(
                user=request.user,
                problem=problem,
                raw_input=raw_input,
                submission_type=problem_type,
                problem_set=problem_set,
                course=course,
                activated_hints=activated_hints,
            )

            # Build context for handler
            handler_context = {
                "user_id": request.user.id,
                "problem_set": problem_set,
                "problem_set_id": problem_set.id if problem_set else None,
                "course": course,
                "course_id": course.id if course else None,
                "request_id": request_id,
                "activated_hints": activated_hints,
            }

            # Delegate to handler - handler owns sync/async decision
            outcome = handler.submit(submission, raw_input, problem, handler_context)

            if outcome.complete:
                # Synchronous completion (e.g., MCQ)
                logger.info(f"✅ Sync submission complete: {submission.submission_id}")

                return Response(
                    {
                        "status": "complete",
                        "submission_id": str(submission.submission_id),
                        "problem_type": problem_type,
                        **outcome.result_data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Asynchronous processing (e.g., EiPL)
                logger.info(f"🚀 Async task queued: task_id={outcome.task_id}")

                # Store request_id in session for SSE authentication
                if not request.session.get("user_tasks"):
                    request.session["user_tasks"] = []
                request.session["user_tasks"].append(request_id)
                request.session.save()

                return Response(
                    {
                        "request_id": request_id,
                        "task_id": outcome.task_id,
                        "status": "processing",
                        "problem_type": problem_type,
                        "stream_url": f"/api/tasks/{request_id}/stream/",
                        "message": "Your submission is being processed. Connect to the stream URL for real-time updates.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

        except Exception as e:
            logger.error(
                f"❌ Submission failed for {problem_type} problem {problem.slug}: {str(e)}",
                exc_info=True,
            )
            return Response(
                {
                    "error": "Failed to process submission. Please try again.",
                    "request_id": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ActivityTypesView(APIView):
    """
    List all registered activity types with their metadata.

    Used by admin interface to populate type selector dropdowns.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        registered_types = get_registered_types()

        types_data = []
        for type_name in registered_types:
            handler = get_handler(type_name)
            types_data.append(
                {
                    "type": type_name,
                    "label": dict(ProblemRepository.get_problem_type_choices()).get(
                        type_name, type_name
                    ),
                    "has_pipeline": True,  # All registered handlers have submit()
                    "admin_config": handler.get_admin_config(),
                }
            )

        return Response({"types": types_data, "default": "eipl"})


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
                return Response(
                    {"error": "Problem not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error fetching problem {problem_slug}: {str(e)}")
            return Response(
                {"error": "Failed to fetch problem"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Get filters
        problem_set_slug = request.query_params.get("problem_set_slug")
        course_id = request.query_params.get("course_id")
        limit = request.query_params.get("limit", 50)  # Default to last 50 attempts

        try:
            limit = int(limit)
            limit = min(limit, 100)  # Cap at 100 for performance
        except (ValueError, TypeError):
            limit = 50

        # Build query filters
        filters = {"user": request.user, "problem": problem}

        # Add problem_set filter if provided - important to prevent cross-set leakage
        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return Response(
                    {"error": "Problem set not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Verify problem belongs to this problem set
            if not problem_set.problems.filter(id=problem.id).exists():
                return Response(
                    {"error": "Problem does not belong to the specified problem set"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filters["problem_set"] = problem_set

        # Add course filter if provided
        if course_id:
            # Validate course enrollment
            validation_result = CourseService.validate_course_enrollment(
                request.user, course_id
            )
            if validation_result["success"]:
                filters["course"] = validation_result["course"]
                # Also verify problem set belongs to course if both are provided
                if problem_set_slug:
                    from ..repositories import CourseRepository

                    if (
                        problem_set.id
                        not in CourseRepository.get_course_problem_set_ids(
                            validation_result["course"]
                        )
                    ):
                        return Response(
                            {"error": "Problem set does not belong to this course"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

        # Fetch submissions via repository
        from purplex.submissions.repositories import SubmissionRepository

        submissions = SubmissionRepository.get_user_submission_history(
            user=request.user,
            problem=problem,
            problem_set=filters.get("problem_set"),
            course=filters.get("course"),
            limit=limit,
        )

        # Find the best attempt
        best_score = 0
        best_attempt_id = None

        # Format submission data for frontend
        submission_history = []
        for index, submission in enumerate(submissions):
            # Get test execution summary (use prefetched data, avoid extra queries)
            test_executions = list(submission.test_executions.all())
            total_tests = len(test_executions)
            passed_tests = sum(1 for t in test_executions if t.passed)

            # Get code variations
            variations = submission.code_variations.all()

            # Track best score
            if submission.score > best_score:
                best_score = submission.score
                best_attempt_id = str(submission.submission_id)

            # Get segmentation data only if segmentation is enabled for this problem
            segmentation_data = None
            if (
                hasattr(submission, "segmentation")
                and submission.segmentation
                and submission.problem.segmentation_enabled
            ):
                seg = submission.segmentation
                segmentation_data = {
                    "segment_count": seg.segment_count,
                    "comprehension_level": seg.comprehension_level,
                    "confidence_score": seg.confidence_score,
                    "feedback_message": seg.feedback_message,
                    "suggested_improvements": seg.suggested_improvements,
                    "segments": seg.segments,
                    "code_mappings": seg.code_mappings,
                }

            submission_data = {
                "id": str(submission.submission_id),
                "attempt_number": len(submissions)
                - index,  # Reverse numbering (oldest = 1)
                "submitted_at": submission.submitted_at.isoformat(),
                "score": submission.score,
                "passed_all_tests": submission.passed_all_tests,
                "completion_status": submission.completion_status,
                "execution_status": submission.execution_status,
                "submission_type": submission.submission_type,
                "tests_passed": passed_tests,
                "total_tests": total_tests,
                "execution_time_ms": submission.execution_time_ms,
                "is_best": False,  # Will be set later
                "variations_count": variations.count(),
                "comprehension_level": (
                    submission.comprehension_level
                    if submission.submission_type == "eipl"
                    else None
                ),
                "segmentation": segmentation_data,  # Include segmentation data
                # Include the actual submission data for switching
                "data": {
                    "raw_input": submission.raw_input,
                    "processed_code": submission.processed_code,
                    "variations": [
                        {
                            "code": var.generated_code,
                            "variation_number": var.variation_index,
                            "passed_all_tests": var.score >= 100,
                            "tests_passed": var.tests_passed,
                            "total_tests": var.tests_total,
                            # Include test results for this specific variation
                            # FALLBACK: Create placeholder results if TestExecution records missing
                            "test_results": (
                                lambda var_tests: (
                                    var_tests
                                    if var_tests
                                    else (
                                        [
                                            {
                                                "test_case_id": None,
                                                "passed": i < var.tests_passed,
                                                "expected": "Test details not available",
                                                "actual": (
                                                    "Passed"
                                                    if i < var.tests_passed
                                                    else "Failed"
                                                ),
                                                "error_message": (
                                                    ""
                                                    if i < var.tests_passed
                                                    else "Test failed (details not available)"
                                                ),
                                                "inputs": {},
                                            }
                                            for i in range(var.tests_total)
                                        ]
                                        if var.tests_total > 0
                                        else []
                                    )
                                )
                            )(
                                [
                                    {
                                        "test_case_id": te.test_case_id,
                                        "passed": te.passed,
                                        "expected": te.expected_output,
                                        "actual": te.actual_output,
                                        "error_message": (
                                            te.error_message
                                            if hasattr(te, "error_message")
                                            else ""
                                        ),
                                        "inputs": te.input_values,
                                    }
                                    for te in [
                                        t
                                        for t in test_executions
                                        if t.code_variation_id == var.id
                                    ]
                                ]
                            ),
                        }
                        for var in variations
                    ],
                    # Keep test_results at top level for non-variation submissions
                    "test_results": (
                        [
                            {
                                "test_case_id": te.test_case_id,
                                "passed": te.passed,
                                "expected": te.expected_output,
                                "actual": te.actual_output,
                                "error_message": (
                                    te.error_message
                                    if hasattr(te, "error_message")
                                    else ""
                                ),
                                "inputs": te.input_values,
                            }
                            for te in test_executions
                            if not variations.exists()
                        ]
                        if not variations.exists()
                        else []
                    ),
                },
                # Handler-provided type-specific serialization
                "type_specific": (
                    get_handler(submission.submission_type).serialize_result(submission)
                    if is_registered(submission.submission_type)
                    else {}
                ),
            }

            submission_history.append(submission_data)

        # Mark the best attempt
        for submission in submission_history:
            if submission["id"] == best_attempt_id:
                submission["is_best"] = True

        # Get current progress
        progress = ProgressService.get_user_progress(
            user_id=request.user.id,
            problem_id=problem.id,
            course_id=filters.get("course").id if filters.get("course") else None,
        )

        return Response(
            {
                "problem_slug": problem_slug,
                "total_attempts": len(submission_history),
                "best_score": best_score,
                "best_attempt_id": best_attempt_id,
                "current_progress": (
                    {
                        "status": progress.status if progress else "not_started",
                        "best_score": progress.best_score if progress else 0,
                        "attempts": progress.attempts if progress else 0,
                        "is_completed": progress.is_completed if progress else False,
                    }
                    if progress
                    else None
                ),
                "submissions": submission_history,
            }
        )
