"""
User management service - handles all user-related business logic.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from django.contrib.auth.models import User
from purplex.users_app.models import UserProfile

# Import models only for type hints
if TYPE_CHECKING:
    pass
from purplex.users_app.repositories import UserRepository, UserProfileRepository
from purplex.problems_app.repositories import (
    UserProgressRepository,
    CourseEnrollmentRepository
)
from purplex.submissions.repositories.submission_repository import SubmissionRepository
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
    def get_user_profile(cls, user: User) -> Optional[UserProfile]:
        """
        Get user profile for a user.

        Args:
            user: User instance

        Returns:
            UserProfile instance or None
        """
        # Use repository to get profile instead of direct attribute access
        return UserProfileRepository.get_by_user(user)
    
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
    
