"""
User management service - handles all user-related business logic.
"""
from typing import Optional, List, Dict, Any
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Avg
from purplex.users_app.models import UserProfile
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
        try:
            return User.objects.select_related('userprofile').get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @classmethod
    def get_user_by_firebase_uid(cls, firebase_uid: str) -> Optional[User]:
        """
        Get user by Firebase UID.
        
        Args:
            firebase_uid: Firebase user ID
            
        Returns:
            User instance or None
        """
        try:
            profile = UserProfile.objects.select_related('user').get(firebase_uid=firebase_uid)
            return profile.user
        except UserProfile.DoesNotExist:
            return None
    
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
    @transaction.atomic
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
        return User.objects.filter(userprofile__role=role).select_related('userprofile')
    
    @classmethod
    def search_users(cls, query: str) -> List[User]:
        """
        Search users by username, email, or name.
        
        Args:
            query: Search query
            
        Returns:
            List of User instances
        """
        return User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).select_related('userprofile')[:20]
    
    @classmethod
    def get_user_statistics(cls, user: User) -> Dict[str, Any]:
        """
        Get user statistics for display.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with user statistics
        """
        from purplex.problems_app.models import UserProgress, PromptSubmission
        
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
        
        # Get progress statistics
        progress = UserProgress.objects.filter(user=user).aggregate(
            problems_attempted=Count('id'),
            problems_solved=Count('id', filter=Q(solved=True)),
            avg_attempts=Avg('attempts')
        )
        stats.update(progress)
        
        # Get submission count
        stats['total_submissions'] = PromptSubmission.objects.filter(user=user).count()
        
        return stats
    
    @classmethod
    @transaction.atomic
    def delete_user_data(cls, user: User) -> None:
        """
        Delete all user data (for GDPR compliance).
        
        Args:
            user: User instance
        """
        # Delete all related data
        from purplex.problems_app.models import (
            UserProgress, PromptSubmission, CourseEnrollment
        )
        
        # Delete progress
        UserProgress.objects.filter(user=user).delete()
        
        # Delete submissions
        PromptSubmission.objects.filter(user=user).delete()
        
        # Delete enrollments
        CourseEnrollment.objects.filter(user=user).delete()
        
        # Delete profile and user
        try:
            user.userprofile.delete()
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