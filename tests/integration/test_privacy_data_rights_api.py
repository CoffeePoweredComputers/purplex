"""
Integration tests for data rights API endpoints.

Endpoints:
  GET    /api/users/me/data-export/
  DELETE /api/users/me/delete/
  POST   /api/users/me/cancel-deletion/
"""

import pytest
from rest_framework import status

from purplex.users_app.models import DataAccessAuditLog
from tests.factories import UserConsentFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


class TestDataExportAPI:
    """Tests for GET /api/users/me/data-export/."""

    def test_export_unauthenticated(self, api_client):
        response = api_client.get("/api/users/me/data-export/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_export_returns_user_data(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/data-export/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["export_version"] == "1.0"
        assert data["user_id"] == user.id
        assert "profile" in data
        assert "submissions" in data
        assert "consent_history" in data

    def test_export_creates_audit_log(self, authenticated_client, user):
        authenticated_client.get("/api/users/me/data-export/")
        assert DataAccessAuditLog.objects.filter(
            accessor=user, action="data_export"
        ).exists()

    def test_export_includes_consent_history(self, authenticated_client, user):
        UserConsentFactory(user=user, consent_type="privacy_policy")
        response = authenticated_client.get("/api/users/me/data-export/")
        data = response.json()
        assert len(data["consent_history"]) >= 1


class TestAccountDeletionAPI:
    """Tests for DELETE /api/users/me/delete/ and POST /cancel-deletion/."""

    def test_deletion_unauthenticated(self, api_client):
        response = api_client.delete("/api/users/me/delete/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_deletion(self, authenticated_client, user):
        response = authenticated_client.delete("/api/users/me/delete/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "deletion_scheduled"
        assert "deletion_requested_at" in data
        assert "deletion_scheduled_at" in data

    def test_duplicate_deletion_request(self, authenticated_client, user):
        authenticated_client.delete("/api/users/me/delete/")
        response = authenticated_client.delete("/api/users/me/delete/")
        data = response.json()
        assert data["status"] == "already_requested"

    def test_cancel_deletion(self, authenticated_client, user):
        authenticated_client.delete("/api/users/me/delete/")
        response = authenticated_client.post("/api/users/me/cancel-deletion/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "deletion_cancelled"

    def test_cancel_without_pending(self, authenticated_client, user):
        response = authenticated_client.post("/api/users/me/cancel-deletion/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "no_pending_deletion"

    def test_deletion_creates_audit_log(self, authenticated_client, user):
        authenticated_client.delete("/api/users/me/delete/")
        assert DataAccessAuditLog.objects.filter(
            accessor=user, action="delete_user"
        ).exists()
