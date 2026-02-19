"""
Tests for ConsentService — GDPR/CCPA/DPDPA consent management.

Covers: grant, withdraw, active check, status, history,
registration consents, AI consent gate, and policy version checks.
"""

import pytest

from purplex.users_app.models import ConsentMethod, ConsentType
from purplex.users_app.services.consent_service import (
    CURRENT_POLICY_VERSIONS,
    REQUIRED_AT_REGISTRATION,
    AIConsentNotGrantedError,
    ConsentService,
)
from tests.factories import (
    AgeVerificationFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestGrantConsent:
    """Tests for ConsentService.grant_consent()."""

    def test_grant_creates_record(self, user):
        consent = ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="10.0.0.1",
        )
        assert consent.pk is not None
        assert consent.granted is True
        assert consent.withdrawn_at is None
        assert consent.ip_address == "10.0.0.1"

    def test_grant_uses_default_policy_version(self, user):
        consent = ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.AI_PROCESSING,
            ip_address="127.0.0.1",
        )
        assert (
            consent.policy_version == CURRENT_POLICY_VERSIONS[ConsentType.AI_PROCESSING]
        )

    def test_grant_accepts_custom_policy_version(self, user):
        consent = ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="127.0.0.1",
            policy_version="2.0",
        )
        assert consent.policy_version == "2.0"

    def test_grant_records_consent_method(self, user):
        consent = ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="127.0.0.1",
            consent_method=ConsentMethod.IN_APP,
        )
        assert consent.consent_method == ConsentMethod.IN_APP

    def test_grant_default_consent_method_is_registration(self, user):
        consent = ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="127.0.0.1",
        )
        assert consent.consent_method == ConsentMethod.REGISTRATION


class TestWithdrawConsent:
    """Tests for ConsentService.withdraw_consent()."""

    def test_withdraw_creates_new_record_with_granted_false(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        withdrawal = ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        assert withdrawal.granted is False
        assert withdrawal.withdrawn_at is not None

    def test_withdraw_preserves_original_grant_record(self, user):
        grant = ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Original grant record should still exist
        grant.refresh_from_db()
        assert grant.granted is True

    def test_withdraw_sets_consent_method_to_in_app(self, user):
        withdrawal = ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        assert withdrawal.consent_method == ConsentMethod.IN_APP


class TestHasActiveConsent:
    """Tests for ConsentService.has_active_consent()."""

    def test_no_records_returns_false(self, user):
        assert (
            ConsentService.has_active_consent(user, ConsentType.AI_PROCESSING) is False
        )

    def test_granted_record_returns_true(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        assert (
            ConsentService.has_active_consent(user, ConsentType.AI_PROCESSING) is True
        )

    def test_withdrawn_record_returns_false(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        assert (
            ConsentService.has_active_consent(user, ConsentType.AI_PROCESSING) is False
        )

    def test_re_granted_after_withdrawal_returns_true(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.AI_PROCESSING,
            ip_address="127.0.0.1",
            consent_method=ConsentMethod.IN_APP,
        )
        assert (
            ConsentService.has_active_consent(user, ConsentType.AI_PROCESSING) is True
        )


class TestGetAllConsentStatus:
    """Tests for ConsentService.get_all_consent_status()."""

    def test_returns_all_consent_types(self, user):
        status = ConsentService.get_all_consent_status(user)
        for ct, _label in ConsentType.choices:
            assert ct in status

    def test_ungrated_type_shows_false(self, user):
        status = ConsentService.get_all_consent_status(user)
        assert status[ConsentType.AI_PROCESSING]["granted"] is False
        assert status[ConsentType.AI_PROCESSING]["granted_at"] is None

    def test_granted_type_shows_true_with_timestamp(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        status = ConsentService.get_all_consent_status(user)
        assert status[ConsentType.AI_PROCESSING]["granted"] is True
        assert status[ConsentType.AI_PROCESSING]["granted_at"] is not None
        assert status[ConsentType.AI_PROCESSING]["policy_version"] == "1.0"


class TestGetConsentHistory:
    """Tests for ConsentService.get_consent_history()."""

    def test_empty_history(self, user):
        history = ConsentService.get_consent_history(user)
        assert history == []

    def test_history_ordered_oldest_first(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.PRIVACY_POLICY, ip_address="127.0.0.1"
        )
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        history = ConsentService.get_consent_history(user)
        assert len(history) == 2
        assert history[0]["consent_type"] == ConsentType.PRIVACY_POLICY

    def test_history_includes_withdrawal_records(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        history = ConsentService.get_consent_history(user)
        assert len(history) == 2
        assert history[1]["withdrawn_at"] is not None


class TestGrantRegistrationConsents:
    """Tests for ConsentService.grant_registration_consents()."""

    def test_grants_required_consents(self, user):
        granted = ConsentService.grant_registration_consents(
            user=user, ip_address="10.0.0.1"
        )
        types = [c.consent_type for c in granted]
        for req in REQUIRED_AT_REGISTRATION:
            assert req in types

    def test_grants_optional_consents_when_provided(self, user):
        granted = ConsentService.grant_registration_consents(
            user=user,
            ip_address="10.0.0.1",
            optional_consents=[ConsentType.AI_PROCESSING, ConsentType.RESEARCH_USE],
        )
        types = [c.consent_type for c in granted]
        assert ConsentType.AI_PROCESSING in types
        assert ConsentType.RESEARCH_USE in types

    def test_ignores_invalid_optional_consent_types(self, user):
        granted = ConsentService.grant_registration_consents(
            user=user,
            ip_address="10.0.0.1",
            optional_consents=["invalid_type"],
        )
        # Should only have the 2 required
        assert len(granted) == len(REQUIRED_AT_REGISTRATION)


class TestCheckAiConsent:
    """Tests for ConsentService.check_ai_consent()."""

    def test_raises_when_no_consent(self, user):
        with pytest.raises(AIConsentNotGrantedError):
            ConsentService.check_ai_consent(user)

    def test_passes_when_consent_granted(self, user):
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise
        ConsentService.check_ai_consent(user)

    def test_raises_for_minor_without_parental_consent(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(user=user, is_minor=True, parental_consent_given=False)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        with pytest.raises(AIConsentNotGrantedError, match="Parental consent"):
            ConsentService.check_ai_consent(user)

    def test_passes_for_minor_with_parental_consent(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(user=user, is_minor=True, parental_consent_given=True)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise
        ConsentService.check_ai_consent(user)


class TestNeedsConsentUpdate:
    """Tests for ConsentService.needs_consent_update()."""

    def test_no_consents_returns_empty(self, user):
        assert ConsentService.needs_consent_update(user) == []

    def test_current_version_returns_empty(self, user):
        ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="127.0.0.1",
            policy_version="1.0",
        )
        assert ConsentType.PRIVACY_POLICY not in ConsentService.needs_consent_update(
            user
        )

    def test_outdated_version_returns_consent_type(self, user):
        ConsentService.grant_consent(
            user=user,
            consent_type=ConsentType.PRIVACY_POLICY,
            ip_address="127.0.0.1",
            policy_version="0.9",
        )
        outdated = ConsentService.needs_consent_update(user)
        assert ConsentType.PRIVACY_POLICY in outdated
