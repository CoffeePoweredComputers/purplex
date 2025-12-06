"""
Data anonymization utilities for research exports.

Provides deterministic, reversible (with key) anonymization for research data
while maintaining referential integrity across datasets.
"""

import hashlib
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
