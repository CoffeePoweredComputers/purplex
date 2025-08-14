"""
Central authentication service - single source of truth for all authentication.
This is the ONLY place that handles Firebase authentication.
"""
from typing import Optional, Tuple, Dict, Any
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
import logging
import os
import sys
import hmac
import secrets
import json
import time
import redis

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.environment import config
from purplex.users_app.models import UserProfile

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Central authentication service - single source of truth.
    
    This service handles:
    - Token verification (Firebase or mock)
    - User creation and updates
    - Profile management
    - All authentication-related logic
    """
    
    # Cache for Firebase initialization
    _firebase_initialized = False
    _firebase_auth = None
    
    # Redis client for SSE session tokens
    _redis_client = None
    
    @classmethod
    def _get_redis_client(cls):
        """Get or create Redis client for SSE sessions."""
        if cls._redis_client is None:
            cls._redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=1,  # Use db=1 for SSE sessions
                decode_responses=True
            )
        return cls._redis_client
    
    @classmethod
    def _initialize_firebase(cls):
        """Initialize Firebase once and cache it."""
        if cls._firebase_initialized:
            return cls._firebase_auth
            
        if config.use_mock_firebase:
            # Use mock Firebase for development
            from purplex.users_app.mock_firebase import MockFirebaseAuth
            cls._firebase_auth = MockFirebaseAuth
        else:
            # Use real Firebase for production
            try:
                from firebase_admin import auth, credentials, initialize_app
                import firebase_admin
                
                # Initialize Firebase Admin SDK
                if not hasattr(settings, '_firebase_initialized'):
                    try:
                        cred = credentials.Certificate(config.get_firebase_config()['credentials_path'])
                        firebase_admin_app = initialize_app(cred)
                        settings._firebase_initialized = True
                    except Exception as e:
                        logger.error(f"Firebase initialization error: {e}")
                        raise
                
                cls._firebase_auth = auth
            except ImportError as e:
                logger.error("firebase-admin not installed. Install it for production use.")
                raise
        
        cls._firebase_initialized = True
        return cls._firebase_auth
    
    @classmethod
    def authenticate_token(cls, token: str) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate a Firebase token and return user.
        
        This is the ONLY method that verifies Firebase tokens.
        Handles both mock (dev) and real (prod) Firebase.
        
        Args:
            token: Firebase ID token
            
        Returns:
            Tuple of (User instance, decoded token data)
            
        Raises:
            ValueError: If token is invalid or expired
        """
        if not token:
            raise ValueError("No token provided")
        
        # Get Firebase auth module (mock or real)
        auth_module = cls._initialize_firebase()
        
        try:
            # Verify the token (same interface for mock and real)
            decoded_token = auth_module.verify_id_token(token)
            
            # Extract user information
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            display_name = decoded_token.get('name', '')
            
            # Get or create the user
            user = cls.get_or_create_user(firebase_uid, email, display_name)
            
            # Log authentication in development
            if config.is_development:
                logger.debug(f"Authenticated user: {user.username} (email: {email})")
            
            return (user, decoded_token)
            
        except Exception as e:
            # Handle different exception types - sanitize error messages
            error_name = e.__class__.__name__
            
            # Log detailed error for debugging
            logger.error(f"Authentication error - Type: {error_name}, Details: {e}")
            
            # Return generic error messages to client
            if 'InvalidIdTokenError' in error_name:
                raise ValueError("Invalid authentication credentials")
            elif 'ExpiredIdTokenError' in error_name:
                raise ValueError("Authentication credentials have expired")
            else:
                # Never expose internal error details to client
                raise ValueError("Authentication failed")
    
    @classmethod
    @transaction.atomic
    def get_or_create_user(cls, firebase_uid: str, email: str, display_name: str) -> User:
        """
        Get existing user or create new one.
        
        Uses database transaction to prevent race conditions.
        
        Args:
            firebase_uid: Firebase user ID
            email: User's email address
            display_name: User's display name
            
        Returns:
            Django User instance
        """
        # Try to get existing user profile
        try:
            user_profile = UserProfile.objects.select_for_update().get(firebase_uid=firebase_uid)
            user = user_profile.user
            
            # Update user info if changed
            cls._update_user_if_needed(user, email, display_name)
            
            return user
            
        except UserProfile.DoesNotExist:
            # Create new user
            user = cls._create_django_user(firebase_uid, email, display_name)
            
            # Create user profile
            user_profile = UserProfile.objects.create(
                user=user,
                firebase_uid=firebase_uid,
                role='user'
            )
            
            # Apply test user permissions in development
            if config.is_development and email:
                cls._apply_test_user_permissions(user, user_profile, email)
            
            logger.info(f"Created new user: {user.username} (Firebase UID: {firebase_uid})")
            return user
    
    @classmethod
    def _create_django_user(cls, firebase_uid: str, email: str, display_name: str) -> User:
        """
        Create a Django user with unique username.
        
        Args:
            firebase_uid: Firebase user ID
            email: User's email address
            display_name: User's display name
            
        Returns:
            New Django User instance
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
    
    @classmethod
    def _update_user_if_needed(cls, user: User, email: str, display_name: str) -> None:
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
            logger.debug(f"Updated user {user.username}: email={email}, name={display_name}")
    
    @classmethod
    def _apply_test_user_permissions(cls, user: User, user_profile: UserProfile, email: str) -> None:
        """
        Apply test user permissions in development environment.
        
        Args:
            user: Django User instance
            user_profile: UserProfile instance
            email: User's email address
        """
        from purplex.users_app.mock_firebase import MockFirebaseAuth
        
        if email in MockFirebaseAuth.TEST_USERS:
            test_data = MockFirebaseAuth.TEST_USERS[email]
            user.is_staff = test_data['is_staff']
            user.is_superuser = test_data['is_superuser']
            user_profile.role = test_data['role']
            user.save()
            user_profile.save()
            
            logger.debug(f"Applied test user permissions for {email}: "
                        f"staff={user.is_staff}, superuser={user.is_superuser}, "
                        f"role={user_profile.role}")
    
    @classmethod
    def verify_service_account(cls, service_key: str) -> Optional[User]:
        """
        Verify service account authentication.
        
        Args:
            service_key: Service account API key
            
        Returns:
            Service User instance or None
        """
        if not service_key:
            return None
        
        # Validate service key using constant-time comparison
        valid_key = os.environ.get('SERVICE_ACCOUNT_KEY')
        if not valid_key:
            return None
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(service_key, valid_key):
            # Add delay to prevent rapid enumeration attempts
            time.sleep(0.1)  # Small delay on failure
            
            # Log failed attempt for security monitoring
            logger.warning(f"Failed service account authentication attempt")
            return None
        
        # Log successful service account authentication
        logger.info(f"Service account authenticated successfully")
        
        # Get or create service user
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
        
        return service_user
    
    @classmethod
    def create_sse_session(cls, user: User) -> str:
        """
        Create a short-lived session token for SSE connections.
        
        This prevents token exposure in URLs by using temporary sessions.
        
        Args:
            user: Authenticated Django user
            
        Returns:
            Session token for SSE connection
        """
        # Generate secure random token
        session_token = secrets.token_urlsafe(32)
        
        # Store session data in Redis with 5-minute TTL
        redis_client = cls._get_redis_client()
        session_key = f"sse_session:{session_token}"
        session_data = {
            'user_id': user.id,
            'username': user.username,
            'created_at': time.time()
        }
        
        # Set with 5-minute expiration (auto-renewed on activity)
        redis_client.setex(
            session_key,
            300,  # 5 minutes
            json.dumps(session_data)
        )
        
        logger.info(f"Created SSE session for user {user.username}")
        return session_token
    
    @classmethod
    def validate_sse_session(cls, session_token: str) -> Optional[User]:
        """
        Validate an SSE session token and return the associated user.
        
        Args:
            session_token: SSE session token
            
        Returns:
            User instance if valid, None otherwise
        """
        if not session_token:
            return None
        
        redis_client = cls._get_redis_client()
        session_key = f"sse_session:{session_token}"
        
        # Get session data
        session_data_str = redis_client.get(session_key)
        if not session_data_str:
            logger.debug(f"SSE session not found or expired")
            return None
        
        try:
            session_data = json.loads(session_data_str)
            user_id = session_data.get('user_id')
            
            # Refresh TTL on activity (sliding expiration)
            redis_client.expire(session_key, 300)
            
            # Get user from database
            user = User.objects.get(id=user_id)
            return user
            
        except (json.JSONDecodeError, User.DoesNotExist) as e:
            logger.error(f"Invalid SSE session data: {e}")
            # Clean up invalid session
            redis_client.delete(session_key)
            return None
    
    @classmethod
    def revoke_sse_session(cls, session_token: str) -> bool:
        """
        Revoke an SSE session token.
        
        Args:
            session_token: SSE session token to revoke
            
        Returns:
            True if revoked, False if not found
        """
        if not session_token:
            return False
        
        redis_client = cls._get_redis_client()
        session_key = f"sse_session:{session_token}"
        
        result = redis_client.delete(session_key)
        if result:
            logger.info(f"Revoked SSE session")
        
        return bool(result)