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
    pass
import os
import sys
import hmac
import secrets
import time

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

                # Initialize Firebase Admin SDK
                if not hasattr(settings, '_firebase_initialized'):
                    try:
                        # Get Firebase credentials path from config or environment
                        firebase_path = config.firebase_credentials_path or os.environ.get('FIREBASE_CREDENTIALS_PATH', '/app/firebase-credentials.json')
                        cred = credentials.Certificate(firebase_path)
                        initialize_app(cred)
                        settings._firebase_initialized = True
                        logger.info(f"Firebase initialized with credentials from {firebase_path}")
                    except Exception as e:
                        logger.error(f"Firebase initialization error: {e}")
                        raise
                
                cls._firebase_auth = auth
            except ImportError:
                logger.error("firebase-admin not installed. Install it for production use.")
                raise
        
        cls._firebase_initialized = True
        return cls._firebase_auth

    @classmethod
    def check_token_expiry(cls, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if token needs refresh based on expiration time.

        Args:
            decoded_token: Decoded Firebase token with 'exp' field

        Returns:
            Dict with: {
                'needs_refresh': bool,
                'expires_in': int (seconds),
                'expires_at': int (unix timestamp)
            }
        """
        exp = decoded_token.get('exp', 0)
        now = int(time.time())
        expires_in = exp - now

        # Recommend refresh if less than 5 minutes remaining
        needs_refresh = expires_in < 300

        return {
            'needs_refresh': needs_refresh,
            'expires_in': expires_in,
            'expires_at': exp
        }

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
                # Validate token expiry with grace period support
                # Firebase tokens have an 'exp' field with Unix timestamp
                token_exp = cached_data.get('exp', 0)
                current_time = time.time()
                firebase_uid = cached_data.get('uid')

                if token_exp > current_time:
                    # Token is valid - normal path
                    user = cls.get_cached_user(firebase_uid)

                    # Add expiry metadata to cached token
                    expiry_info = cls.check_token_expiry(cached_data)
                    cached_data_with_expiry = {**cached_data, **expiry_info}

                    # Log cache hit for monitoring
                    logger.debug(f"Token cache hit for user {firebase_uid}")

                    return (user, cached_data_with_expiry)
                else:
                    # Token expired - check grace period
                    time_since_expiry = current_time - token_exp
                    grace_period_seconds = getattr(settings, 'FIREBASE_GRACE_PERIOD_SECONDS', 600)

                    if time_since_expiry < grace_period_seconds:
                        # Within grace period - accept with warning
                        # This enables graceful degradation during Firebase API outages
                        logger.warning(
                            f"Accepting expired token for user {firebase_uid} "
                            f"within grace period (expired {int(time_since_expiry)}s ago, "
                            f"{int(grace_period_seconds - time_since_expiry)}s remaining)"
                        )

                        user = cls.get_cached_user(firebase_uid)

                        # Add grace period metadata
                        expiry_info = cls.check_token_expiry(cached_data)
                        cached_data_with_expiry = {
                            **cached_data,
                            **expiry_info,
                            'in_grace_period': True,
                            'grace_period_remaining': int(grace_period_seconds - time_since_expiry),
                            'expired_since': int(time_since_expiry)
                        }

                        return (user, cached_data_with_expiry)
                    else:
                        # Expired beyond grace period - delete and re-verify
                        cache.delete(cache_key)
                        logger.debug(
                            f"Cached token expired beyond grace period for hash {token_hash} "
                            f"(expired {int(time_since_expiry)}s ago)"
                        )
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

            # Cache the successful result to align with frontend refresh schedule
            # Frontend refreshes 5 min before 1-hour expiry (at T=55min)
            # This ensures backend cache is valid when frontend uses new token
            try:
                cache_ttl = getattr(settings, 'FIREBASE_TOKEN_CACHE_TTL', 3300)
                cache.set(cache_key, decoded_token, cache_ttl)
                logger.debug(f"Cached token for user {firebase_uid} (TTL: {cache_ttl // 60} min)")
            except Exception as e:
                # Cache write failed, continue without caching
                logger.warning(f"Cache write failed: {e}")

            # Check token expiry and add metadata
            expiry_info = cls.check_token_expiry(decoded_token)

            # Log authentication in development
            if config.is_development:
                logger.debug(f"Authenticated user: {user.username} (email: {email})")
                if expiry_info['needs_refresh']:
                    logger.debug(f"Token expiring soon: {expiry_info['expires_in']}s remaining")

            # Return user and token with expiry metadata
            token_with_expiry = {**decoded_token, **expiry_info}
            return (user, token_with_expiry)

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
        Uses Django cache (which already has correct Redis authentication).

        Args:
            user: Authenticated Django user

        Returns:
            Session token for SSE connection
        """
        from django.core.cache import cache

        # Generate secure random token
        session_token = secrets.token_urlsafe(32)

        logger.info(f"🔑 Creating SSE session for user {user.username} (ID: {user.id})")
        logger.info(f"   Token preview: {session_token[:10]}...{session_token[-10:]}")

        # Store session data in Django cache with 5-minute TTL
        session_key = f"sse_session:{session_token}"
        session_data = {
            'user_id': user.id,
            'username': user.username,
            'created_at': time.time()
        }

        # Set with 5-minute expiration (Django cache handles TTL)
        try:
            cache.set(session_key, session_data, 300)  # 5 minutes

            # Verify it was stored
            verify = cache.get(session_key)
            if verify:
                logger.info(f"✅ SSE session stored successfully in cache")
                logger.info(f"   Key: {session_key}")
            else:
                logger.error(f"❌ Failed to store SSE session in cache!")
        except Exception as e:
            logger.error(f"❌ Cache error creating SSE session: {e}")
            raise

        return session_token
    
    @classmethod
    def validate_sse_session(cls, session_token: str) -> Optional[User]:
        """
        Validate an SSE session token and return the associated user.
        Uses Django cache (which already has correct Redis authentication).

        Args:
            session_token: SSE session token

        Returns:
            User instance if valid, None otherwise
        """
        from django.core.cache import cache

        if not session_token:
            logger.warning("🔒 SSE session validation: No token provided")
            return None

        logger.info(f"🔍 Validating SSE session token: {session_token[:10]}...{session_token[-10:]}")

        session_key = f"sse_session:{session_token}"

        # Get session data from Django cache
        try:
            session_data = cache.get(session_key)
            if not session_data:
                logger.error(f"❌ SSE session NOT FOUND in cache")
                logger.error(f"   Token: {session_token[:10]}...{session_token[-10:]}")
                logger.error(f"   Key: {session_key}")
                return None

            logger.info(f"✅ SSE session found in cache")

            # session_data is already a dict (cache.get deserializes automatically)
            user_id = session_data.get('user_id')
            logger.info(f"📋 Session data: user_id={user_id}")

            # Refresh TTL on activity (sliding expiration)
            cache.touch(session_key, 300)
            logger.info(f"⏱️ Refreshed TTL for session (300 seconds)")

            # Get user from database using repository
            user = UserRepository.get_by_id(user_id)
            if not user:
                logger.error(f"❌ User {user_id} NOT FOUND in database for valid SSE session")
                cache.delete(session_key)  # Clean up orphaned session
                return None

            logger.info(f"✅ SSE session validated successfully for user: {user.username}")
            return user

        except Exception as e:
            logger.error(f"❌ Cache error validating SSE session: {e}")
            # Clean up invalid session
            try:
                cache.delete(session_key)
            except:
                pass
            return None
    
    @classmethod
    def revoke_sse_session(cls, session_token: str) -> bool:
        """
        Revoke an SSE session token.
        Uses Django cache (which already has correct Redis authentication).

        Args:
            session_token: SSE session token to revoke

        Returns:
            True if revoked, False if not found
        """
        from django.core.cache import cache

        if not session_token:
            return False

        session_key = f"sse_session:{session_token}"

        try:
            # Django cache.delete returns None, check if key existed first
            existed = cache.get(session_key) is not None
            cache.delete(session_key)
            if existed:
                logger.info(f"Revoked SSE session")
            return existed
        except Exception as e:
            logger.error(f"❌ Error revoking SSE session: {e}")
            return False