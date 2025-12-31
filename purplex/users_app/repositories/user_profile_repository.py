"""
Repository for UserProfile model data access.
"""

import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import QuerySet

from purplex.problems_app.repositories.base_repository import BaseRepository
from purplex.users_app.models import UserProfile

logger = logging.getLogger(__name__)


class UserProfileRepository(BaseRepository):
    """
    Repository for all UserProfile-related database queries.

    This repository handles all data access for UserProfile model
    ensuring consistent data access patterns and separation of
    concerns from business logic.
    """

    model_class = UserProfile

    @classmethod
    def get_by_id(cls, profile_id: int) -> UserProfile | None:
        """
        Get a user profile by its primary key.

        Args:
            profile_id: The primary key of the profile

        Returns:
            UserProfile instance or None if not found
        """
        try:
            return UserProfile.objects.get(pk=profile_id)
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def get_by_user(cls, user: User) -> UserProfile | None:
        """
        Get a user profile by the associated user.

        Args:
            user: The User instance

        Returns:
            UserProfile instance or None if not found
        """
        try:
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def get_by_user_id(cls, user_id: int) -> UserProfile | None:
        """
        Get a user profile by the associated user's ID.

        Args:
            user_id: The User's primary key

        Returns:
            UserProfile instance or None if not found
        """
        try:
            return UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def get_by_firebase_uid(cls, firebase_uid: str) -> UserProfile | None:
        """
        Get a user profile by Firebase UID.

        Args:
            firebase_uid: The Firebase UID

        Returns:
            UserProfile instance or None if not found
        """
        try:
            return UserProfile.objects.get(firebase_uid=firebase_uid)
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def get_by_firebase_with_user(cls, firebase_uid: str) -> UserProfile | None:
        """
        Get a user profile by Firebase UID with the related User pre-fetched.

        Args:
            firebase_uid: The Firebase UID

        Returns:
            UserProfile instance with User or None if not found
        """
        try:
            return UserProfile.objects.select_related("user").get(
                firebase_uid=firebase_uid
            )
        except UserProfile.DoesNotExist:
            return None

    @classmethod
    def create(cls, **kwargs) -> UserProfile:
        """
        Create a new user profile.

        Args:
            **kwargs: UserProfile fields (user, firebase_uid, role, etc.)

        Returns:
            Created UserProfile instance
        """
        return UserProfile.objects.create(**kwargs)

    @classmethod
    def get_or_create_with_user(
        cls, firebase_uid: str, email: str, display_name: str
    ) -> tuple[UserProfile, User]:
        """
        Get or create user profile with associated Django user.

        Uses Django's get_or_create to handle race conditions safely without database locks.
        This method avoids the select_for_update bottleneck by relying on database
        constraints and Django's built-in race condition handling.

        Args:
            firebase_uid: Firebase user ID (must be unique)
            email: User's email address
            display_name: User's display name

        Returns:
            Tuple of (UserProfile instance, Django User instance)
            The UserProfile will have a 'was_created' attribute set to True if newly created.
        """
        from purplex.users_app.repositories.user_repository import UserRepository

        # First, try to get existing profile
        try:
            user_profile = UserProfile.objects.select_related("user").get(
                firebase_uid=firebase_uid
            )
            user_profile.was_created = False

            # Ensure user exists (edge case handling)
            if not user_profile.user:
                # Edge case: profile exists but no user (shouldn't happen in normal operation)
                logger.warning(
                    f"UserProfile exists without User for Firebase UID: {firebase_uid}"
                )

                # Create the missing user with retry logic for username conflicts
                if email:
                    username_base = email.split("@")[0]
                else:
                    username_base = firebase_uid[:15]

                max_attempts = 10
                for attempt in range(max_attempts):
                    try:
                        # Generate unique username with timestamp to reduce conflicts
                        import time

                        timestamp_suffix = str(int(time.time() * 1000))[
                            -6:
                        ]  # Last 6 digits of milliseconds
                        if attempt == 0:
                            username = username_base
                        else:
                            username = f"{username_base}_{timestamp_suffix}_{attempt}"

                        # Try to create the user
                        user = UserRepository.create(
                            username=username,
                            email=email or "",
                            first_name=display_name or "",
                        )
                        break  # Success, exit the loop

                    except IntegrityError as e:
                        if "username" in str(e) and attempt < max_attempts - 1:
                            # Username conflict, try again with a different username
                            logger.debug(
                                f"Username conflict for {username}, retrying..."
                            )
                            continue
                        else:
                            # Different error or max attempts reached
                            raise e
                else:
                    # This shouldn't happen, but handle it just in case
                    raise ValueError(
                        f"Could not create unique username after {max_attempts} attempts"
                    )

                user_profile.user = user
                user_profile.save(update_fields=["user"])

                logger.info(
                    f"Created missing User for existing UserProfile: {firebase_uid}"
                )
            else:
                user = user_profile.user

            logger.debug(
                f"Found existing user profile for Firebase UID: {firebase_uid}"
            )
            return user_profile, user_profile.user

        except UserProfile.DoesNotExist:
            # Profile doesn't exist, need to create both user and profile
            pass

        # Create Django user first
        if email:
            username_base = email.split("@")[0]
        else:
            username_base = firebase_uid[:15]

        # Create user with retry logic for username conflicts
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                # Generate unique username with timestamp to reduce conflicts
                import time

                timestamp_suffix = str(int(time.time() * 1000))[
                    -6:
                ]  # Last 6 digits of milliseconds
                if attempt == 0:
                    username = username_base
                else:
                    username = f"{username_base}_{timestamp_suffix}_{attempt}"

                # Try to create the user
                user = UserRepository.create(
                    username=username, email=email or "", first_name=display_name or ""
                )
                break  # Success, exit the loop

            except IntegrityError as e:
                if "username" in str(e) and attempt < max_attempts - 1:
                    # Username conflict, try again with a different username
                    logger.debug(f"Username conflict for {username}, retrying...")
                    continue
                else:
                    # Different error or max attempts reached
                    raise e
        else:
            # This shouldn't happen, but handle it just in case
            raise ValueError(
                f"Could not create unique username after {max_attempts} attempts"
            )

        # Try to create the profile with the user
        try:
            user_profile = UserProfile.objects.create(
                firebase_uid=firebase_uid, user=user, role="user"
            )
            user_profile.was_created = True

            logger.debug(
                f"Created new user profile and user for Firebase UID: {firebase_uid}"
            )
            return user_profile, user

        except IntegrityError as e:
            # Race condition: Another thread created the profile while we were creating the user
            # Clean up the user we just created since it wasn't linked
            user.delete()

            logger.debug(
                f"IntegrityError during profile creation, fetching existing: {e}"
            )

            # Get the existing profile that was created by another thread
            try:
                user_profile = UserProfile.objects.select_related("user").get(
                    firebase_uid=firebase_uid
                )
                user_profile.was_created = False
                return user_profile, user_profile.user
            except UserProfile.DoesNotExist:
                # This shouldn't happen, but if it does, re-raise the original error
                raise e

    @classmethod
    def update(cls, profile_id: int, **kwargs) -> UserProfile | None:
        """
        Update a user profile's fields.

        Args:
            profile_id: The profile's primary key
            **kwargs: Fields to update

        Returns:
            Updated UserProfile instance or None if not found
        """
        updated = UserProfile.objects.filter(pk=profile_id).update(**kwargs)
        if updated:
            return cls.get_by_id(profile_id)
        return None

    @classmethod
    def get_or_create(
        cls, user: User, defaults: dict[str, Any] = None
    ) -> tuple[UserProfile, bool]:
        """
        Get or create a user profile for a user.

        Args:
            user: The User instance
            defaults: Default values for creation

        Returns:
            Tuple of (UserProfile instance, created boolean)
        """
        return UserProfile.objects.get_or_create(user=user, defaults=defaults or {})

    @classmethod
    def get_by_role(cls, role: str) -> QuerySet:
        """
        Get all user profiles with a specific role.

        Args:
            role: The role to filter by

        Returns:
            QuerySet of UserProfiles with the specified role
        """
        return UserProfile.objects.filter(role=role).select_related("user")

    @classmethod
    def get_all_with_users(cls) -> QuerySet:
        """
        Get all user profiles with their users pre-fetched.

        Returns:
            QuerySet of all UserProfiles with users
        """
        return UserProfile.objects.all().select_related("user")

    @classmethod
    def bulk_create(cls, profiles_data: list[dict[str, Any]]) -> list[UserProfile]:
        """
        Bulk create multiple user profiles.

        Args:
            profiles_data: List of dictionaries with profile data

        Returns:
            List of created UserProfile instances
        """
        profiles = [UserProfile(**data) for data in profiles_data]
        return UserProfile.objects.bulk_create(profiles)

    @classmethod
    def search(cls, query: dict[str, Any]) -> QuerySet:
        """
        Search user profiles based on multiple criteria.

        Args:
            query: Dictionary of search criteria

        Returns:
            QuerySet of matching profiles
        """
        queryset = UserProfile.objects.all()

        if "role" in query:
            queryset = queryset.filter(role=query["role"])

        if "firebase_uid" in query:
            queryset = queryset.filter(firebase_uid=query["firebase_uid"])

        if "user_id" in query:
            queryset = queryset.filter(user_id=query["user_id"])

        if "username" in query:
            queryset = queryset.filter(user__username__icontains=query["username"])

        if "email" in query:
            queryset = queryset.filter(user__email__icontains=query["email"])

        return queryset.select_related("user")
