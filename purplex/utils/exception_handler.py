"""
Custom DRF exception handler that normalizes all error responses to {"error": ...}.

Wraps DRF's default handler, then catches known Django exceptions that DRF ignores
(Http404, ObjectDoesNotExist). Unknown exceptions are logged (picked up by Sentry's
LoggingIntegration in production) and return a JSON 500 response.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Let DRF handle its own exceptions first (ValidationError, NotAuthenticated, etc.)
    response = drf_default_handler(exc, context)

    if response is not None:
        # Normalize DRF's {"detail": ...} to {"error": ...}
        if isinstance(response.data, dict) and "detail" in response.data:
            response.data = {"error": response.data["detail"]}
        else:
            # ValidationError produces {"field": ["errors"]} or ["errors"] — wrap it
            response.data = {"error": response.data}
        return response

    # DRF didn't handle it — map known Django exceptions
    if isinstance(exc, Http404):
        return Response(
            {"error": str(exc) or "Not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {"error": str(exc) or "Not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Note: Django's PermissionDenied is already handled by DRF's default handler
    # (converted to DRF PermissionDenied), so no manual mapping needed here.

    # Unknown exception: log for Sentry (via LoggingIntegration) and return JSON 500.
    # Without this catch-all, DRF re-raises and Django returns HTML — not JSON.
    logger.error(
        "Unhandled exception in %s: %s", context.get("view"), exc, exc_info=True
    )
    return Response(
        {"error": "An unexpected error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
