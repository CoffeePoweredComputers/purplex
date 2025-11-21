"""
Rate limiting service for authentication endpoints.
Prevents brute force attacks and excessive API usage.
"""
import redis
import time
import logging
from typing import Optional
from django.conf import settings
from purplex.utils.redis_client import get_rate_limit_client

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Redis-based rate limiting for authentication endpoints.
    """
    
    # Default rate limits
    AUTH_ATTEMPTS_PER_MINUTE = 10
    AUTH_ATTEMPTS_PER_HOUR = 100
    SERVICE_ACCOUNT_ATTEMPTS_PER_MINUTE = 5
    SSE_TOKEN_REQUESTS_PER_MINUTE = 20

    @classmethod
    def check_auth_rate_limit(cls, identifier: str) -> bool:
        """
        Check if authentication attempt is within rate limits.

        Args:
            identifier: IP address or user identifier

        Returns:
            True if within limits, False if rate limited
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            # Check per-minute limit
            minute_key = f"auth_limit:minute:{identifier}:{int(time.time() // 60)}"
            minute_count = redis_client.incr(minute_key)
            redis_client.expire(minute_key, 60)

            if minute_count > cls.AUTH_ATTEMPTS_PER_MINUTE:
                logger.warning(f"Auth rate limit exceeded (minute) for {identifier}")
                return False

            # Check per-hour limit
            hour_key = f"auth_limit:hour:{identifier}:{int(time.time() // 3600)}"
            hour_count = redis_client.incr(hour_key)
            redis_client.expire(hour_key, 3600)

            if hour_count > cls.AUTH_ATTEMPTS_PER_HOUR:
                logger.warning(f"Auth rate limit exceeded (hour) for {identifier}")
                return False

            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # Fail open: Allow authentication if Redis is temporarily unavailable
            # This prevents Redis outages from blocking all authentication
            logger.error(f"⚠️ Redis connection failed for rate limiting: {e}. Failing open (allowing request).")
            return True
    
    @classmethod
    def check_service_account_rate_limit(cls, identifier: str) -> bool:
        """
        Check if service account authentication attempt is within rate limits.
        More restrictive than regular auth.

        Args:
            identifier: IP address or service identifier

        Returns:
            True if within limits, False if rate limited
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            minute_key = f"service_auth_limit:{identifier}:{int(time.time() // 60)}"
            count = redis_client.incr(minute_key)
            redis_client.expire(minute_key, 60)

            if count > cls.SERVICE_ACCOUNT_ATTEMPTS_PER_MINUTE:
                logger.warning(f"Service account rate limit exceeded for {identifier}")
                return False

            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"⚠️ Redis connection failed for service account rate limiting: {e}. Failing open.")
            return True
    
    @classmethod
    def check_sse_token_rate_limit(cls, user_id: int) -> bool:
        """
        Check if SSE token request is within rate limits.

        Args:
            user_id: User ID requesting SSE token

        Returns:
            True if within limits, False if rate limited
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            minute_key = f"sse_token_limit:{user_id}:{int(time.time() // 60)}"
            count = redis_client.incr(minute_key)
            redis_client.expire(minute_key, 60)

            if count > cls.SSE_TOKEN_REQUESTS_PER_MINUTE:
                logger.warning(f"SSE token rate limit exceeded for user {user_id}")
                return False

            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"⚠️ Redis connection failed for SSE token rate limiting: {e}. Failing open.")
            return True
    
    @classmethod
    def record_failed_auth(cls, identifier: str) -> None:
        """
        Record a failed authentication attempt for tracking.

        Args:
            identifier: IP address or user identifier
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            # Track failed attempts with exponential backoff
            fail_key = f"auth_failures:{identifier}"
            failures = redis_client.incr(fail_key)

            # Exponential backoff: 1 min, 5 min, 15 min, 1 hour
            if failures <= 3:
                redis_client.expire(fail_key, 60)
            elif failures <= 6:
                redis_client.expire(fail_key, 300)
            elif failures <= 10:
                redis_client.expire(fail_key, 900)
            else:
                redis_client.expire(fail_key, 3600)

            logger.info(f"Failed auth attempt #{failures} for {identifier}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"⚠️ Redis connection failed while recording failed auth: {e}")
            # Continue - not critical if we can't record this
    
    @classmethod
    def is_blocked(cls, identifier: str) -> bool:
        """
        Check if an identifier is temporarily blocked due to too many failures.

        Args:
            identifier: IP address or user identifier

        Returns:
            True if blocked, False otherwise
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            fail_key = f"auth_failures:{identifier}"
            failures = redis_client.get(fail_key)

            if failures and int(failures) > 10:
                logger.warning(f"Identifier {identifier} is temporarily blocked")
                return True

            return False
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"⚠️ Redis connection failed while checking if blocked: {e}. Failing open.")
            return False  # Not blocked if we can't check
    
    @classmethod
    def reset_limits(cls, identifier: str) -> None:
        """
        Reset rate limits for an identifier (e.g., after successful auth).

        Args:
            identifier: IP address or user identifier
        """
        try:
            redis_client = get_rate_limit_client()  # Use centralized client

            # Clear failure counter on successful auth
            fail_key = f"auth_failures:{identifier}"
            redis_client.delete(fail_key)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"⚠️ Redis connection failed while resetting limits: {e}")
            # Continue - not critical if we can't reset
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: Django request object
            
        Returns:
            Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip