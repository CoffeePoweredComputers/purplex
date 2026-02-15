"""
Tests for DataDeletionService — GDPR Art. 17 (Right to Erasure).

Covers: request, cancel, hard delete (with mocked Firebase),
idempotent re-request, and pending deletion query.
"""

from unittest.mock import MagicMock, patch

import pytest

from purplex.users_app.models import (
    AgeVerification,
    DataAccessAuditLog,
    DataPrincipalNominee,
    UserConsent,
)
from purplex.users_app.services.data_deletion_service import DataDeletionService
from tests.factories import (
    AgeVerificationFactory,
    DataPrincipalNomineeFactory,
    UserConsentFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestRequestDeletion:
    """Tests for DataDeletionService.request_deletion()."""

    def test_request_deactivates_user(self, user):
        result = DataDeletionService.request_deletion(user)
        user.refresh_from_db()
        assert user.is_active is False
        assert result["status"] == "deletion_scheduled"

    def test_request_sets_timestamps(self, user):
        result = DataDeletionService.request_deletion(user)
        profile = user.profile
        profile.refresh_from_db()
        assert profile.deletion_requested_at is not None
        assert profile.deletion_scheduled_at is not None
        assert "deletion_requested_at" in result
        assert "deletion_scheduled_at" in result

    def test_request_uses_grace_period(self, user):
        result = DataDeletionService.request_deletion(user)
        assert result["grace_period_days"] == 30

    def test_duplicate_request_returns_already_requested(self, user):
        DataDeletionService.request_deletion(user)
        result = DataDeletionService.request_deletion(user)
        assert result["status"] == "already_requested"

    def test_request_raises_for_user_without_profile(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="noprofile", password="test123")
        with pytest.raises(ValueError, match="no profile"):
            DataDeletionService.request_deletion(user)

    @patch("purplex.users_app.services.data_deletion_service.settings")
    def test_respects_custom_grace_period(self, mock_settings, user):
        mock_settings.DATA_RETENTION = {"DELETION_GRACE_PERIOD_DAYS": 7}
        result = DataDeletionService.request_deletion(user)
        assert result["grace_period_days"] == 7


class TestCancelDeletion:
    """Tests for DataDeletionService.cancel_deletion()."""

    def test_cancel_reactivates_user(self, user):
        DataDeletionService.request_deletion(user)
        result = DataDeletionService.cancel_deletion(user)
        user.refresh_from_db()
        assert user.is_active is True
        assert result["status"] == "deletion_cancelled"

    def test_cancel_clears_timestamps(self, user):
        DataDeletionService.request_deletion(user)
        DataDeletionService.cancel_deletion(user)
        profile = user.profile
        profile.refresh_from_db()
        assert profile.deletion_requested_at is None
        assert profile.deletion_scheduled_at is None

    def test_cancel_with_no_pending_deletion(self, user):
        result = DataDeletionService.cancel_deletion(user)
        assert result["status"] == "no_pending_deletion"

    def test_cancel_for_user_without_profile(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="noprofile2", password="test123")
        result = DataDeletionService.cancel_deletion(user)
        assert result["status"] == "no_pending_deletion"


class TestExecuteHardDeletion:
    """Tests for DataDeletionService.execute_hard_deletion()."""

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_removes_user(self, mock_firebase, user):
        mock_firebase.return_value = True
        user_id = user.id
        result = DataDeletionService.execute_hard_deletion(user)
        assert result["status"] == "deleted"
        assert result["user_id"] == user_id
        from django.contrib.auth.models import User

        assert not User.objects.filter(id=user_id).exists()

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_preserves_consent_records_with_null_user(self, mock_firebase, user):
        """Consent records use SET_NULL — preserved for GDPR Art. 7 audit trail."""
        mock_firebase.return_value = True
        user_id = user.id
        UserConsentFactory(user=user)
        UserConsentFactory(user=user, consent_type="ai_processing")
        DataDeletionService.execute_hard_deletion(user)
        # Records preserved but user FK set to NULL
        assert UserConsent.objects.filter(user_id=user_id).count() == 0
        # The records still exist with user=None (orphaned for audit trail)
        assert UserConsent.objects.filter(user__isnull=True).count() >= 2

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_removes_age_verification(self, mock_firebase, user):
        mock_firebase.return_value = True
        AgeVerificationFactory(user=user)
        DataDeletionService.execute_hard_deletion(user)
        assert not AgeVerification.objects.filter(user_id=user.id).exists()

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_removes_nominee(self, mock_firebase, user):
        mock_firebase.return_value = True
        DataPrincipalNomineeFactory(user=user)
        DataDeletionService.execute_hard_deletion(user)
        assert not DataPrincipalNominee.objects.filter(user_id=user.id).exists()

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_creates_audit_log(self, mock_firebase, user):
        mock_firebase.return_value = True
        user_id = user.id
        DataDeletionService.execute_hard_deletion(user)
        audit = DataAccessAuditLog.objects.filter(
            action="delete_user", target_user_ids__contains=[user_id]
        )
        assert audit.exists()

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_hard_delete_returns_stats(self, mock_firebase, user):
        mock_firebase.return_value = True
        result = DataDeletionService.execute_hard_deletion(user)
        stats = result["stats"]
        assert "user_deleted" in stats
        assert stats["user_deleted"] is True


class TestDeleteFirebaseAccount:
    """Tests for DataDeletionService._delete_firebase_account()."""

    def test_returns_false_when_no_profile(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="noprofile3", password="test123")
        assert DataDeletionService._delete_firebase_account(user) is False

    @patch("purplex.users_app.utils.firebase.get_firebase_service")
    def test_returns_true_on_success(self, mock_get_firebase, user):
        mock_service = MagicMock()
        mock_get_firebase.return_value = mock_service
        assert DataDeletionService._delete_firebase_account(user) is True
        mock_service.delete_user.assert_called_once_with(user.profile.firebase_uid)

    @patch("purplex.users_app.utils.firebase.get_firebase_service")
    def test_returns_false_on_firebase_error(self, mock_get_firebase, user):
        mock_service = MagicMock()
        mock_service.delete_user.side_effect = Exception("Firebase error")
        mock_get_firebase.return_value = mock_service
        assert DataDeletionService._delete_firebase_account(user) is False


class TestGetAccountsPendingDeletion:
    """Tests for DataDeletionService.get_accounts_pending_deletion()."""

    def test_returns_expired_accounts(self, user_with_deletion_requested):
        pending = DataDeletionService.get_accounts_pending_deletion()
        user_ids = [p.user.id for p in pending]
        assert user_with_deletion_requested.id in user_ids

    def test_excludes_active_accounts(self, user):
        # user is active — should not be in pending
        pending = DataDeletionService.get_accounts_pending_deletion()
        user_ids = [p.user.id for p in pending]
        assert user.id not in user_ids
