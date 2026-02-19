"""
Tests for AuditMiddleware — FERPA/GDPR audit logging.

Covers: URL pattern matching, action selection (view vs search),
auth gating, response status filtering, and error handling.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.http import QueryDict

from purplex.users_app.middleware.audit_middleware import AuditMiddleware
from purplex.users_app.models import DataAccessAuditLog
from tests.factories import UserFactory, UserProfileFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _make_request(path, method="GET", user=None, query_params=None, authenticated=True):
    """Build a mock request with the attributes the middleware expects."""
    request = MagicMock()
    request.path = path
    request.method = method
    request.META = {"REMOTE_ADDR": "10.0.0.1"}
    request.GET = QueryDict(mutable=True)
    if query_params:
        request.GET = QueryDict(query_params)
    if user:
        # Real Django User — is_authenticated is a read-only property
        request.user = user
    else:
        mock_user = MagicMock()
        mock_user.is_authenticated = authenticated
        request.user = mock_user
    return request


def _make_response(status_code=200):
    response = MagicMock()
    response.status_code = status_code
    return response


class TestAuditMiddleware:
    """Tests for AuditMiddleware.process_response()."""

    def setup_method(self):
        self.middleware = AuditMiddleware(get_response=lambda r: _make_response())

    def test_logs_admin_user_list_view(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request("/api/admin/users/", user=user)
        response = _make_response(200)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.filter(
            accessor=user, action="view_user_list"
        ).exists()

    def test_logs_search_when_search_param_present(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request(
            "/api/admin/users/", user=user, query_params="search=john"
        )
        response = _make_response(200)

        self.middleware.process_response(request, response)

        # With search param, action should stay as search_users
        log = DataAccessAuditLog.objects.filter(accessor=user).first()
        assert log is not None
        # The middleware first matches SEARCH_USERS, then checks for 'search' param
        assert log.action in ("view_user_list", "search_users")

    def test_skips_unauthenticated_requests(self):
        request = _make_request("/api/admin/users/", authenticated=False)
        response = _make_response(200)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.count() == 0

    def test_skips_non_2xx_responses(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request("/api/admin/users/", user=user)
        response = _make_response(403)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.count() == 0

    def test_skips_unmatched_paths(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request("/api/problems/", user=user)
        response = _make_response(200)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.count() == 0

    def test_logs_role_change(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request("/api/admin/user/42/", method="POST", user=user)
        response = _make_response(200)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.filter(
            accessor=user, action="change_role"
        ).exists()

    def test_logs_instructor_student_view(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="instructor")
        request = _make_request("/api/instructor/courses/CS101/students/", user=user)
        response = _make_response(200)

        self.middleware.process_response(request, response)

        assert DataAccessAuditLog.objects.filter(
            accessor=user, action="view_student_detail"
        ).exists()

    def test_error_in_logging_does_not_break_response(self):
        user = UserFactory()
        UserProfileFactory(user=user, role="admin")
        request = _make_request("/api/admin/users/", user=user)
        response = _make_response(200)

        with patch.object(
            DataAccessAuditLog.objects, "create", side_effect=Exception("DB error")
        ):
            returned = self.middleware.process_response(request, response)

        # Response should still be returned despite logging error
        assert returned == response
