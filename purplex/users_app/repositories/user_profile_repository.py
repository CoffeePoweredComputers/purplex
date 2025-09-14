"""
Repository for UserProfile model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Q
from django.db import transaction
from django.contrib.auth.models import User

from purplex.users_app.models import UserProfile
from purplex.problems_app.repositories.base_repository import BaseRepository


class UserProfileRepository(BaseRepository):
    """
    Repository for all UserProfile-related database queries.
    
    This repository handles all data access for UserProfile model
    ensuring consistent data access patterns and separation of
    concerns from business logic.
    """
    
    model_class = UserProfile
    
    @classmethod
    def get_by_id(cls, profile_id: int) -> Optional[UserProfile]:
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
    def get_by_user(cls, user: User) -> Optional[UserProfile]:
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
    def get_by_firebase_uid(cls, firebase_uid: str) -> Optional[UserProfile]:
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
    def get_by_firebase_uid_for_update(cls, firebase_uid: str) -> Optional[UserProfile]:
        """
        Get a user profile by Firebase UID with a database lock for update.
        This is used for atomic operations to prevent race conditions.
        
        Args:
            firebase_uid: The Firebase UID
            
        Returns:
            UserProfile instance with update lock or None if not found
        """
        try:
            return UserProfile.objects.select_for_update().get(firebase_uid=firebase_uid)
        except UserProfile.DoesNotExist:
            return None
    
    @classmethod
    def get_by_firebase_with_user(cls, firebase_uid: str) -> Optional[UserProfile]:
        """
        Get a user profile by Firebase UID with the related User pre-fetched.
        
        Args:
            firebase_uid: The Firebase UID
            
        Returns:
            UserProfile instance with User or None if not found
        """
        try:
            return UserProfile.objects.select_related('user').get(firebase_uid=firebase_uid)
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
    def update(cls, profile_id: int, **kwargs) -> Optional[UserProfile]:
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
    def update_by_user(cls, user: User, **kwargs) -> Optional[UserProfile]:
        """
        Update a user profile by user reference.
        
        Args:
            user: The User instance
            **kwargs: Fields to update
            
        Returns:
            Updated UserProfile instance or None if not found
        """
        updated = UserProfile.objects.filter(user=user).update(**kwargs)
        if updated:
            return cls.get_by_user(user)
        return None
    
    @classmethod
    def update_by_firebase_uid(cls, firebase_uid: str, **kwargs) -> Optional[UserProfile]:
        """
        Update a user profile by Firebase UID.
        
        Args:
            firebase_uid: The Firebase UID
            **kwargs: Fields to update
            
        Returns:
            Updated UserProfile instance or None if not found
        """
        updated = UserProfile.objects.filter(firebase_uid=firebase_uid).update(**kwargs)
        if updated:
            return cls.get_by_firebase_uid(firebase_uid)
        return None
    
    @classmethod
    def firebase_uid_exists(cls, firebase_uid: str) -> bool:
        """
        Check if a Firebase UID already exists.
        
        Args:
            firebase_uid: The Firebase UID to check
            
        Returns:
            True if exists, False otherwise
        """
        return UserProfile.objects.filter(firebase_uid=firebase_uid).exists()
    
    @classmethod
    def get_or_create(cls, user: User, defaults: Dict[str, Any] = None) -> tuple[UserProfile, bool]:
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
        return UserProfile.objects.filter(role=role).select_related('user')
    
    @classmethod
    def get_all_with_users(cls) -> QuerySet:
        """
        Get all user profiles with their users pre-fetched.
        
        Returns:
            QuerySet of all UserProfiles with users
        """
        return UserProfile.objects.all().select_related('user')
    
    @classmethod
    def delete_by_user(cls, user: User) -> bool:
        """
        Delete a user profile by user reference.
        
        Args:
            user: The User instance
            
        Returns:
            True if deleted, False if not found
        """
        deleted, _ = UserProfile.objects.filter(user=user).delete()
        return deleted > 0
    
    @classmethod
    def delete_by_firebase_uid(cls, firebase_uid: str) -> bool:
        """
        Delete a user profile by Firebase UID.
        
        Args:
            firebase_uid: The Firebase UID
            
        Returns:
            True if deleted, False if not found
        """
        deleted, _ = UserProfile.objects.filter(firebase_uid=firebase_uid).delete()
        return deleted > 0
    
    @classmethod
    def bulk_create(cls, profiles_data: List[Dict[str, Any]]) -> List[UserProfile]:
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
    def search(cls, query: Dict[str, Any]) -> QuerySet:
        """
        Search user profiles based on multiple criteria.
        
        Args:
            query: Dictionary of search criteria
            
        Returns:
            QuerySet of matching profiles
        """
        queryset = UserProfile.objects.all()
        
        if 'role' in query:
            queryset = queryset.filter(role=query['role'])
        
        if 'firebase_uid' in query:
            queryset = queryset.filter(firebase_uid=query['firebase_uid'])
        
        if 'user_id' in query:
            queryset = queryset.filter(user_id=query['user_id'])
        
        if 'username' in query:
            queryset = queryset.filter(user__username__icontains=query['username'])
        
        if 'email' in query:
            queryset = queryset.filter(user__email__icontains=query['email'])
        
        return queryset.select_related('user')
    
    @classmethod
    def update_last_login(cls, firebase_uid: str) -> bool:
        """
        Update the last login timestamp for a user profile.
        
        Args:
            firebase_uid: The Firebase UID
            
        Returns:
            True if updated, False if not found
        """
        from django.utils import timezone
        updated = UserProfile.objects.filter(firebase_uid=firebase_uid).update(
            last_login=timezone.now()
        )
        return updated > 0
    
    @classmethod
    def get_instructors(cls) -> QuerySet:
        """
        Get all user profiles with instructor role.
        
        Returns:
            QuerySet of instructor profiles
        """
        return UserProfile.objects.filter(role='instructor').select_related('user')
    
    @classmethod
    def get_students(cls) -> QuerySet:
        """
        Get all user profiles with student role.
        
        Returns:
            QuerySet of student profiles
        """
        return UserProfile.objects.filter(role='student').select_related('user')