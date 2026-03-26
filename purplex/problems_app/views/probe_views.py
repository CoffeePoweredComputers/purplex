"""
Probe API views for Probeable Code problems.

These endpoints handle synchronous oracle queries (probes).
Code submission uses the standard async submission endpoint.
"""

import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.models import Problem
from purplex.problems_app.services.course_service import CourseService
from purplex.problems_app.services.probe_service import (
    ProbeService,
    parse_function_signature,
    validate_probe_input,
)

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key="user", rate="30/m", method="POST"), name="post")
class ProbeOracleView(APIView):
    """
    Synchronous endpoint for probing the oracle (reference solution).

    POST /api/problems/<slug>/probe/

    Request body:
    {
        "input": {
            "param1": value1,
            "param2": value2,
            ...
        },
        "course_id": "optional-course-id"
    }

    Response:
    {
        "success": true/false,
        "result": <oracle output>,
        "error": null or "error message",
        "probe_status": {
            "mode": "block"|"cooldown"|"explore",
            "remaining": int or null,
            "used": int,
            "can_probe": bool,
            "message": "human-readable status"
        }
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug: str) -> Response:
        """Execute a probe query against the oracle."""
        # Check rate limit
        if getattr(request, "limited", False):
            return Response(
                {
                    "error": "Rate limit exceeded. Please wait a moment before probing again.",
                    "success": False,
                    "result": None,
                    "probe_status": None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Get problem
        try:
            problem = Problem.objects.get(slug=slug)
        except Problem.DoesNotExist:
            return Response(
                {
                    "error": f"Problem not found: {slug}",
                    "success": False,
                    "result": None,
                    "probe_status": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify this is a probeable_code or probeable_spec problem
        if problem.problem_type not in ("probeable_code", "probeable_spec"):
            return Response(
                {
                    "error": f"Problem type {problem.problem_type} does not support probing",
                    "success": False,
                    "result": None,
                    "probe_status": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional course validation
        course_id = request.data.get("course_id")
        if course_id:
            enrollment_result = CourseService.validate_course_enrollment(
                request.user, course_id
            )
            if not enrollment_result["success"]:
                return Response(
                    {
                        "error": enrollment_result["error"],
                        "success": False,
                        "result": None,
                        "probe_status": None,
                    },
                    status=enrollment_result["status_code"],
                )

        # Validate probe input
        probe_input = request.data.get("input", {})
        if not isinstance(probe_input, dict):
            return Response(
                {
                    "error": "Probe input must be an object mapping parameter names to values",
                    "success": False,
                    "result": None,
                    "probe_status": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate against function signature
        is_valid, error_msg = validate_probe_input(
            problem.function_signature, probe_input
        )
        if not is_valid:
            return Response(
                {
                    "error": error_msg,
                    "success": False,
                    "result": None,
                    "probe_status": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute probe
        logger.info(
            f"Probe request: problem={slug}, user={request.user.username}, "
            f"input={probe_input}"
        )

        result = ProbeService.execute_probe(
            problem=problem, user_id=request.user.id, probe_input=probe_input
        )

        # Record durable activity event (fire-and-forget)
        from purplex.submissions.activity_event_service import ActivityEventService

        ActivityEventService.record_best_effort(
            user=request.user,
            event_type="probe.execute",
            payload={
                "input": probe_input,
                "output": result.get("result"),
                "success": result["success"],
                "probe_mode": result.get("probe_status", {}).get("mode"),
                "probes_remaining": result.get("probe_status", {}).get("remaining"),
                "course_id": course_id,
            },
            problem=problem,
        )

        return Response(result, status=status.HTTP_200_OK)


class ProbeStatusView(APIView):
    """
    Get current probe status without executing a probe.

    GET /api/problems/<slug>/probe/status/

    Response:
    {
        "mode": "block"|"cooldown"|"explore",
        "remaining": int or null,
        "used": int,
        "can_probe": bool,
        "message": "human-readable status",
        "function_signature": "f(x: int, y: str) -> bool" or null,
        "function_name": "function_name",
        "parameters": [{"name": "x", "type": "int"}, ...]
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, slug: str) -> Response:
        """Get probe status for the current user."""
        # Get problem
        try:
            problem = Problem.objects.get(slug=slug)
        except Problem.DoesNotExist:
            return Response(
                {"error": f"Problem not found: {slug}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify this is a probeable_code or probeable_spec problem
        if problem.problem_type not in ("probeable_code", "probeable_spec"):
            return Response(
                {
                    "error": f"Problem type {problem.problem_type} does not support probing"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get probe status
        probe_status = ProbeService.get_probe_status(
            problem=problem, user_id=request.user.id
        )

        # Add function info
        show_signature = getattr(problem, "show_function_signature", True)

        if show_signature:
            probe_status["function_signature"] = problem.function_signature
            probe_status["parameters"] = parse_function_signature(
                problem.function_signature
            )
        else:
            probe_status["function_signature"] = None
            probe_status["parameters"] = []

        probe_status["function_name"] = problem.function_name

        return Response(probe_status, status=status.HTTP_200_OK)


class ProbeHistoryView(APIView):
    """
    Get user's probe history for a problem.

    GET /api/problems/<slug>/probe/history/

    Query params:
    - limit: Maximum entries to return (default 50, max 100)

    Response:
    {
        "history": [
            {
                "input": {"x": 5, "y": "hello"},
                "output": 10,
                "timestamp": "2024-01-15T10:30:00Z"
            },
            ...
        ],
        "probe_status": {...}
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, slug: str) -> Response:
        """Get probe history for the current user."""
        # Get problem
        try:
            problem = Problem.objects.get(slug=slug)
        except Problem.DoesNotExist:
            return Response(
                {"error": f"Problem not found: {slug}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify this is a probeable_code or probeable_spec problem
        if problem.problem_type not in ("probeable_code", "probeable_spec"):
            return Response(
                {
                    "error": f"Problem type {problem.problem_type} does not support probing"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get limit from query params
        try:
            limit = min(int(request.query_params.get("limit", 50)), 100)
        except (ValueError, TypeError):
            limit = 50

        # Get history
        history = ProbeService.get_probe_history(
            problem_id=problem.id, user_id=request.user.id, limit=limit
        )

        # Get current status
        probe_status = ProbeService.get_probe_status(
            problem=problem, user_id=request.user.id
        )

        return Response(
            {"history": history, "probe_status": probe_status},
            status=status.HTTP_200_OK,
        )


@method_decorator(ratelimit(key="user", rate="60/m", method="POST"), name="post")
class RefuteTestView(APIView):
    """
    Test counterexample input for Refute problems.

    POST /api/problems/<slug>/test-counterexample/

    Request body:
    {
        "input": {
            "param1": value1,
            "param2": value2,
            ...
        }
    }

    Response:
    {
        "success": true/false,
        "result": <function output>,
        "claim_disproven": true/false,
        "error": null or "error message"
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug: str) -> Response:
        """Test if input disproves the claim."""
        # Check rate limit
        if getattr(request, "limited", False):
            return Response(
                {
                    "error": "Rate limit exceeded. Please wait before testing again.",
                    "success": False,
                    "result": None,
                    "claim_disproven": False,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Get problem
        try:
            problem = Problem.objects.get(slug=slug)
        except Problem.DoesNotExist:
            return Response(
                {
                    "error": f"Problem not found: {slug}",
                    "success": False,
                    "result": None,
                    "claim_disproven": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify this is a refute problem
        if problem.problem_type != "refute":
            return Response(
                {
                    "error": f"Problem type {problem.problem_type} does not support counterexample testing",
                    "success": False,
                    "result": None,
                    "claim_disproven": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate input
        test_input = request.data.get("input", {})
        if not isinstance(test_input, dict):
            return Response(
                {
                    "error": "Input must be an object mapping parameter names to values",
                    "success": False,
                    "result": None,
                    "claim_disproven": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate against function signature
        is_valid, error_msg = validate_probe_input(
            problem.function_signature, test_input
        )
        if not is_valid:
            return Response(
                {
                    "error": error_msg,
                    "success": False,
                    "result": None,
                    "claim_disproven": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get handler and execute test
        handler = get_handler(problem.problem_type)
        result = handler.test_counterexample(problem, test_input)

        logger.info(
            f"Refute test: problem={slug}, user={request.user.username}, "
            f"input={test_input}, result={result.get('result')}, "
            f"disproven={result.get('claim_disproven')}"
        )

        # Record durable activity event for counterexample trial
        from purplex.submissions.activity_event_service import ActivityEventService

        ActivityEventService.record_best_effort(
            user=request.user,
            event_type="refute.attempt",
            payload={
                "input": test_input,
                "output": result.get("result"),
                "claim_disproven": result.get("claim_disproven", False),
                "success": result.get("success", False),
            },
            problem=problem,
        )

        return Response(result, status=status.HTTP_200_OK)
