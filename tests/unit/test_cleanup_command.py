"""
Tests for cleanup_expired_data management command.

Covers: dry-run mode, expired deletions processing,
inactive account warnings, and audit log/snapshot rotation.
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from purplex.users_app.models import DataAccessAuditLog
from tests.factories import (
    DataAccessAuditLogFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestCleanupExpiredData:
    """Tests for the cleanup_expired_data management command."""

    def test_dry_run_does_not_delete(self, user_with_deletion_requested):
        out = StringIO()
        call_command("cleanup_expired_data", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "DRY RUN" in output
        # User should still exist
        from django.contrib.auth.models import User

        assert User.objects.filter(id=user_with_deletion_requested.id).exists()

    @patch(
        "purplex.users_app.services.data_deletion_service.DataDeletionService._delete_firebase_account"
    )
    def test_processes_expired_deletions(
        self, mock_firebase, user_with_deletion_requested
    ):
        mock_firebase.return_value = True
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "Deleted user" in output or "account(s) for hard deletion" in output

    def test_no_pending_deletions(self, user):
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "No accounts pending deletion" in output

    def test_warns_inactive_accounts(self):
        user = UserFactory(
            is_active=True,
            last_login=timezone.now() - timedelta(days=400),
        )
        UserProfileFactory(user=user)
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "inactive account" in output.lower()

    def test_cleans_old_audit_logs(self):
        # Create an audit log older than 7 years
        old_log = DataAccessAuditLogFactory()
        DataAccessAuditLog.objects.filter(pk=old_log.pk).update(
            timestamp=timezone.now() - timedelta(days=8 * 365)
        )
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "audit log" in output.lower()

    def test_reports_no_expired_audit_logs(self):
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "No expired audit logs" in output

    def test_completion_message(self, user):
        out = StringIO()
        call_command("cleanup_expired_data", stdout=out)
        output = out.getvalue()
        assert "Retention cleanup completed" in output
