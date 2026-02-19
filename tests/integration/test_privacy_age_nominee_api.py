"""
Integration tests for age verification, nominee, and directory info endpoints.

Endpoints:
  GET/POST  /api/users/me/age-verification/
  GET/POST/DELETE /api/users/me/nominee/
  PATCH /api/users/me/directory-info/
"""

import pytest
from rest_framework import status

from purplex.users_app.models import DataPrincipalNominee
from tests.factories import AgeVerificationFactory, DataPrincipalNomineeFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# =============================================================================
# Age Verification
# =============================================================================


class TestAgeVerificationAPI:
    """Tests for GET/POST /api/users/me/age-verification/."""

    def test_get_unverified(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/age-verification/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["verified"] is False

    def test_get_verified(self, authenticated_client, user):
        AgeVerificationFactory(user=user, is_minor=False, is_child=False)
        response = authenticated_client.get("/api/users/me/age-verification/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_minor"] is False
        assert data["is_child"] is False
        assert "verified_at" in data

    def test_post_adult(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/age-verification/",
            {"date_of_birth": "1990-01-15", "is_minor": False, "is_child": False},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_minor"] is False
        assert data["is_child"] is False

    def test_post_minor(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/age-verification/",
            {"date_of_birth": "2010-06-01", "is_minor": True, "is_child": False},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_minor"] is True

    def test_post_child(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/age-verification/",
            {"date_of_birth": "2015-03-20", "is_minor": True, "is_child": True},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["is_child"] is True

    def test_update_existing_verification(self, authenticated_client, user):
        AgeVerificationFactory(user=user, is_minor=True)
        response = authenticated_client.post(
            "/api/users/me/age-verification/",
            {"is_minor": False, "is_child": False},
            format="json",
        )
        # update_or_create returns 200 on update
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_minor"] is False

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/users/me/age-verification/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Nominee (DPDPA Sec. 8(7))
# =============================================================================


class TestNomineeAPI:
    """Tests for GET/POST/DELETE /api/users/me/nominee/."""

    def test_get_no_nominee(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/nominee/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["nominee"] is None

    def test_get_existing_nominee(self, authenticated_client, user):
        DataPrincipalNomineeFactory(
            user=user,
            nominee_name="Jane Doe",
            nominee_email="jane@example.com",
            nominee_relationship="parent",
        )
        response = authenticated_client.get("/api/users/me/nominee/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nominee_name"] == "Jane Doe"
        assert data["nominee_email"] == "jane@example.com"

    def test_post_create_nominee(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/nominee/",
            {
                "nominee_name": "John Smith",
                "nominee_email": "john@example.com",
                "nominee_relationship": "spouse",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["nominee_name"] == "John Smith"

    def test_post_update_nominee(self, authenticated_client, user):
        DataPrincipalNomineeFactory(user=user, nominee_name="Old Name")
        response = authenticated_client.post(
            "/api/users/me/nominee/",
            {
                "nominee_name": "New Name",
                "nominee_email": "new@example.com",
                "nominee_relationship": "sibling",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["nominee_name"] == "New Name"

    def test_post_missing_fields(self, authenticated_client, user):
        response = authenticated_client.post(
            "/api/users/me/nominee/",
            {"nominee_name": "Incomplete"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_nominee(self, authenticated_client, user):
        DataPrincipalNomineeFactory(user=user)
        response = authenticated_client.delete("/api/users/me/nominee/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DataPrincipalNominee.objects.filter(user=user).exists()

    def test_delete_nonexistent_nominee(self, authenticated_client, user):
        response = authenticated_client.delete("/api/users/me/nominee/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/users/me/nominee/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Directory Info Opt-Out (FERPA)
# =============================================================================


class TestDirectoryInfoAPI:
    """Tests for PATCH /api/users/me/directory-info/."""

    def test_opt_out(self, authenticated_client, user):
        response = authenticated_client.patch(
            "/api/users/me/directory-info/",
            {"directory_info_visible": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["directory_info_visible"] is False

    def test_opt_back_in(self, authenticated_client, user):
        # First opt out
        authenticated_client.patch(
            "/api/users/me/directory-info/",
            {"directory_info_visible": False},
            format="json",
        )
        # Then opt back in
        response = authenticated_client.patch(
            "/api/users/me/directory-info/",
            {"directory_info_visible": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["directory_info_visible"] is True

    def test_missing_field(self, authenticated_client, user):
        response = authenticated_client.patch(
            "/api/users/me/directory-info/", {}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self, api_client):
        response = api_client.patch(
            "/api/users/me/directory-info/",
            {"directory_info_visible": False},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
