"""
Central authentication service - single source of truth for all authentication.
This is the ONLY place that handles Firebase authentication.
"""
from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
import hashlib
import logging

# Import models only for type hints
if TYPE_CHECKING:
    from django.db import transaction
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
from purplex.users_app.repositories import UserRepository, UserProfileRepository

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
                host=getattr(settings, 'REDIS_HOST', 'redis'),
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
        Authenticate a Firebase token and return user with caching.

        This is the ONLY method that verifies Firebase tokens.
        Handles both mock (dev) and real (prod) Firebase.
        Caches verified tokens for 5 minutes to reduce Firebase API calls.

        Args:
            token: Firebase ID token

        Returns:
            Tuple of (User instance, decoded token data)

        Raises:
            ValueError: If token is invalid or expired
        """
        if not token:
            raise ValueError("No token provided")

        # Generate secure cache key from token hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        cache_key = f"firebase:token:{token_hash}"

        # Try to get from cache
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                # Validate token hasn't expired
                # Firebase tokens have an 'exp' field with Unix timestamp
                if cached_data.get('exp', 0) > time.time():
                    # Get user from cache or database
                    firebase_uid = cached_data['uid']
                    user = cls.get_cached_user(firebase_uid)

                    # Log cache hit for monitoring
                    logger.debug(f"Token cache hit for user {firebase_uid}")

                    return (user, cached_data)
                else:
                    # Token expired, clear from cache
                    cache.delete(cache_key)
                    logger.debug(f"Cached token expired for hash {token_hash}")
        except Exception as e:
            # Cache read failed, fall back to Firebase verification
            logger.warning(f"Cache read failed, falling back to Firebase: {e}")

        # Cache miss or error - verify with Firebase
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

            # Cache the successful result for 5 minutes
            try:
                cache.set(cache_key, decoded_token, 300)  # 5 minutes
                logger.debug(f"Cached token for user {firebase_uid}")
            except Exception as e:
                # Cache write failed, continue without caching
                logger.warning(f"Cache write failed: {e}")

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
    def get_cached_user(cls, firebase_uid: str) -> User:
        """
        Get a user from cache or database.

        Caches User objects for 10 minutes to reduce database queries.

        Args:
            firebase_uid: Firebase user ID

        Returns:
            Django User instance

        Raises:
            ValueError: If user not found
        """
        # User cache key (10 minute TTL)
        user_cache_key = f"firebase:user:{firebase_uid}"

        # Try to get from cache
        try:
            cached_user_id = cache.get(user_cache_key)
            if cached_user_id:
                # Try to get user from database by cached ID
                user = UserRepository.get_by_id(cached_user_id)
                if user:
                    logger.debug(f"User cache hit for Firebase UID {firebase_uid}")
                    return user
                else:
                    # User deleted, clear cache
                    cache.delete(user_cache_key)
                    logger.debug(f"Cached user no longer exists, cleared cache for {firebase_uid}")
        except Exception as e:
            logger.warning(f"User cache read failed: {e}")

        # Cache miss - get from database
        user_profile = UserProfileRepository.get_by_firebase_uid(firebase_uid)
        if not user_profile:
            raise ValueError(f"User not found for Firebase UID: {firebase_uid}")

        user = user_profile.user

        # Cache the user ID for 10 minutes
        try:
            cache.set(user_cache_key, user.id, 600)  # 10 minutes
            logger.debug(f"Cached user {user.username} for Firebase UID {firebase_uid}")
        except Exception as e:
            logger.warning(f"User cache write failed: {e}")

        return user

    @classmethod
    def clear_user_cache(cls, firebase_uid: str) -> None:
        """
        Clear cached user data when user info is updated.

        Args:
            firebase_uid: Firebase user ID to clear from cache
        """
        user_cache_key = f"firebase:user:{firebase_uid}"
        try:
            cache.delete(user_cache_key)
            logger.debug(f"Cleared user cache for Firebase UID {firebase_uid}")
        except Exception as e:
            logger.warning(f"Failed to clear user cache: {e}")

    @classmethod
    def get_or_create_user(cls, firebase_uid: str, email: str, display_name: str) -> User:
        """
        Get existing user or create new one using Django's race-condition-safe get_or_create.

        This method avoids database locking bottlenecks by using Django's built-in
        get_or_create pattern which handles race conditions through database constraints.
        Includes retry logic for handling connection pool exhaustion.

        Args:
            firebase_uid: Firebase user ID
            email: User's email address
            display_name: User's display name

        Returns:
            Django User instance
        """
        import time
        from purplex.users_app.utils.retry_utils import retry_with_backoff

        start_time = time.time()

        # Wrap the repository call with retry logic for connection pool issues
        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.05,
            max_delay=2.0,
            backoff_factor=2.0
        )
        def get_or_create_with_retry():
            return UserProfileRepository.get_or_create_with_user(
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name
            )

        # Get or create the user profile and associated user with retry logic
        user_profile, user = get_or_create_with_retry()

        # Update user info if profile existed but info changed
        if not user_profile.was_created:
            cls._update_user_if_needed(user, email, display_name)

        # Apply test user permissions in development for new users
        if user_profile.was_created and config.is_development and email:
            cls._apply_test_user_permissions(user, user_profile, email)

        # Log slow operations for monitoring
        duration = time.time() - start_time
        if duration > 0.1:  # Log operations taking more than 100ms
            logger.warning(f"Slow user creation/lookup: {duration:.3f}s for {firebase_uid}")

        if user_profile.was_created:
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
        
        # Ensure username is unique using repository
        username = username_base
        counter = 1
        while UserRepository.username_exists(username):
            username = f"{username_base}{counter}"
            counter += 1
        
        # Create the Django user using repository
        user = UserRepository.create(
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

            # Clear user cache when user info is updated
            user_profile = UserProfileRepository.get_by_user_id(user.id)
            if user_profile and user_profile.firebase_uid:
                cls.clear_user_cache(user_profile.firebase_uid)
    
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
        
        # Get or create service user using repository
        service_user = UserRepository.get_service_account()
        if not service_user:
            if config.is_development:
                # Create service account in development using repository
                service_user = UserRepository.create(
                    username='service_account',
                    email='service@purplex.local',
                    is_staff=True
                )
                UserProfileRepository.create(
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
            
            # Get user from database using repository
            user = UserRepository.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            return user
            
        except (json.JSONDecodeError, ValueError) as e:
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