"""
Activity event API views for frontend event recording.

Provides a POST endpoint for the Vue frontend to record activity events
(hint tracking, session start/end) directly to the ActivityEvent model.
"""

import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.problems_app.repositories.course_repository import CourseRepository
from purplex.problems_app.repositories.problem_repository import ProblemRepository
from purplex.submissions.activity_event_service import ActivityEventService
from purplex.users_app.models import ConsentType
from purplex.users_app.services.consent_service import ConsentService
from purplex.utils.error_codes import ErrorCode, error_response

logger = logging.getLogger(__name__)


def _resolve_problem(slug):
    """Resolve a problem slug to a Problem instance, or None."""
    if not slug:
        return None
    return ProblemRepository.get_problem_by_slug(slug)


def _resolve_course(course_id):
    """Resolve a course_id string to a Course instance, or None."""
    if not course_id:
        return None
    return CourseRepository.get_course_by_id(course_id)


@method_decorator(ratelimit(key="user", rate="60/m", method="POST"), name="post")
class ActivityEventCreateView(APIView):
    """
    Record a single activity event from the frontend.

    POST /api/activity-events/

    Request body:
    {
        "event_type": "hint.track",           // required
        "payload": {"hint_type": "structural"}, // optional
        "problem_slug": "two-sum",            // optional
        "course_id": "CS101-F24",             // optional
        "idempotency_key": "uuid-here"        // optional
    }

    Returns:
        201: {"id": <int>, "event_type": "<str>"}
        400: Invalid input (missing/invalid event_type)
        403: Consent required (session.* events need BEHAVIORAL_TRACKING)
        429: Rate limit exceeded
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Rate limit check
        if getattr(request, "limited", False):
            return error_response("Rate limit exceeded", ErrorCode.RATE_LIMITED, 429)

        event_type = request.data.get("event_type")
        if not event_type:
            return error_response(
                "event_type is required", ErrorCode.VALIDATION_ERROR, 400
            )

        # Consent gate for behavioral events (session.*)
        prefix = event_type.split(".")[0] if "." in event_type else ""
        if prefix == "session":
            if not ConsentService.has_active_consent(
                request.user, ConsentType.BEHAVIORAL_TRACKING
            ):
                return error_response(
                    "Behavioral tracking consent required",
                    ErrorCode.CONSENT_REQUIRED,
                    403,
                )

        # Resolve optional FK references
        problem = _resolve_problem(request.data.get("problem_slug"))
        course = _resolve_course(request.data.get("course_id"))

        payload = request.data.get("payload", {})
        idempotency_key = request.data.get("idempotency_key")

        try:
            event = ActivityEventService.record(
                user=request.user,
                event_type=event_type,
                payload=payload,
                problem=problem,
                course=course,
                idempotency_key=idempotency_key,
            )
        except ValueError as e:
            return error_response(str(e), ErrorCode.VALIDATION_ERROR, 400)

        return Response(
            {"id": event.id, "event_type": event.event_type},
            status=status.HTTP_201_CREATED,
        )
