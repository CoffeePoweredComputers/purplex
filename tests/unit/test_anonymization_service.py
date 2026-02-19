"""
Tests for AnonymizationService — deterministic SHA-256 based anonymization.

Covers: deterministic output, cache behavior, length constraints,
and different users producing different hashes.
"""

import hashlib

import pytest
from django.core.cache import cache

from purplex.utils.anonymization import AnonymizationService
from tests.factories import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestAnonymizeUserId:
    """Tests for AnonymizationService.anonymize_user_id()."""

    def test_returns_16_char_hex_string(self):
        user = UserFactory()
        result = AnonymizationService.anonymize_user_id(user, use_cache=False)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_output(self):
        user = UserFactory()
        result1 = AnonymizationService.anonymize_user_id(user, use_cache=False)
        result2 = AnonymizationService.anonymize_user_id(user, use_cache=False)
        assert result1 == result2

    def test_matches_expected_sha256(self):
        user = UserFactory()
        expected_input = f"user_{user.id}_{user.username}"
        expected_hash = hashlib.sha256(expected_input.encode()).hexdigest()[:16]
        result = AnonymizationService.anonymize_user_id(user, use_cache=False)
        assert result == expected_hash

    def test_different_users_produce_different_hashes(self):
        user1 = UserFactory()
        user2 = UserFactory()
        hash1 = AnonymizationService.anonymize_user_id(user1, use_cache=False)
        hash2 = AnonymizationService.anonymize_user_id(user2, use_cache=False)
        assert hash1 != hash2

    def test_cache_stores_result(self):
        cache.clear()
        user = UserFactory()
        AnonymizationService.anonymize_user_id(user, use_cache=True)
        cache_key = f"{AnonymizationService.CACHE_PREFIX}:user:{user.id}"
        assert cache.get(cache_key) is not None

    def test_cache_returns_same_value(self):
        cache.clear()
        user = UserFactory()
        result1 = AnonymizationService.anonymize_user_id(user, use_cache=True)
        result2 = AnonymizationService.anonymize_user_id(user, use_cache=True)
        assert result1 == result2
