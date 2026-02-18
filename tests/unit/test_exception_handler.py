"""
Tests for the custom DRF exception handler.

Strategy: call the handler function directly with synthetic exceptions
and a minimal DRF context. No views, no URL routing, no HTTP client.

DRF handler signature: handler(exc, context) -> Response | None
Our handler returns JSON for all exceptions — including a 500 catch-all
that logs for Sentry via LoggingIntegration.
"""

from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ValidationError,
)
from rest_framework.exceptions import (
    PermissionDenied as DRFPermissionDenied,
)

from purplex.utils.exception_handler import custom_exception_handler

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def handler_context():
    """Minimal DRF context dict — the handler only uses it for logging."""
    return {"view": None, "request": None}


class TestExceptionHandlerMapping:
    """Verify that each exception type maps to the correct status and body shape."""

    # -- Django exceptions that DRF ignores --

    def test_object_does_not_exist_returns_404(self, handler_context):
        response = custom_exception_handler(
            ObjectDoesNotExist("not found"), handler_context
        )
        assert response is not None
        assert response.status_code == 404
        assert response.data == {"error": "not found"}

    def test_django_permission_denied_returns_403(self, handler_context):
        """DRF's default handler already converts Django's PermissionDenied."""
        response = custom_exception_handler(
            DjangoPermissionDenied("nope"), handler_context
        )
        assert response is not None
        assert response.status_code == 403
        assert "error" in response.data

    def test_http404_returns_404(self, handler_context):
        response = custom_exception_handler(
            Http404("Problem not found"), handler_context
        )
        assert response is not None
        assert response.status_code == 404
        assert response.data == {"error": "Problem not found"}

    def test_http404_empty_message_gets_default(self, handler_context):
        response = custom_exception_handler(Http404(), handler_context)
        assert response is not None
        assert response.status_code == 404
        assert response.data == {"error": "Not found."}

    # -- DRF exceptions (delegated, then normalized) --

    def test_drf_permission_denied_returns_403(self, handler_context):
        response = custom_exception_handler(
            DRFPermissionDenied("forbidden"), handler_context
        )
        assert response is not None
        assert response.status_code == 403
        assert response.data == {"error": "forbidden"}

    def test_not_authenticated_returns_401(self, handler_context):
        response = custom_exception_handler(NotAuthenticated(), handler_context)
        assert response is not None
        assert response.status_code == 401
        assert "error" in response.data

    def test_drf_not_found_returns_404(self, handler_context):
        response = custom_exception_handler(NotFound("gone"), handler_context)
        assert response is not None
        assert response.status_code == 404
        assert response.data == {"error": "gone"}

    def test_validation_error_preserves_field_errors(self, handler_context):
        exc = ValidationError({"title": ["required"]})
        response = custom_exception_handler(exc, handler_context)
        assert response is not None
        assert response.status_code == 400
        assert response.data == {"error": {"title": ["required"]}}

    def test_validation_error_string_returns_400(self, handler_context):
        response = custom_exception_handler(ValidationError("invalid"), handler_context)
        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data

    def test_method_not_allowed_returns_405(self, handler_context):
        response = custom_exception_handler(MethodNotAllowed("POST"), handler_context)
        assert response is not None
        assert response.status_code == 405
        assert "error" in response.data

    # -- Unknown exceptions: catch-all JSON 500 --

    def test_unhandled_exception_returns_500(self, handler_context):
        """Unknown exceptions return JSON 500 instead of letting Django serve HTML."""
        response = custom_exception_handler(RuntimeError("boom"), handler_context)
        assert response is not None
        assert response.status_code == 500
        assert response.data == {"error": "An unexpected error occurred."}

    def test_value_error_returns_500(self, handler_context):
        """ValueError is not special — could be a bug, not user input."""
        response = custom_exception_handler(ValueError("bad"), handler_context)
        assert response is not None
        assert response.status_code == 500
        assert response.data == {"error": "An unexpected error occurred."}

    def test_unhandled_exception_logs_with_exc_info(self, handler_context):
        """Catch-all logs with exc_info=True so Sentry's LoggingIntegration captures it."""
        exc = RuntimeError("boom")
        with patch("purplex.utils.exception_handler.logger") as mock_logger:
            custom_exception_handler(exc, handler_context)
            mock_logger.error.assert_called_once()
            _, kwargs = mock_logger.error.call_args
            assert kwargs.get("exc_info") is True


class TestExceptionHandlerWiring:
    """Verify the handler is properly registered in Django settings."""

    def test_handler_registered_in_settings(self):
        handler_path = settings.REST_FRAMEWORK.get("EXCEPTION_HANDLER")
        assert (
            handler_path == "purplex.utils.exception_handler.custom_exception_handler"
        )
