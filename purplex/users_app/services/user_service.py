"""
User management service - handles all user-related business logic.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from django.contrib.auth.models import User
from purplex.users_app.models import UserProfile

# Import models only for type hints
if TYPE_CHECKING:
    from django.db import transaction
    from django.db.models import Q, Count, Avg
from purplex.users_app.repositories import UserRepository, UserProfileRepository
from purplex.problems_app.repositories import (
    UserProgressRepository,
    SubmissionRepository,
    CourseEnrollmentRepository
)
import logging

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user management operations.
    
    All user-related business logic should go through this service.
    No direct User or UserProfile model access in views.
    """
    
    @classmethod
    def get_user_by_id(cls, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None
        """
        return UserRepository.get_with_profile(user_id)
    
    @classmethod
    def get_user_by_firebase_uid(cls, firebase_uid: str) -> Optional[User]:
        """
        Get user by Firebase UID.
        
        Args:
            firebase_uid: Firebase user ID
            
        Returns:
            User instance or None
        """
        profile = UserProfileRepository.get_by_firebase_with_user(firebase_uid)
        return profile.user if profile else None
    
    @classmethod
    def get_user_profile(cls, user: User) -> Optional[UserProfile]:
        """
        Get user profile for a user.
        
        Args:
            user: User instance
            
        Returns:
            UserProfile instance or None
        """
        try:
            return user.userprofile
        except UserProfile.DoesNotExist:
            return None
    
    @classmethod
    def update_user_role(cls, user: User, role: str) -> UserProfile:
        """
        Update user's role.
        
        Args:
            user: User instance
            role: New role (user, instructor, admin)
            
        Returns:
            Updated UserProfile
            
        Raises:
            ValueError: If role is invalid
        """
        valid_roles = ['user', 'instructor', 'admin', 'service']
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        profile = cls.get_user_profile(user)
        if not profile:
            raise ValueError(f"No profile found for user {user.username}")
        
        profile.role = role
        
        # Update Django permissions based on role
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'instructor':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        
        user.save()
        profile.save()
        
        logger.info(f"Updated role for user {user.username} to {role}")
        return profile
    
    @classmethod
    def get_users_by_role(cls, role: str) -> List[User]:
        """
        Get all users with a specific role.
        
        Args:
            role: Role to filter by
            
        Returns:
            List of User instances
        """
        return UserRepository.get_by_role(role)
    
    @classmethod
    def search_users(cls, query: str) -> List[User]:
        """
        Search users by username, email, or name.
        
        Args:
            query: Search query
            
        Returns:
            List of User instances
        """
        # Use repository search method
        return UserRepository.search_users(query, limit=20)
    
    @classmethod
    def get_user_statistics(cls, user: User) -> Dict[str, Any]:
        """
        Get user statistics for display.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with user statistics
        """
        stats = {
            'username': user.username,
            'email': user.email,
            'role': 'user',
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
        
        # Get role
        profile = cls.get_user_profile(user)
        if profile:
            stats['role'] = profile.role
        
        # Get progress statistics using repository
        progress_stats = UserProgressRepository.get_user_statistics(user)
        stats.update(progress_stats)
        
        # Get submission count using repository
        stats['total_submissions'] = SubmissionRepository.count(user=user)
        
        return stats
    
    @classmethod
    def delete_user_data(cls, user: User) -> None:
        """
        Delete all user data (for GDPR compliance).
        
        Args:
            user: User instance
        """
        # Delete all related data
        
        # Delete progress using repository
        UserProgressRepository.delete(user=user)
        
        # Delete submissions using repository
        SubmissionRepository.delete(user=user)
        
        # Delete enrollments using repository
        CourseEnrollmentRepository.delete(user=user)
        
        # Delete profile and user
        try:
            user.profile.delete()
        except UserProfile.DoesNotExist:
            pass
        
        username = user.username
        user.delete()
        
        logger.info(f"Deleted all data for user {username}")
    
    @classmethod
    def is_admin(cls, user: User) -> bool:
        """
        Check if user is an admin.
        
        Args:
            user: User instance
            
        Returns:
            True if user is admin
        """
        if user.is_superuser:
            return True
        
        profile = cls.get_user_profile(user)
        return profile and profile.role == 'admin'
    
    @classmethod
    def is_instructor(cls, user: User) -> bool:
        """
        Check if user is an instructor or admin.
        
        Args:
            user: User instance
            
        Returns:
            True if user is instructor or admin
        """
        if user.is_superuser or user.is_staff:
            return True
        
        profile = cls.get_user_profile(user)
        return profile and profile.role in ['instructor', 'admin']
    
    @classmethod
    def can_access_admin(cls, user: User) -> bool:
        """
        Check if user can access admin features.
        
        Args:
            user: User instance
            
        Returns:
            True if user can access admin
        """
        return cls.is_admin(user) or cls.is_instructor(user)