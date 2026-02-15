"""
Management command for enforcing data retention policies.

Run via cron or Celery Beat:
    python manage.py cleanup_expired_data

Handles:
- Hard deletion of accounts past the grace period (GDPR Art. 17)
- Cleanup of expired progress snapshots (GDPR Art. 5(1)(e))
- Warning emails for inactive accounts
- Audit log rotation
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from purplex.users_app.models import DataAccessAuditLog
from purplex.users_app.services.data_deletion_service import DataDeletionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Enforce data retention policies and process pending deletions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        retention = getattr(settings, "DATA_RETENTION", {})

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made"))

        # 1. Process accounts pending hard deletion
        self._process_pending_deletions(dry_run)

        # 2. Warn inactive accounts
        self._warn_inactive_accounts(retention, dry_run)

        # 3. Clean up old audit logs
        self._cleanup_audit_logs(retention, dry_run)

        # 4. Clean up old progress snapshots
        self._cleanup_progress_snapshots(retention, dry_run)

        self.stdout.write(self.style.SUCCESS("Retention cleanup completed"))

    def _process_pending_deletions(self, dry_run: bool):
        """Hard-delete accounts whose grace period has expired."""
        pending = DataDeletionService.get_accounts_pending_deletion()
        count = pending.count()

        if count == 0:
            self.stdout.write("No accounts pending deletion")
            return

        self.stdout.write(f"Processing {count} account(s) for hard deletion")

        for profile in pending:
            user = profile.user
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would delete user {user.username} "
                    f"(requested {profile.deletion_requested_at})"
                )
            else:
                try:
                    result = DataDeletionService.execute_hard_deletion(user)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Deleted user {user.username}: {result['stats']}"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to delete user {user.username}: {e}"
                        )
                    )

    def _warn_inactive_accounts(self, retention: dict, dry_run: bool):
        """Identify accounts inactive for 12+ months and flag them."""
        warning_months = retention.get("INACTIVE_ACCOUNT_WARNING_MONTHS", 12)
        cutoff = timezone.now() - timedelta(days=warning_months * 30)

        inactive_users = User.objects.filter(
            last_login__lt=cutoff,
            is_active=True,
        ).exclude(
            profile__deletion_requested_at__isnull=False,
        )

        count = inactive_users.count()
        if count > 0:
            self.stdout.write(
                f"Found {count} inactive account(s) (no login in {warning_months} months)"
            )
            if not dry_run:
                # In production, this would send warning emails
                logger.info(
                    f"Inactive accounts requiring notification: "
                    f"{list(inactive_users.values_list('username', flat=True)[:20])}"
                )

    def _cleanup_audit_logs(self, retention: dict, dry_run: bool):
        """Remove audit logs older than retention period."""
        retention_years = retention.get("AUDIT_LOG_RETENTION_YEARS", 7)
        cutoff = timezone.now() - timedelta(days=retention_years * 365)

        old_logs = DataAccessAuditLog.objects.filter(timestamp__lt=cutoff)
        count = old_logs.count()

        if count > 0:
            self.stdout.write(
                f"Cleaning up {count} audit log(s) older than {retention_years} years"
            )
            if not dry_run:
                old_logs.delete()
        else:
            self.stdout.write("No expired audit logs")

    def _cleanup_progress_snapshots(self, retention: dict, dry_run: bool):
        """Remove progress snapshots older than retention period."""
        retention_years = retention.get("PROGRESS_SNAPSHOTS_YEARS", 2)
        cutoff = timezone.now() - timedelta(days=retention_years * 365)

        from purplex.problems_app.models import ProgressSnapshot

        old_snapshots = ProgressSnapshot.objects.filter(snapshot_date__lt=cutoff)
        count = old_snapshots.count()

        if count > 0:
            self.stdout.write(
                f"Cleaning up {count} progress snapshot(s) older than {retention_years} years"
            )
            if not dry_run:
                old_snapshots.delete()
        else:
            self.stdout.write("No expired progress snapshots")
