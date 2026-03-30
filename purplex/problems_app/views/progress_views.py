"""Views for tracking user progress on problems and problem sets."""

import logging

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.users_app.permissions import IsAuthenticated
from purplex.utils.error_codes import ErrorCode, error_response

from ..models import CourseProblemSet
from ..services.progress_service import ProgressService

logger = logging.getLogger(__name__)


class UserProgressView(APIView):
    """Get user's progress for a specific problem or all problems."""

    permission_classes = [IsAuthenticated]

    def get(self, request, problem_slug=None):
        import logging

        logger = logging.getLogger(__name__)

        user = request.user
        logger.info(
            f"[DEBUG-VIEW] UserProgressView.get - User: {user.username}, Problem slug: {problem_slug}"
        )

        if problem_slug:
            # Get optional context parameters from query params
            query_params = getattr(request, "query_params", request.GET)
            problem_set_slug = query_params.get("problem_set_slug")
            course_id = query_params.get("course_id")

            # Use service layer for specific problem progress
            try:
                # If problem_set_slug is provided, get progress for that specific context
                if problem_set_slug:
                    # Use service layer to get progress context
                    context = ProgressService.get_progress_context(
                        user_id=user.id,
                        problem_slug=problem_slug,
                        problem_set_slug=problem_set_slug,
                        course_id=course_id,
                    )
                    problem = context["problem"]
                    progress = context["progress"]
                    if progress:
                        progress_data = {
                            "problem_slug": problem.slug,
                            "status": progress.status,
                            "best_score": progress.best_score,
                            "attempts": progress.attempts,
                            "is_completed": progress.is_completed,
                            "completion_percentage": progress.completion_percentage,
                            "last_attempt": progress.last_attempt,
                            "completed_at": progress.completed_at,
                            "grade": getattr(
                                progress, "grade", None
                            ),  # New grade field
                        }
                        logger.info(
                            f"[DEBUG-VIEW] Returning progress data: is_completed={progress_data['is_completed']}, status={progress_data['status']}, best_score={progress_data['best_score']}"
                        )
                    else:
                        # Return default values for this context
                        progress_data = {
                            "problem_slug": problem.slug,
                            "status": "not_started",
                            "best_score": 0,
                            "attempts": 0,
                            "is_completed": False,
                            "completion_percentage": 0,
                            "last_attempt": None,
                            "completed_at": None,
                            "grade": "incomplete",  # Default grade
                        }
                    return Response(progress_data)
                else:
                    # No context provided, return overall progress for the problem
                    progress_data = ProgressService.get_problem_progress(
                        user_id=user.id, problem_slug=problem_slug
                    )
                    return Response(progress_data)
            except ValueError as e:
                return error_response(str(e), ErrorCode.NOT_FOUND, 404)
        else:
            # Use service layer for all progress
            progress_data = ProgressService.get_all_user_progress(user.id)
            return Response(progress_data)


class ProblemSetProgressView(APIView):
    """Get user's progress for a problem set."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        user = request.user

        # Get course_id from query params if provided
        # Handle both DRF and Django requests
        query_params = getattr(request, "query_params", request.GET)
        course_id = query_params.get("course_id")

        try:
            # Use service layer to get problem set progress with full context
            progress_data = ProgressService.get_problem_set_progress_with_context(
                user=user, problem_set_slug=slug, course_id=course_id
            )

            problem_set = progress_data["problem_set"]
            set_progress = progress_data["progress"]
            problems_with_progress = progress_data["problems_with_progress"]

            # Use service to format problems progress data
            problems_progress = ProgressService.format_problems_progress(
                problems_with_progress
            )

            # Build response data
            response_data = {
                "problem_set": {
                    "slug": problem_set.slug,
                    "title": problem_set.title,
                    "total_problems": set_progress.total_problems,
                    "completed_problems": set_progress.completed_problems,
                    "in_progress_problems": set_progress.in_progress_problems,
                    "completion_percentage": set_progress.completion_percentage,
                    "is_completed": set_progress.is_completed,
                    "average_score": set_progress.average_score,
                    "last_activity": set_progress.last_activity,
                },
                "problems_progress": problems_progress,
            }

            # Include deadline info if course context is provided
            if course_id:
                cps = CourseProblemSet.objects.filter(
                    course__course_id=course_id, problem_set=problem_set
                ).first()
                if cps and cps.due_date:
                    now = timezone.now()
                    is_past_due = now > cps.due_date
                    response_data["deadline"] = {
                        "due_date": cps.due_date.isoformat(),
                        "deadline_type": cps.deadline_type,
                        "is_past_due": is_past_due,
                        "is_locked": is_past_due and cps.deadline_type == "hard",
                    }

            return Response(response_data)
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return error_response(error_msg, ErrorCode.NOT_FOUND, 404)
            return error_response(error_msg, ErrorCode.VALIDATION_ERROR, 400)
        except Exception as e:
            logger.error(f"Error getting problem set progress: {str(e)}")
            return error_response(
                "Error retrieving problem set progress",
                ErrorCode.SERVER_ERROR,
                500,
            )


class LastSubmissionView(APIView):
    """Get user's last submission for a specific problem with problem set context."""

    permission_classes = [IsAuthenticated]

    def get(self, request, problem_slug):
        user = request.user

        # Get context parameters from query params
        query_params = getattr(request, "query_params", request.GET)
        problem_set_slug = query_params.get("problem_set_slug")
        course_id = query_params.get("course_id")

        # Use service layer to get last submission with context
        submission_context = ProgressService.get_last_submission_with_context(
            user=user,
            problem_slug=problem_slug,
            problem_set_slug=problem_set_slug,
            course_id=course_id,
        )

        problem = submission_context["problem"]
        submission = submission_context["submission"]

        # Check if problem was found
        if problem is None:
            return error_response(
                f"Problem {problem_slug} not found", ErrorCode.NOT_FOUND, 404
            )

        # Check if problem_set was specified but not found
        if problem_set_slug and submission_context.get("problem_set") is None:
            return error_response(
                f"Problem set {problem_set_slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        if submission:
            # Use service methods to extract clean data
            return Response(
                {
                    "has_submission": True,
                    "submission_id": str(submission.submission_id),
                    "variations": ProgressService._extract_variations(submission),
                    "results": ProgressService._extract_test_results(
                        submission, problem
                    ),
                    "passing_variations": ProgressService._calculate_passing_variations(
                        submission
                    ),
                    "total_variations": ProgressService._count_variations(submission),
                    "user_prompt": submission.raw_input,
                    "feedback": "",  # Legacy field, kept empty
                    "segmentation": ProgressService._extract_segmentation(submission),
                    "segmentation_passed": ProgressService._check_segmentation_passed(
                        submission
                    ),
                    "score": submission.score,
                    "submitted_at": submission.submitted_at,
                    "grade": (
                        getattr(submission, "grade", None)
                        if hasattr(submission, "grade")
                        else None
                    ),  # New grade field
                }
            )
        else:
            # No submission found for this context
            return Response(
                {
                    "has_submission": False,
                    "variations": [],
                    "results": [],
                    "passing_variations": 0,
                    "total_variations": 0,
                    "user_prompt": "",
                    "feedback": "",
                    "segmentation": None,
                    "segmentation_passed": None,
                    "score": 0,
                    "submitted_at": None,
                }
            )
