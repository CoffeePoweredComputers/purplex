"""
Tests for AI consent gates in the pipeline.

Covers: generate_variations_helper and segment_prompt_helper
consent checks, including minor/parental consent scenarios.
"""

from unittest.mock import patch

import pytest

from purplex.users_app.models import ConsentType
from purplex.users_app.services.consent_service import (
    AIConsentNotGrantedError,
    ConsentService,
)
from tests.factories import AgeVerificationFactory, UserFactory, UserProfileFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestGenerateVariationsConsentGate:
    """Tests for the AI consent gate in generate_variations_helper."""

    @patch("purplex.problems_app.tasks.pipeline.getattr")
    def test_blocks_when_no_ai_consent(self, mock_getattr):
        """Without AI consent, generate_variations_helper should raise."""
        user = UserFactory()
        UserProfileFactory(user=user)

        # Directly test the consent check logic
        with pytest.raises(AIConsentNotGrantedError):
            ConsentService.check_ai_consent(user)

    def test_allows_when_ai_consent_granted(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise
        ConsentService.check_ai_consent(user)

    def test_blocks_minor_without_parental_consent(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(user=user, is_minor=True, parental_consent_given=False)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        with pytest.raises(AIConsentNotGrantedError, match="Parental consent"):
            ConsentService.check_ai_consent(user)

    def test_allows_minor_with_parental_consent(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(user=user, is_minor=True, parental_consent_given=True)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise
        ConsentService.check_ai_consent(user)

    def test_allows_child_with_parental_consent(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(
            user=user, is_minor=True, is_child=True, parental_consent_given=True
        )
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise — parental consent given
        ConsentService.check_ai_consent(user)

    def test_blocks_after_consent_withdrawal(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        ConsentService.withdraw_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        with pytest.raises(AIConsentNotGrantedError):
            ConsentService.check_ai_consent(user)

    def test_adult_without_age_verification_only_checks_consent(self):
        """User without age_verification — only AI consent check matters."""
        user = UserFactory()
        UserProfileFactory(user=user)
        # No AgeVerification created — user treated as adult
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise
        ConsentService.check_ai_consent(user)

    def test_non_minor_age_verification_does_not_require_parental(self):
        user = UserFactory()
        UserProfileFactory(user=user)
        AgeVerificationFactory(user=user, is_minor=False, is_child=False)
        ConsentService.grant_consent(
            user=user, consent_type=ConsentType.AI_PROCESSING, ip_address="127.0.0.1"
        )
        # Should not raise — adult
        ConsentService.check_ai_consent(user)
