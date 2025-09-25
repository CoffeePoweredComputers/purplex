"""
Users app repository module.

This module provides repository classes for data access patterns
following the repository pattern to separate data access logic
from business logic.
"""

from .user_repository import UserRepository
from .user_profile_repository import UserProfileRepository

__all__ = [
    'UserRepository',
    'UserProfileRepository',
]