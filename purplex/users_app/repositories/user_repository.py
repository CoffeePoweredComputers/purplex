"""
Repository for User model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Q
from django.contrib.auth.models import User

from purplex.problems_app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """
    Repository for all User-related database queries.
    
    This repository handles all data access for Django User model
    ensuring consistent data access patterns and separation of
    concerns from business logic.
    """
    
    model_class = User
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional[User]:
        """
        Get a user by their primary key ID.
        
        Args:
            user_id: The primary key of the user
            
        Returns:
            User instance or None if not found
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    @classmethod
    def get_with_profile(cls, user_id: int) -> Optional[User]:
        """
        Get a user with their profile pre-fetched.
        
        Args:
            user_id: The primary key of the user
            
        Returns:
            User instance with profile or None if not found
        """
        try:
            return User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[User]:
        """
        Get a user by their username.
        
        Args:
            username: The username to search for
            
        Returns:
            User instance or None if not found
        """
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
    
    @classmethod
    def get_service_account(cls) -> Optional[User]:
        """
        Get the service account user.
        
        Returns:
            Service account User instance or None if not found
        """
        try:
            return User.objects.get(username='service_account')
        except User.DoesNotExist:
            return None
    
    @classmethod
    def username_exists(cls, username: str) -> bool:
        """
        Check if a username already exists.
        
        Args:
            username: The username to check
            
        Returns:
            True if username exists, False otherwise
        """
        return User.objects.filter(username=username).exists()
    
    @classmethod
    def email_exists(cls, email: str) -> bool:
        """
        Check if an email already exists.
        
        Args:
            email: The email to check
            
        Returns:
            True if email exists, False otherwise
        """
        return User.objects.filter(email=email).exists()
    
    @classmethod
    def create(cls, **kwargs) -> User:
        """
        Create a new user.
        
        Args:
            **kwargs: User fields (username, email, etc.)
            
        Returns:
            Created User instance
        """
        return User.objects.create(**kwargs)
    
    @classmethod
    def create_user(cls, username: str, email: str = None, password: str = None, **kwargs) -> User:
        """
        Create a new user with proper password hashing.
        
        Args:
            username: Username for the new user
            email: Email address (optional)
            password: Raw password (will be hashed)
            **kwargs: Additional user fields
            
        Returns:
            Created User instance
        """
        return User.objects.create_user(username=username, email=email, password=password, **kwargs)
    
    @classmethod
    def get_by_role(cls, role: str) -> QuerySet:
        """
        Get all users with a specific role.
        
        Args:
            role: The role to filter by (from UserProfile)
            
        Returns:
            QuerySet of users with the specified role
        """
        return User.objects.filter(profile__role=role).select_related('profile')
    
    @classmethod
    def search(cls, query: Dict[str, Any]) -> QuerySet:
        """
        Search users based on multiple criteria.
        
        Args:
            query: Dictionary of search criteria
            
        Returns:
            QuerySet of matching users
        """
        queryset = User.objects.all()
        
        if 'username' in query:
            queryset = queryset.filter(username__icontains=query['username'])
        
        if 'email' in query:
            queryset = queryset.filter(email__icontains=query['email'])
        
        if 'first_name' in query:
            queryset = queryset.filter(first_name__icontains=query['first_name'])
        
        if 'last_name' in query:
            queryset = queryset.filter(last_name__icontains=query['last_name'])
        
        if 'is_active' in query:
            queryset = queryset.filter(is_active=query['is_active'])
        
        if 'is_staff' in query:
            queryset = queryset.filter(is_staff=query['is_staff'])
        
        if 'role' in query:
            queryset = queryset.filter(profile__role=query['role'])
        
        return queryset.select_related('profile')
    
    @classmethod
    def get_all_users(cls) -> QuerySet:
        """
        Get all users with their profiles.
        
        Returns:
            QuerySet of all users with profiles pre-fetched
        """
        return User.objects.all().select_related('profile')
    
    @classmethod
    def get_active_users(cls) -> QuerySet:
        """
        Get all active users.
        
        Returns:
            QuerySet of active users
        """
        return User.objects.filter(is_active=True).select_related('profile')
    
    @classmethod
    def update(cls, user_id: int, **kwargs) -> Optional[User]:
        """
        Update a user's fields.
        
        Args:
            user_id: The user's primary key
            **kwargs: Fields to update
            
        Returns:
            Updated User instance or None if not found
        """
        updated = User.objects.filter(pk=user_id).update(**kwargs)
        if updated:
            return cls.get_by_id(user_id)
        return None
    
    @classmethod
    def delete_user(cls, user_id: int) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user's primary key
            
        Returns:
            True if deleted, False if not found
        """
        deleted, _ = User.objects.filter(pk=user_id).delete()
        return deleted > 0
    
    @classmethod
    def deactivate_user(cls, user_id: int) -> bool:
        """
        Deactivate a user (soft delete).
        
        Args:
            user_id: The user's primary key
            
        Returns:
            True if deactivated, False if not found
        """
        updated = User.objects.filter(pk=user_id).update(is_active=False)
        return updated > 0
    
    @classmethod
    def activate_user(cls, user_id: int) -> bool:
        """
        Activate a user.
        
        Args:
            user_id: The user's primary key
            
        Returns:
            True if activated, False if not found
        """
        updated = User.objects.filter(pk=user_id).update(is_active=True)
        return updated > 0
    
    @classmethod
    def bulk_create_users(cls, users_data: List[Dict[str, Any]]) -> List[User]:
        """
        Bulk create multiple users.
        
        Args:
            users_data: List of dictionaries with user data
            
        Returns:
            List of created User instances
        """
        users = [User(**data) for data in users_data]
        return User.objects.bulk_create(users)
    
    @classmethod
    def search_users(cls, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search users by username, email, first name, or last name.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of user dictionaries with profile data
        """
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).select_related('profile')[:limit]
        
        return [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'role': user.profile.role if hasattr(user, 'profile') else 'user'
            }
            for user in users
        ]
    
    @classmethod
    def exists_with_email(cls, email: str) -> bool:
        """
        Check if a user exists with the given email.
        
        Args:
            email: Email to check
            
        Returns:
            True if exists, False otherwise
        """
        return User.objects.filter(email=email).exists()
    
    @classmethod
    def get_or_create_service_account(cls) -> tuple[User, bool]:
        """
        Get or create the service account user.
        
        Returns:
            Tuple of (User instance, created boolean)
        """
        return User.objects.get_or_create(
            username='service_account',
            defaults={
                'email': 'service@purplex.ai',
                'first_name': 'Service',
                'last_name': 'Account',
                'is_active': True,
                'is_staff': False,
            }
        )