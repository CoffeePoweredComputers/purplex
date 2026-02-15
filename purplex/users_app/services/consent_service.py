"""
Consent management service for GDPR, CCPA, and DPDPA compliance.

Handles grant, withdrawal, and verification of user consent.
Consent records are append-only — withdrawals create new records
rather than modifying existing ones, preserving the audit trail.
"""

import logging

from django.contrib.auth.models import User
from django.utils import timezone

from ..models import ConsentMethod, ConsentType, UserConsent

logger = logging.getLogger(__name__)

# Current policy versions — update when policies change
CURRENT_POLICY_VERSIONS = {
    ConsentType.PRIVACY_POLICY: "1.0",
    ConsentType.TERMS_OF_SERVICE: "1.0",
    ConsentType.AI_PROCESSING: "1.0",
    ConsentType.THIRD_PARTY_SHARING: "1.0",
    ConsentType.RESEARCH_USE: "1.0",
    ConsentType.BEHAVIORAL_TRACKING: "1.0",
}

# Consent types required at registration
REQUIRED_AT_REGISTRATION = [
    ConsentType.PRIVACY_POLICY,
    ConsentType.TERMS_OF_SERVICE,
]

# Consent types that are optional (can be granted/withdrawn independently)
OPTIONAL_CONSENT_TYPES = [
    ConsentType.AI_PROCESSING,
    ConsentType.THIRD_PARTY_SHARING,
    ConsentType.RESEARCH_USE,
    ConsentType.BEHAVIORAL_TRACKING,
]


class AIConsentNotGrantedError(Exception):
    """Raised when a user has not consented to AI processing."""

    pass


class ConsentService:
    """Service for managing user consent records."""

    @staticmethod
    def grant_consent(
        user: User,
        consent_type: str,
        ip_address: str,
        consent_method: str = ConsentMethod.REGISTRATION,
        policy_version: str | None = None,
    ) -> UserConsent:
        """
        Record a consent grant. Creates a new record (append-only).
        """
        if policy_version is None:
            policy_version = CURRENT_POLICY_VERSIONS.get(consent_type, "1.0")

        consent = UserConsent.objects.create(
            user=user,
            consent_type=consent_type,
            granted=True,
            ip_address=ip_address,
            policy_version=policy_version,
            consent_method=consent_method,
        )

        logger.info(
            f"Consent granted: user={user.username}, type={consent_type}, "
            f"version={policy_version}, method={consent_method}"
        )
        return consent

    @staticmethod
    def withdraw_consent(
        user: User,
        consent_type: str,
        ip_address: str,
    ) -> UserConsent:
        """
        Record a consent withdrawal. Creates a new record with granted=False.

        For required consent types (privacy_policy, terms_of_service),
        withdrawal effectively means the user wants to delete their account.
        """
        consent = UserConsent.objects.create(
            user=user,
            consent_type=consent_type,
            granted=False,
            withdrawn_at=timezone.now(),
            ip_address=ip_address,
            policy_version=CURRENT_POLICY_VERSIONS.get(consent_type, "1.0"),
            consent_method=ConsentMethod.IN_APP,
        )

        logger.info(f"Consent withdrawn: user={user.username}, type={consent_type}")
        return consent

    @staticmethod
    def has_active_consent(user: User, consent_type: str) -> bool:
        """
        Check if a user currently has active consent for a given type.
        Looks at the most recent record for this user+type combination.
        """
        latest = (
            UserConsent.objects.filter(user=user, consent_type=consent_type)
            .order_by("-granted_at")
            .first()
        )

        if latest is None:
            return False

        return latest.granted and latest.withdrawn_at is None

    @staticmethod
    def get_all_consent_status(user: User) -> dict:
        """
        Get current consent status for all consent types.
        Returns dict mapping consent_type -> {granted, granted_at, policy_version}.
        """
        result = {}
        for consent_type, _label in ConsentType.choices:
            latest = (
                UserConsent.objects.filter(user=user, consent_type=consent_type)
                .order_by("-granted_at")
                .first()
            )

            if latest:
                result[consent_type] = {
                    "granted": latest.granted and latest.withdrawn_at is None,
                    "granted_at": latest.granted_at.isoformat()
                    if latest.granted_at
                    else None,
                    "withdrawn_at": latest.withdrawn_at.isoformat()
                    if latest.withdrawn_at
                    else None,
                    "policy_version": latest.policy_version,
                }
            else:
                result[consent_type] = {
                    "granted": False,
                    "granted_at": None,
                    "withdrawn_at": None,
                    "policy_version": None,
                }

        return result

    @staticmethod
    def get_consent_history(user: User) -> list[dict]:
        """
        Get full consent history for a user (for data export).
        """
        records = UserConsent.objects.filter(user=user).order_by("granted_at")
        return [
            {
                "consent_type": r.consent_type,
                "granted": r.granted,
                "granted_at": r.granted_at.isoformat(),
                "withdrawn_at": r.withdrawn_at.isoformat() if r.withdrawn_at else None,
                "policy_version": r.policy_version,
                "consent_method": r.consent_method,
            }
            for r in records
        ]

    @staticmethod
    def grant_registration_consents(
        user: User,
        ip_address: str,
        optional_consents: list[str] | None = None,
    ) -> list[UserConsent]:
        """
        Grant all required consents at registration, plus any optional ones.
        """
        granted = []

        # Required consents
        for consent_type in REQUIRED_AT_REGISTRATION:
            consent = ConsentService.grant_consent(
                user=user,
                consent_type=consent_type,
                ip_address=ip_address,
                consent_method=ConsentMethod.REGISTRATION,
            )
            granted.append(consent)

        # Optional consents
        if optional_consents:
            for consent_type in optional_consents:
                if consent_type in OPTIONAL_CONSENT_TYPES:
                    consent = ConsentService.grant_consent(
                        user=user,
                        consent_type=consent_type,
                        ip_address=ip_address,
                        consent_method=ConsentMethod.REGISTRATION,
                    )
                    granted.append(consent)

        return granted

    @staticmethod
    def check_ai_consent(user: User) -> None:
        """
        Verify the user has active AI processing consent.
        Raises AIConsentNotGrantedError if not.

        For minors (DPDPA): also checks parental consent.
        """
        if not ConsentService.has_active_consent(user, ConsentType.AI_PROCESSING):
            raise AIConsentNotGrantedError("User has not consented to AI processing")

        # DPDPA: Check parental consent for minors
        age_verification = getattr(user, "age_verification", None)
        if age_verification and age_verification.is_minor:
            if not age_verification.parental_consent_given:
                raise AIConsentNotGrantedError(
                    "Parental consent required for AI processing of minor's data"
                )

    @staticmethod
    def needs_consent_update(user: User) -> list[str]:
        """
        Check if any of the user's consents are for outdated policy versions.
        Returns list of consent types that need re-consent.
        """
        outdated = []
        for consent_type, current_version in CURRENT_POLICY_VERSIONS.items():
            latest = (
                UserConsent.objects.filter(
                    user=user,
                    consent_type=consent_type,
                    granted=True,
                    withdrawn_at__isnull=True,
                )
                .order_by("-granted_at")
                .first()
            )

            if latest and latest.policy_version != current_version:
                outdated.append(consent_type)

        return outdated
