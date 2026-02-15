"""
Integration tests for consent management API endpoints.

Endpoints:
  GET  /api/users/me/consents/
  POST /api/users/me/consents/
  DELETE /api/users/me/consents/<consent_type>/
"""

import pytest
from rest_framework import status

from purplex.users_app.models import ConsentType
from tests.factories import UserConsentFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestConsentListAPI:
    """Tests for GET/POST /api/users/me/consents/."""

    def test_get_consents_unauthenticated(self, api_client):
        response = api_client.get("/api/users/me/consents/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_consents_returns_all_types(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/consents/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for ct, _label in ConsentType.choices:
            assert ct in data

    def test_get_consents_shows_granted_status(self, authenticated_client, user):
        UserConsentFactory(user=user, consent_type=ConsentType.AI_PROCESSING)
        response = authenticated_client.get("/api/users/me/consents/")
        data = response.json()
        assert data[ConsentType.AI_PROCESSING]["granted"] is True

    def test_post_grant_consent(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/consents/",
            {"consent_type": ConsentType.AI_PROCESSING},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["consent_type"] == ConsentType.AI_PROCESSING
        assert data["granted"] is True

    def test_post_missing_consent_type(self, authenticated_client):
        response = authenticated_client.post(
            "/api/users/me/consents/", {}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_invalid_consent_type(self, authenticated_client):
        response = authenticated_client.post(
            "/api/users/me/consents/",
            {"consent_type": "invalid_type"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestConsentWithdrawAPI:
    """Tests for DELETE /api/users/me/consents/<consent_type>/."""

    def test_withdraw_consent(self, authenticated_client, user):
        UserConsentFactory(user=user, consent_type=ConsentType.AI_PROCESSING)
        response = authenticated_client.delete(
            f"/api/users/me/consents/{ConsentType.AI_PROCESSING}/"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["granted"] is False
        assert data["withdrawn_at"] is not None

    def test_withdraw_invalid_consent_type(self, authenticated_client):
        response = authenticated_client.delete("/api/users/me/consents/invalid_type/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_withdraw_unauthenticated(self, api_client):
        response = api_client.delete(
            f"/api/users/me/consents/{ConsentType.AI_PROCESSING}/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
