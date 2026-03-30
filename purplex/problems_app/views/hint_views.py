"""Views for managing and accessing problem hints."""

import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.users_app.permissions import IsAdmin, IsAuthenticated
from purplex.utils.error_codes import ErrorCode, error_response

from ..services.course_service import CourseService
from ..services.hint_display_service import HintDisplayService
from ..services.hint_service import AdminHintService, HintService

logger = logging.getLogger(__name__)


class ProblemHintAvailabilityView(APIView):
    """Get hint availability for a problem based on user's attempts."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        user = request.user

        # Get optional course context parameters
        query_params = getattr(request, "query_params", request.GET)
        course_id = query_params.get("course_id")
        problem_set_slug = query_params.get("problem_set_slug")

        # Validate course enrollment if provided
        if course_id:
            validation_result = CourseService.validate_course_enrollment(
                user, course_id
            )
            if not validation_result["success"]:
                status_code = validation_result["status_code"]
                code = (
                    ErrorCode.NOT_FOUND
                    if status_code == 404
                    else ErrorCode.FORBIDDEN
                    if status_code == 403
                    else ErrorCode.VALIDATION_ERROR
                )
                return Response(
                    {
                        "error": validation_result["error"],
                        "code": code,
                    },
                    status=status_code,
                )

        # Use service layer for hint availability
        availability_data = HintService.get_hint_availability(
            user=user,
            problem_slug=slug,
            course_id=course_id,
            problem_set_slug=problem_set_slug,
        )

        # Use HintDisplayService to format hints for display
        available_hints = HintDisplayService.format_available_hints(
            availability_data.get("hints", [])
        )

        # Get hints the user has already used
        hints_used = HintService.get_used_hints(
            user=user,
            problem_slug=slug,
            course_id=course_id,
            problem_set_slug=problem_set_slug,
        )

        return Response(
            {
                "available_hints": available_hints,
                "hints_used": hints_used,
                "current_attempts": availability_data.get("user_attempts", 0),
            }
        )


class ProblemHintDetailView(APIView):
    """Get specific hint content for a problem."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug, hint_type):
        user = request.user

        # Get optional course context parameters
        query_params = getattr(request, "query_params", request.GET)
        course_id = query_params.get("course_id")
        problem_set_slug = query_params.get("problem_set_slug")

        # Use service layer to get hint content
        hint_data = HintService.get_hint_content(
            user=user,
            problem_slug=slug,
            hint_type=hint_type,
            course_id=course_id,
            problem_set_slug=problem_set_slug,
        )

        # Handle different error types from service
        if "error" in hint_data:
            error_type = hint_data["error"]
            message = hint_data.get("message", "An error occurred")

            if error_type == "not_found":
                return error_response(message, ErrorCode.NOT_FOUND, 404)
            elif error_type == "invalid_type":
                return error_response(message, ErrorCode.VALIDATION_ERROR, 400)
            elif error_type == "invalid_context":
                return error_response(message, ErrorCode.VALIDATION_ERROR, 400)
            elif error_type == "forbidden":
                return error_response(message, ErrorCode.HINT_LOCKED, 403)
            elif error_type == "disabled":
                return error_response(message, ErrorCode.HINT_LOCKED, 403)
            elif error_type == "insufficient_attempts":
                return error_response(message, ErrorCode.INSUFFICIENT_ATTEMPTS, 403)
            else:
                return error_response(message, ErrorCode.SERVER_ERROR, 500)

        # Record durable activity event for hint delivery
        from purplex.submissions.activity_event_service import ActivityEventService

        ActivityEventService.record_best_effort(
            user=request.user,
            event_type="hint.view",
            payload={
                "hint_type": hint_type,
                "problem_slug": slug,
                "course_id": course_id,
                "min_attempts": hint_data.get("min_attempts"),
            },
        )

        # Return successful response
        return Response(hint_data)


class AdminProblemHintView(APIView):
    """Admin endpoint to manage hints for a problem."""

    permission_classes = [IsAdmin]

    def get(self, request, slug):
        """Get all hint configurations for a problem"""
        try:
            # Use service layer to get hint configurations
            hint_configs = AdminHintService.get_problem_hints_config(slug)
            return Response(hint_configs)
        except ValueError as e:
            return error_response(str(e), ErrorCode.NOT_FOUND, 404)

    def put(self, request, slug):
        """Bulk update all hint types for a problem"""
        # Expect data in format:
        # {
        #   "hints": [
        #     {
        #       "type": "variable_fade",
        #       "is_enabled": true,
        #       "min_attempts": 3,
        #       "content": {...}
        #     },
        #     ...
        #   ]
        # }

        hints_data = request.data.get("hints", [])

        try:
            # Use service layer to bulk update hints
            result = AdminHintService.bulk_update_hints(slug, hints_data)
            return Response(result)
        except ValueError as e:
            return error_response(str(e), ErrorCode.VALIDATION_ERROR, 400)
        except RuntimeError as e:
            logger.error(f"Failed to update hints for problem {slug}: {str(e)}")
            return error_response(str(e), ErrorCode.SERVER_ERROR, 500)
