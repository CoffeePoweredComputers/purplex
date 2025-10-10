"""
Data anonymization utilities for research exports.

Provides deterministic, reversible (with key) anonymization for research data
while maintaining referential integrity across datasets.
"""

import hashlib
import secrets
from typing import Optional, Dict
from django.contrib.auth.models import User
from django.core.cache import cache


class AnonymizationService:
    """
    Service for anonymizing user data in research exports.
    """

    # Cache key prefix for anonymization mappings
    CACHE_PREFIX = 'anon_map'
    CACHE_TIMEOUT = 3600  # 1 hour

    @classmethod
    def anonymize_user_id(cls, user: User, use_cache: bool = True) -> str:
        """
        Anonymize user ID using deterministic hash.

        Args:
            user: User instance
            use_cache: Whether to use cached mapping

        Returns:
            Anonymized user ID (16-char hex)
        """
        cache_key = f"{cls.CACHE_PREFIX}:user:{user.id}"

        if use_cache:
            cached_id = cache.get(cache_key)
            if cached_id:
                return cached_id

        # Create deterministic hash
        hash_input = f"user_{user.id}_{user.username}"
        anon_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        if use_cache:
            cache.set(cache_key, anon_id, cls.CACHE_TIMEOUT)

        return anon_id

    @classmethod
    def anonymize_email(cls, user: User) -> str:
        """Generate anonymized email address."""
        anon_id = cls.anonymize_user_id(user)
        return f"{anon_id}@anonymized.purplex.edu"

    @classmethod
    def anonymize_name(cls, user: User) -> str:
        """Generate anonymized display name."""
        anon_id = cls.anonymize_user_id(user)
        return f"User_{anon_id[:8]}"

    @classmethod
    def anonymize_dataset(cls, data: Dict, user_fields: list = None) -> Dict:
        """
        Anonymize a complete dataset.

        Args:
            data: Dataset dictionary
            user_fields: List of field names containing user IDs

        Returns:
            Anonymized dataset
        """
        user_fields = user_fields or ['user_id', 'username', 'email']

        # Deep copy to avoid mutating original
        import copy
        anonymized = copy.deepcopy(data)

        # Create mapping for consistent anonymization
        user_mapping = {}

        def anonymize_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in user_fields and value:
                        if value not in user_mapping:
                            # Create consistent anonymous ID
                            hash_val = hashlib.sha256(str(value).encode()).hexdigest()[:16]
                            user_mapping[value] = hash_val
                        obj[key] = user_mapping[value]
                    elif isinstance(value, (dict, list)):
                        anonymize_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    anonymize_recursive(item)

        anonymize_recursive(anonymized)

        return anonymized

    @classmethod
    def create_anonymization_key(cls, export_id: str) -> str:
        """
        Create a unique key for an export that can be used to reverse anonymization.

        Args:
            export_id: Unique identifier for the export

        Returns:
            Secret key for reversal
        """
        key = secrets.token_urlsafe(32)
        cache_key = f"{cls.CACHE_PREFIX}:export:{export_id}"
        cache.set(cache_key, key, 86400)  # 24 hours
        return key

    @classmethod
    def get_deanonymization_mapping(
        cls,
        export_id: str,
        secret_key: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve the mapping to reverse anonymization (admin only).

        Args:
            export_id: Export identifier
            secret_key: Secret key from create_anonymization_key

        Returns:
            Mapping of anonymous IDs to real usernames, or None if invalid
        """
        cache_key = f"{cls.CACHE_PREFIX}:export:{export_id}"
        stored_key = cache.get(cache_key)

        if stored_key != secret_key:
            return None

        # TODO: Implement secure storage of mappings
        # For now, return None (mapping not persisted)
        return None
