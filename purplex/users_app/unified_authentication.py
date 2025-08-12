"""
Unified authentication system for all environments.
This module provides a single authentication class that works consistently
across development, staging, and production environments.
"""
from rest_framework import authentication, exceptions
from django.contrib.auth.models import User
from django.conf import settings
import os
import sys

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.environment import config

# Import the appropriate Firebase module based on environment
if config.use_mock_firebase:
    from .mock_firebase import (
        MockFirebaseAuth as firebase_auth_module,
        InvalidIdTokenError,
        ExpiredIdTokenError
    )
    # Create a compatible interface
    class auth:
        verify_id_token = firebase_auth_module.verify_id_token
        InvalidIdTokenError = InvalidIdTokenError
        ExpiredIdTokenError = ExpiredIdTokenError
else:
    try:
        from firebase_admin import auth, credentials, initialize_app
        import firebase_admin
        
        # Initialize Firebase Admin SDK for production/staging
        if not hasattr(settings, '_firebase_initialized'):
            try:
                cred = credentials.Certificate(config.get_firebase_config()['credentials_path'])
                firebase_admin_app = initialize_app(cred)
                settings._firebase_initialized = True
            except Exception as e:
                print(f"Firebase initialization error: {e}")
                firebase_admin_app = None
    except ImportError:
        print("Warning: firebase-admin not installed. Install it for production use.")
        auth = None


from .models import UserProfile


class UnifiedAuthentication(authentication.BaseAuthentication):
    """
    Single authentication class for all environments.
    
    This class provides consistent authentication across development,
    staging, and production environments by using either mock or real
    Firebase based on configuration.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using Firebase tokens.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Tuple of (user, None) if authentication succeeds
            None if no authentication is attempted
            
        Raises:
            AuthenticationFailed: If authentication fails
        """
        # Get the auth header from the request
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # Check if auth header exists and starts with 'Bearer'
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        # Extract the token
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return None
        
        # Verify the token
        try:
            # Same code path for all environments
            decoded_token = auth.verify_id_token(token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            display_name = decoded_token.get('name', '')
            
            # Try to get existing user profile
            try:
                user_profile = UserProfile.objects.get(firebase_uid=firebase_uid)
                user = user_profile.user
                self._update_user_if_needed(user, email, display_name)
            except UserProfile.DoesNotExist:
                # Create new Django user and profile
                user = self._create_django_user(firebase_uid, email, display_name)
                user_profile = UserProfile.objects.create(
                    user=user,
                    firebase_uid=firebase_uid,
                    role='user'
                )
                
                # Apply test user permissions in development
                if config.is_development and email:
                    from .mock_firebase import MockFirebaseAuth
                    if email in MockFirebaseAuth.TEST_USERS:
                        test_data = MockFirebaseAuth.TEST_USERS[email]
                        user.is_staff = test_data['is_staff']
                        user.is_superuser = test_data['is_superuser']
                        user_profile.role = test_data['role']
                        user.save()
                        user_profile.save()
                        
                        if config.is_development:
                            print(f"Applied test user permissions for {email}: "
                                  f"staff={user.is_staff}, superuser={user.is_superuser}, "
                                  f"role={user_profile.role}")
            
            # Log authentication in development
            if config.is_development:
                print(f"Authenticated user: {user.username} (email: {email}, role: {user_profile.role})")
            
            return (user, None)
            
        except auth.InvalidIdTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid authentication token: {str(e)}')
        except auth.ExpiredIdTokenError:
            raise exceptions.AuthenticationFailed('Authentication token has expired')
        except Exception as e:
            if config.is_development:
                print(f"Authentication error: {e}")
                import traceback
                traceback.print_exc()
            raise exceptions.AuthenticationFailed('Authentication failed')
    
    def _create_django_user(self, firebase_uid, email, display_name):
        """
        Create a Django user for the given Firebase user.
        
        Args:
            firebase_uid: Firebase user ID
            email: User's email address
            display_name: User's display name
            
        Returns:
            Django User instance
        """
        # Generate username from email or firebase_uid
        if email:
            username_base = email.split('@')[0]
        else:
            username_base = firebase_uid[:15]
        
        # Ensure username is unique
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1
        
        # Create the Django user
        user = User.objects.create(
            username=username,
            email=email or '',
            first_name=display_name or ''
        )
        
        return user
    
    def _create_or_update_django_user(self, firebase_uid, email, display_name, user_profile):
        """
        Create or update a Django user for the given Firebase user.
        
        Args:
            firebase_uid: Firebase user ID
            email: User's email address
            display_name: User's display name
            user_profile: UserProfile instance
            
        Returns:
            Django User instance
        """
        # Generate username from email or firebase_uid
        if email:
            username_base = email.split('@')[0]
        else:
            username_base = firebase_uid[:15]
        
        # Ensure username is unique
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1
        
        # Create the Django user
        user = User.objects.create(
            username=username,
            email=email or '',
            first_name=display_name or ''
        )
        
        # In development, apply test user permissions if applicable
        if config.is_development and email:
            from .mock_firebase import MockFirebaseAuth
            if email in MockFirebaseAuth.TEST_USERS:
                test_data = MockFirebaseAuth.TEST_USERS[email]
                user.is_staff = test_data['is_staff']
                user.is_superuser = test_data['is_superuser']
                user_profile.role = test_data['role']
                user.save()
                
                if config.is_development:
                    print(f"Applied test user permissions for {email}: "
                          f"staff={user.is_staff}, superuser={user.is_superuser}, "
                          f"role={user_profile.role}")
        
        # Link user to profile
        user_profile.user = user
        user_profile.save()
        
        return user
    
    def _update_user_if_needed(self, user, email, display_name):
        """
        Update Django user if Firebase data has changed.
        
        Args:
            user: Django User instance
            email: Current email from Firebase
            display_name: Current display name from Firebase
        """
        updated = False
        
        if email and user.email != email:
            user.email = email
            updated = True
        
        if display_name and user.first_name != display_name:
            user.first_name = display_name
            updated = True
        
        if updated:
            user.save()
            if config.is_development:
                print(f"Updated user {user.username}: email={email}, name={display_name}")


class ServiceAccountAuthentication(authentication.BaseAuthentication):
    """
    Authentication for service accounts and internal services.
    
    This can be used for Celery workers, cron jobs, etc. that need
    to authenticate without Firebase tokens.
    """
    
    def authenticate(self, request):
        """
        Authenticate service accounts using API keys.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Tuple of (user, None) if authentication succeeds
            None if no authentication is attempted
        """
        # Check for service account header
        service_key = request.META.get('HTTP_X_SERVICE_KEY', '')
        
        if not service_key:
            return None
        
        # Validate service key
        valid_key = os.environ.get('SERVICE_ACCOUNT_KEY')
        if not valid_key or service_key != valid_key:
            return None
        
        # Return a service user
        # In production, this should be a dedicated service account
        try:
            service_user = User.objects.get(username='service_account')
        except User.DoesNotExist:
            if config.is_development:
                # Create service account in development
                service_user = User.objects.create(
                    username='service_account',
                    email='service@purplex.local',
                    is_staff=True
                )
                UserProfile.objects.create(
                    user=service_user,
                    firebase_uid='service-account',
                    role='service'
                )
            else:
                return None
        
        return (service_user, None)