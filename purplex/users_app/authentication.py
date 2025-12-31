"""
Clean authentication system for Purplex.
Single authentication class for ALL endpoints.
"""

import logging
from typing import Any

from django.contrib.auth.models import User
from rest_framework import authentication, exceptions

from .services.authentication_service import AuthenticationService
from .services.rate_limit_service import RateLimitService

logger = logging.getLogger(__name__)


class PurplexAuthentication(authentication.BaseAuthentication):
    """
    Single authentication class for ALL endpoints.

    Handles both header and query parameter tokens (for SSE).
    All Firebase logic is delegated to AuthenticationService.
    """

    def authenticate(self, request) -> tuple[User, Any] | None:
        """
        Authenticate the request using Firebase tokens.

        Only tries header authentication. SSE uses separate session tokens.

        Args:
            request: The HTTP request object

        Returns:
            Tuple of (user, auth_data) if authentication succeeds
            None if no authentication is attempted

        Raises:
            AuthenticationFailed: If authentication fails
        """
        # Try header first
        token = self._extract_header_token(request)

        # Check for SSE session token (secure alternative to query params)
        if not token:
            sse_token = self._extract_sse_session_token(request)
            if sse_token:
                user = AuthenticationService.validate_sse_session(sse_token)
                if user:
                    return (user, {"type": "sse_session"})

        # Try service account if no user token (with rate limiting)
        if not token:
            client_ip = RateLimitService.get_client_ip(request)
            if RateLimitService.check_service_account_rate_limit(client_ip):
                service_user = self._check_service_account(request)
                if service_user:
                    return (service_user, None)
            else:
                logger.warning(f"Service account rate limit exceeded for {client_ip}")
                raise exceptions.AuthenticationFailed("Rate limit exceeded")

        # No authentication attempted
        if not token:
            return None

        # Only check if IP is blocked due to too many FAILED attempts
        client_ip = RateLimitService.get_client_ip(request)

        # Check if IP is blocked due to too many failures
        if RateLimitService.is_blocked(client_ip):
            logger.warning(f"Blocked authentication attempt from {client_ip}")
            raise exceptions.AuthenticationFailed(
                "Too many failed attempts. Please try again later."
            )

        # NOTE: We do NOT rate limit valid token validation
        # Rate limits are only for preventing brute force attacks on login
        # Users with valid tokens should be able to navigate freely

        # Authenticate the token
        try:
            user, auth_data = AuthenticationService.authenticate_token(token)
            # Reset rate limits on successful auth
            RateLimitService.reset_limits(client_ip)
            return (user, auth_data)
        except ValueError as e:
            # Record failed attempt
            RateLimitService.record_failed_auth(client_ip)
            # Log detailed error for debugging, return generic to client
            logger.warning(f"Authentication attempt failed from {client_ip}: {e}")
            # Return generic error message to prevent information disclosure
            raise exceptions.AuthenticationFailed("Authentication failed")
        except Exception as e:
            # Record failed attempt
            RateLimitService.record_failed_auth(client_ip)
            # Log unexpected errors but never expose details
            logger.error(
                f"Unexpected authentication error from {client_ip}: {type(e).__name__}"
            )
            raise exceptions.AuthenticationFailed("Authentication failed")

    def _extract_header_token(self, request) -> str | None:
        """
        Extract token from Authorization header.

        Args:
            request: The HTTP request object

        Returns:
            Token string or None
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            return None

        # Support both 'Bearer' and 'Token' prefixes
        parts = auth_header.split()
        if len(parts) != 2:
            return None

        auth_type, token = parts
        if auth_type.lower() in ["bearer", "token"]:
            return token

        return None

    def _extract_sse_session_token(self, request) -> str | None:
        """
        Extract SSE session token from request.

        Uses X-SSE-Token header or sse_token query parameter.
        Query parameter is only for EventSource API compatibility.

        Args:
            request: The HTTP request object

        Returns:
            SSE session token or None
        """
        # Try header first (preferred)
        sse_token = request.META.get("HTTP_X_SSE_TOKEN", "")
        if sse_token:
            return sse_token

        # Query parameter only as fallback for EventSource
        # This is still more secure than exposing Firebase tokens
        return request.GET.get("sse_token")

    def _check_service_account(self, request) -> User | None:
        """
        Check for service account authentication.

        Args:
            request: The HTTP request object

        Returns:
            Service User or None
        """
        service_key = request.META.get("HTTP_X_SERVICE_KEY", "")
        if service_key:
            return AuthenticationService.verify_service_account(service_key)
        return None
