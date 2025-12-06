from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAdmin, IsAuthenticated
from django.conf import settings

from .models import UserRole, LanguageChoice
from .authentication import PurplexAuthentication
from .services.authentication_service import AuthenticationService
from .services.rate_limit_service import RateLimitService
from .services.user_service import UserService
from .repositories import UserRepository, UserProfileRepository
import logging

logger = logging.getLogger(__name__)


class UserRoleView(APIView):
    """
    Get current authenticated user's information.

    This endpoint allows checking authentication status without requiring
    the user to already be authenticated (returns 401 instead of 403).
    """
    authentication_classes = [PurplexAuthentication]
    permission_classes = []  # Allow unauthenticated requests to check status

    def get(self, request):
        """Get current user info or return 401 if not authenticated"""
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"authenticated": False, "detail": "Not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Use UserService to get profile
        profile = UserService.get_user_profile(request.user)
        if not profile:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'authenticated': True,
            'username': request.user.username,
            'email': request.user.email,
            'role': profile.role,
            'is_admin': profile.is_admin,
            'firebase_uid': profile.firebase_uid,
            'language_preference': profile.language_preference
        })
            
class AuthStatusView(APIView):
    """View for validating a Firebase token and returning user information"""
    
    def post(self, request):
        auth = PurplexAuthentication()
        
        # Try to authenticate with the provided token
        try:
            user_auth_tuple = auth.authenticate(request)
            if user_auth_tuple is None:
                return Response({'authenticated': False, 'message': 'Invalid authentication token'}, status=401)
                
            user, _ = user_auth_tuple
            
            # Get user profile using UserService
            profile = UserService.get_user_profile(user)
            if not profile:
                return Response({'authenticated': False, 'message': 'User profile not found'}, status=404)
            
            return Response({
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': profile.role,
                    'is_admin': profile.is_admin,
                    'firebase_uid': profile.firebase_uid,
                    'language_preference': profile.language_preference
                }
            })
                
        except Exception as e:
            return Response({'authenticated': False, 'message': str(e)}, status=401)

class AdminUserManagementView(APIView):
    """View for admin users to manage other users' roles"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all users and their roles (admin only)"""
        # Use repository to get all users
        users = UserRepository.get_all_users()

        if settings.DEBUG and not UserProfileRepository.exists():
            print("Debug mode: Creating test user profiles")
            for user in users:
                # Check if profile already exists
                if not hasattr(user, 'profile'):
                    UserProfileRepository.create(
                        user=user,
                        firebase_uid=f"debug_firebase_{user.id}",
                        role=UserRole.ADMIN if user.is_superuser else UserRole.USER
                    )

        # Use repository to get all profiles
        user_profiles = UserProfileRepository.get_all_with_users()

        if user_profiles.exists():
            # Users with profiles exist, return them
            users_data = []
            for profile in user_profiles:
                users_data.append({
                    'id': profile.user.id,
                    'username': profile.user.username,
                    'email': profile.user.email,
                    'role': profile.role,
                    'is_active': profile.user.is_active
                })
            return Response(users_data)
        
        # No profiles exist, return users with default roles
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': 'user',  # Default role
                'is_active': user.is_active
            })
        return Response(users_data)

    def post(self, request, user_id):
        """Update a user's role (admin only)"""
        # Use repository to get user
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response({'error': 'User not found'}, status=404)

        # Use repository to get or create profile
        profile = UserProfileRepository.get_by_user(user)
        if not profile:
            # Create profile if it doesn't exist using repository
            profile = UserProfileRepository.create(
                user=user,
                firebase_uid=f"firebase_{user.id}",  # Temporary Firebase UID
                role=UserRole.USER
            )

        role = request.data.get('role')
        if role not in [UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.USER]:
            return Response({'error': 'Invalid role'}, status=400)

        profile.role = role
        profile.save()

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': profile.role
        })


class SSETokenView(APIView):
    """
    View for exchanging Firebase tokens for short-lived SSE session tokens.
    
    This prevents token exposure in URLs by providing temporary session tokens
    specifically for SSE connections.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a new SSE session token"""
        try:
            user = request.user
            
            # Check rate limit for SSE token creation
            if not RateLimitService.check_sse_token_rate_limit(user.id):
                logger.warning(f"SSE token rate limit exceeded for user {user.username}")
                return Response({
                    'error': 'Rate limit exceeded. Please wait before requesting another token.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Create SSE session token
            session_token = AuthenticationService.create_sse_session(user)
            
            return Response({
                'sse_token': session_token,
                'expires_in': 300  # 5 minutes
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to create SSE token: {e}")
            return Response({
                'error': 'Failed to create session token'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Revoke an SSE session token"""
        try:
            sse_token = request.data.get('sse_token')
            
            if not sse_token:
                return Response({
                    'error': 'SSE token required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Revoke the session
            revoked = AuthenticationService.revoke_sse_session(sse_token)
            
            if revoked:
                return Response({
                    'message': 'Session revoked successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Session not found or already expired'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Failed to revoke SSE token: {e}")
            return Response({
                'error': 'Failed to revoke session'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LanguagePreferenceView(APIView):
    """
    View for updating the current user's language preference.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Update the current user's language preference"""
        language = request.data.get('language_preference')

        if not language:
            return Response(
                {'error': 'language_preference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the language code
        valid_languages = [choice[0] for choice in LanguageChoice.choices]
        if language not in valid_languages:
            return Response(
                {'error': f'Invalid language. Must be one of: {", ".join(valid_languages)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get user profile
        profile = UserService.get_user_profile(request.user)
        if not profile:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update language preference
        profile.language_preference = language
        profile.save(update_fields=['language_preference'])

        logger.info(f"User {request.user.username} updated language preference to {language}")

        return Response({
            'language_preference': profile.language_preference,
            'message': 'Language preference updated successfully'
        })
