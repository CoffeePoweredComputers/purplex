"""
Audit middleware for logging admin/instructor access to user data.

Required by:
- FERPA: Disclosure records for educational records access
- GDPR Art. 30: Records of processing activities
- GDPR Art. 32: Security measures (access logging)
"""

import logging
import re

from django.utils.deprecation import MiddlewareMixin

from ..models import AuditAction, DataAccessAuditLog
from ..utils.request_helpers import get_client_ip

logger = logging.getLogger(__name__)

# URL patterns that trigger audit logging
AUDITED_PATTERNS = [
    (re.compile(r"^/api/admin/users/?$"), "GET", AuditAction.VIEW_USER_LIST),
    (re.compile(r"^/api/admin/users/?$"), "GET", AuditAction.SEARCH_USERS),
    (re.compile(r"^/api/admin/user/\d+/?$"), "POST", AuditAction.CHANGE_ROLE),
    (
        re.compile(r"^/api/instructor/courses/.+/students/?$"),
        "GET",
        AuditAction.VIEW_STUDENT_DETAIL,
    ),
    (
        re.compile(r"^/api/instructor/courses/.+/submissions/?$"),
        "GET",
        AuditAction.VIEW_SUBMISSIONS,
    ),
    (
        re.compile(r"^/api/admin/courses/.+/submissions/?$"),
        "GET",
        AuditAction.VIEW_SUBMISSIONS,
    ),
]


class AuditMiddleware(MiddlewareMixin):
    """
    Logs admin and instructor access to endpoints that expose user data.

    Only logs successful (2xx) responses to avoid polluting the audit log
    with failed authentication attempts.
    """

    def process_response(self, request, response):
        # Only log successful responses from authenticated users
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if response.status_code < 200 or response.status_code >= 300:
            return response

        path = request.path
        method = request.method

        for pattern, expected_method, action in AUDITED_PATTERNS:
            if method == expected_method and pattern.match(path):
                self._log_access(request, action)
                break

        return response

    def _log_access(self, request, action):
        """Create an audit log entry."""
        try:
            ip = get_client_ip(request)
            query_params = dict(request.GET) if request.GET else {}

            # For search actions, record the search query
            if action == AuditAction.SEARCH_USERS:
                if not query_params.get("search"):
                    # Not a search, it's just a view
                    action = AuditAction.VIEW_USER_LIST

            DataAccessAuditLog.objects.create(
                accessor=request.user,
                action=action,
                query_parameters=query_params,
                ip_address=ip,
            )
        except Exception as e:
            # Audit logging should never break the request
            logger.error(f"Failed to create audit log: {e}")
