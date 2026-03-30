"""
Standardized error codes for API responses.

Every error response should include a machine-readable `code` field that the
frontend can map to translated i18n strings. The `error` field remains a
human-readable English fallback.

Usage in views:
    from purplex.utils.error_codes import error_response, ErrorCode
    return error_response("Course not found", ErrorCode.NOT_FOUND, 404)
"""

from rest_framework import status
from rest_framework.response import Response


class ErrorCode:
    """Machine-readable error codes sent in API responses.

    Frontend maps these to i18n keys: `errors.api.{code}`
    """

    # --- Generic ---
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"

    # --- Authentication ---
    NOT_AUTHENTICATED = "not_authenticated"
    INVALID_TOKEN = "invalid_token"

    # --- Course team management ---
    LAST_PRIMARY = "last_primary"
    ALREADY_INSTRUCTOR = "already_instructor"
    NOT_INSTRUCTOR = "not_instructor"
    INVALID_ROLE = "invalid_role"

    # --- Course enrollment ---
    ENROLLMENT_CLOSED = "enrollment_closed"
    ALREADY_ENROLLED = "already_enrolled"
    NOT_ENROLLED = "not_enrolled"

    # --- Problems ---
    HAS_SUBMISSIONS = "has_submissions"
    INVALID_PROBLEM_TYPE = "invalid_problem_type"
    NOT_PROBEABLE = "not_probeable"
    NOT_REFUTABLE = "not_refutable"
    INVALID_INPUT = "invalid_input"

    # --- Problem sets ---
    PROBLEM_SET_NOT_FOUND = "problem_set_not_found"
    PROBLEM_SET_NOT_IN_COURSE = "problem_set_not_in_course"

    # --- Ownership ---
    NOT_OWNER = "not_owner"

    # --- Hints ---
    HINT_LOCKED = "hint_locked"
    INSUFFICIENT_ATTEMPTS = "insufficient_attempts"

    # --- Privacy/Consent ---
    CONSENT_REQUIRED = "consent_required"
    DELETION_PENDING = "deletion_pending"

    # --- Submissions ---
    SUBMISSION_NOT_FOUND = "submission_not_found"


def error_response(
    message: str,
    code: str,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Create a standardized error response with a machine-readable code.

    Args:
        message: Human-readable error description (English fallback).
        code: Machine-readable ErrorCode constant.
        http_status: HTTP status code (default 400).

    Returns:
        DRF Response with {"error": message, "code": code}
    """
    return Response({"error": message, "code": code}, status=http_status)
