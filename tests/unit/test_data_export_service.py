"""
Tests for DataExportService — GDPR Art. 15/20 (Data Portability).

Covers: profile export, consent history inclusion, age verification,
nominee data, and overall export structure.
"""

import pytest

from purplex.users_app.models import ConsentType
from purplex.users_app.services.data_export_service import DataExportService
from tests.factories import (
    AgeVerificationFactory,
    DataPrincipalNomineeFactory,
    UserConsentFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestExportUserData:
    """Tests for DataExportService.export_user_data()."""

    def test_export_contains_required_keys(self, user):
        data = DataExportService.export_user_data(user)
        assert data["export_version"] == "1.0"
        assert data["user_id"] == user.id
        assert "profile" in data
        assert "submissions" in data
        assert "progress" in data
        assert "enrollments" in data
        assert "consent_history" in data

    def test_export_profile_contains_user_info(self, user):
        data = DataExportService.export_user_data(user)
        profile = data["profile"]
        assert profile["username"] == user.username
        assert profile["email"] == user.email
        assert "role" in profile
        assert "language_preference" in profile
        assert "directory_info_visible" in profile

    def test_export_includes_consent_history(self, user):
        UserConsentFactory(user=user, consent_type=ConsentType.PRIVACY_POLICY)
        UserConsentFactory(user=user, consent_type=ConsentType.AI_PROCESSING)
        data = DataExportService.export_user_data(user)
        assert len(data["consent_history"]) == 2

    def test_export_includes_age_verification_when_present(self, user):
        AgeVerificationFactory(user=user, is_minor=False, is_child=False)
        data = DataExportService.export_user_data(user)
        assert "age_verification" in data
        assert data["age_verification"]["is_minor"] is False
        assert data["age_verification"]["is_child"] is False

    def test_export_excludes_age_verification_when_absent(self, user):
        data = DataExportService.export_user_data(user)
        assert "age_verification" not in data

    def test_export_includes_nominee_when_present(self, user):
        DataPrincipalNomineeFactory(
            user=user,
            nominee_name="Jane Doe",
            nominee_email="jane@example.com",
            nominee_relationship="parent",
        )
        data = DataExportService.export_user_data(user)
        assert "data_nominee" in data
        assert data["data_nominee"]["nominee_name"] == "Jane Doe"

    def test_export_excludes_nominee_when_absent(self, user):
        data = DataExportService.export_user_data(user)
        assert "data_nominee" not in data

    def test_export_profile_without_profile_object(self):
        """User without a UserProfile should still export basic fields."""
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="barebones", password="test123")
        data = DataExportService.export_user_data(user)
        assert data["profile"]["username"] == "barebones"
        # Should not have role/language since no profile
        assert "role" not in data["profile"]
