"""
Account deletion service for GDPR Art. 17 (Right to Erasure).

Two-phase deletion:
1. Soft delete: Set user.is_active=False, schedule hard delete after grace period.
2. Hard delete: Anonymize retained research data, delete PII, delete accounts.

Records linked via SET_NULL (Submissions, UserProgress) are preserved for
research/analytics but de-identified. Records linked via CASCADE auto-delete.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


class DataDeletionService:
    """Service for handling user account deletion with data anonymization."""

    GRACE_PERIOD_DAYS = 30  # Overridable via settings

    @classmethod
    def _get_grace_period(cls) -> int:
        return getattr(
            settings,
            "DATA_RETENTION",
            {},
        ).get("DELETION_GRACE_PERIOD_DAYS", cls.GRACE_PERIOD_DAYS)

    @classmethod
    def request_deletion(cls, user: User) -> dict:
        """
        Phase 1: Soft delete — deactivate account and schedule hard deletion.
        User can cancel during the grace period.
        """
        profile = getattr(user, "profile", None)
        if not profile:
            raise ValueError("User has no profile")

        if profile.deletion_requested_at is not None:
            return {
                "status": "already_requested",
                "deletion_requested_at": profile.deletion_requested_at.isoformat(),
                "deletion_scheduled_at": profile.deletion_scheduled_at.isoformat(),
            }

        grace_days = cls._get_grace_period()
        now = timezone.now()
        scheduled_at = now + timedelta(days=grace_days)

        # Soft delete
        user.is_active = False
        user.save(update_fields=["is_active"])

        profile.deletion_requested_at = now
        profile.deletion_scheduled_at = scheduled_at
        profile.save(update_fields=["deletion_requested_at", "deletion_scheduled_at"])

        logger.info(
            f"Deletion requested for user {user.username} "
            f"(scheduled for {scheduled_at.isoformat()})"
        )

        return {
            "status": "deletion_scheduled",
            "deletion_requested_at": now.isoformat(),
            "deletion_scheduled_at": scheduled_at.isoformat(),
            "grace_period_days": grace_days,
        }

    @classmethod
    def cancel_deletion(cls, user: User) -> dict:
        """
        Cancel a pending deletion during the grace period.
        Re-activates the user account.
        """
        profile = getattr(user, "profile", None)
        if not profile or profile.deletion_requested_at is None:
            return {"status": "no_pending_deletion"}

        user.is_active = True
        user.save(update_fields=["is_active"])

        profile.deletion_requested_at = None
        profile.deletion_scheduled_at = None
        profile.save(update_fields=["deletion_requested_at", "deletion_scheduled_at"])

        logger.info(f"Deletion cancelled for user {user.username}")
        return {"status": "deletion_cancelled"}

    @classmethod
    def execute_hard_deletion(cls, user: User) -> dict:
        """
        Phase 2: Hard delete — anonymize retained data and delete user.

        This is called by the cleanup management command after the grace period.
        It can also be called directly for immediate deletion (admin action).

        Deletion order matters for referential integrity:
        1. Anonymize submissions (SET_NULL preserves them)
        2. Delete hint activations, segmentation analyses, feedback
        3. Delete progress records
        4. Delete enrollments
        5. Delete consent records
        6. Delete age verification
        7. Delete nominee
        8. Delete user profile
        9. Delete Firebase account
        10. Delete Django user (cascades remaining relations)
        """
        username = user.username
        user_id = user.id
        stats = {}

        try:
            # 1. Anonymize submissions (these use SET_NULL, so user FK becomes NULL)
            # The raw_input may contain PII — scrub it if requested
            from purplex.submissions.models import (
                HintActivation,
                SegmentationAnalysis,
                Submission,
                SubmissionFeedback,
            )

            submission_ids = list(
                Submission.objects.filter(user=user).values_list("id", flat=True)
            )
            stats["submissions_anonymized"] = len(submission_ids)

            # 2. Delete detailed submission data that's tied to user identity
            stats["hint_activations_deleted"] = HintActivation.objects.filter(
                submission__user=user
            ).delete()[0]

            stats["segmentation_analyses_deleted"] = (
                SegmentationAnalysis.objects.filter(submission__user=user).delete()[0]
            )

            stats["submission_feedback_deleted"] = SubmissionFeedback.objects.filter(
                submission__user=user
            ).delete()[0]

            # 3. Null out user FK on submissions (preserves for research)
            Submission.objects.filter(user=user).update(user=None)

            # 4. Delete progress records
            from purplex.problems_app.models import (
                CourseEnrollment,
                ProgressSnapshot,
                UserProblemSetProgress,
                UserProgress,
            )

            # UserProgress uses SET_NULL, so null it out
            stats["progress_anonymized"] = UserProgress.objects.filter(
                user=user
            ).update(user=None)

            # These use CASCADE but let's be explicit
            stats["problem_set_progress_deleted"] = (
                UserProblemSetProgress.objects.filter(user=user).delete()[0]
            )

            stats["progress_snapshots_deleted"] = ProgressSnapshot.objects.filter(
                user=user
            ).delete()[0]

            # 5. Delete enrollments
            stats["enrollments_deleted"] = CourseEnrollment.objects.filter(
                user=user
            ).delete()[0]

            # 6. Delete privacy-related records
            from ..models import (
                AgeVerification,
                AuditAction,
                DataAccessAuditLog,
                DataPrincipalNominee,
                UserConsent,
            )

            # Consent records use SET_NULL — they are preserved for GDPR Art. 7
            # audit trail. The user FK is automatically nulled on user.delete().
            stats["consent_records_preserved"] = UserConsent.objects.filter(
                user=user
            ).count()

            try:
                AgeVerification.objects.filter(user=user).delete()
                stats["age_verification_deleted"] = True
            except AgeVerification.DoesNotExist:
                stats["age_verification_deleted"] = False

            try:
                DataPrincipalNominee.objects.filter(user=user).delete()
                stats["nominee_deleted"] = True
            except DataPrincipalNominee.DoesNotExist:
                stats["nominee_deleted"] = False

            # 7. Delete Firebase account
            stats["firebase_deleted"] = cls._delete_firebase_account(user)

            # 8. Log the deletion in audit trail (before deleting user)
            DataAccessAuditLog.objects.create(
                accessor=None,  # System action
                action=AuditAction.DELETE_USER,
                target_user_ids=[user_id],
                query_parameters={"reason": "user_requested_deletion"},
                ip_address="127.0.0.1",  # System action
            )

            # 9. Delete user profile and Django user (CASCADE handles profile)
            user.delete()
            stats["user_deleted"] = True

            logger.info(
                f"Hard deletion completed for user {username} (id={user_id}): {stats}"
            )
            return {"status": "deleted", "user_id": user_id, "stats": stats}

        except Exception as e:
            logger.error(
                f"Error during hard deletion for user {username}: {e}",
                exc_info=True,
            )
            raise

    @staticmethod
    def _delete_firebase_account(user: User) -> bool:
        """
        Delete the user's Firebase account.

        Raises on failure so the caller can decide whether to proceed
        with local deletion or abort (GDPR Art. 17 requires complete erasure).
        """
        profile = getattr(user, "profile", None)
        if not profile or not profile.firebase_uid:
            return False

        from ..utils.firebase import get_firebase_service

        firebase = get_firebase_service()
        firebase.delete_user(profile.firebase_uid)
        logger.info(f"Firebase account deleted for uid={profile.firebase_uid}")
        return True

    @classmethod
    def get_accounts_pending_deletion(cls):
        """
        Get all accounts whose grace period has expired and are ready
        for hard deletion. Used by the cleanup management command.
        """
        from ..models import UserProfile

        return UserProfile.objects.filter(
            deletion_requested_at__isnull=False,
            deletion_scheduled_at__lte=timezone.now(),
            user__is_active=False,
        ).select_related("user")
