"""Integration tests for user profile and auth API endpoints.

Validates the HTTP contract for user info, language preferences,
and SSE token management.
"""

import pytest
from rest_framework import status

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from inline dicts in user_views.py and frontend types
# ---------------------------------------------------------------------------

# UserRoleView authenticated response (user_views.py:47-55)
# Frontend UserMeResponse (store/auth.module.ts:156-160) expects:
#   role, is_admin, language_preference
# Backend returns more fields — test the superset
USER_ME_FIELDS = {
    "authenticated",
    "username",
    "email",
    "role",
    "is_admin",
    "language_preference",
}

# SSETokenView POST response (user_views.py)
SSE_TOKEN_FIELDS = {"sse_token", "expires_in"}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def user_me_url():
    return "/api/user/me/"


def language_url():
    return "/api/user/me/language/"


def sse_token_url():
    return "/api/auth/sse-token/"


# ===========================================================================
# TestUserRole
# ===========================================================================
class TestUserRole:
    """GET /api/user/me/"""

    def test_authenticated_success(self, authenticated_client, user):
        resp = authenticated_client.get(user_me_url())
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["authenticated"] is True
        assert resp.data["username"] == user.username

    def test_response_shape(self, authenticated_client):
        resp = authenticated_client.get(user_me_url())
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == USER_ME_FIELDS

    def test_unauthenticated_returns_auth_error(self, api_client):
        """Unauthenticated request should be rejected.

        The view intends to return 401 with {authenticated: False} (user_views.py:34-38),
        but DRF middleware may intercept first and return 403. Either way, the request
        should not succeed.
        """
        resp = api_client.get(user_me_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_has_admin_role(self, admin_client):
        resp = admin_client.get(user_me_url())
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["role"] == "admin"
        assert resp.data["is_admin"] is True

    def test_instructor_has_instructor_role(self, instructor_client):
        resp = instructor_client.get(user_me_url())
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["role"] == "instructor"


# ===========================================================================
# TestLanguagePreference
# ===========================================================================
class TestLanguagePreference:
    """PATCH /api/user/me/language/"""

    def test_update_language_success(self, authenticated_client):
        resp = authenticated_client.patch(
            language_url(), {"language_preference": "es"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["language_preference"] == "es"

    def test_update_invalid_language_400(self, authenticated_client):
        resp = authenticated_client.patch(
            language_url(), {"language_preference": "xx"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_unauthenticated(self, api_client):
        resp = api_client.patch(
            language_url(), {"language_preference": "es"}, format="json"
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestSSEToken
# ===========================================================================
class TestSSEToken:
    """POST/DELETE /api/auth/sse-token/"""

    def test_create_token_success(self, authenticated_client):
        resp = authenticated_client.post(sse_token_url())
        assert resp.status_code == status.HTTP_200_OK

    def test_create_token_response_shape(self, authenticated_client):
        resp = authenticated_client.post(sse_token_url())
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == SSE_TOKEN_FIELDS
        assert isinstance(resp.data["sse_token"], str)
        assert len(resp.data["sse_token"]) > 0
        assert resp.data["expires_in"] > 0

    def test_revoke_token_success(self, authenticated_client):
        # First create a token
        create_resp = authenticated_client.post(sse_token_url())
        assert create_resp.status_code == status.HTTP_200_OK
        token = create_resp.data["sse_token"]

        # Then revoke it
        resp = authenticated_client.delete(
            sse_token_url(), {"sse_token": token}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_revoke_nonexistent_token_404(self, authenticated_client):
        resp = authenticated_client.delete(
            sse_token_url(), {"sse_token": "nonexistent-token"}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_create_token_unauthenticated(self, api_client):
        resp = api_client.post(sse_token_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
