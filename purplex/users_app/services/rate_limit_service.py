"""
Rate limiting service for authentication endpoints.
Prevents brute force attacks and excessive API usage.
"""
import redis
import time
import logging
from typing import Optional
from django.conf import settings

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
    
    _redis_client = None
    
    @classmethod
    def _get_redis_client(cls):
        """Get or create Redis client for rate limiting."""
        if cls._redis_client is None:
            cls._redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'redis'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=2,  # Use db=2 for rate limiting
                decode_responses=True
            )
        return cls._redis_client
    
    @classmethod
    def check_auth_rate_limit(cls, identifier: str) -> bool:
        """
        Check if authentication attempt is within rate limits.
        
        Args:
            identifier: IP address or user identifier
            
        Returns:
            True if within limits, False if rate limited
        """
        redis_client = cls._get_redis_client()
        
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
        redis_client = cls._get_redis_client()
        
        minute_key = f"service_auth_limit:{identifier}:{int(time.time() // 60)}"
        count = redis_client.incr(minute_key)
        redis_client.expire(minute_key, 60)
        
        if count > cls.SERVICE_ACCOUNT_ATTEMPTS_PER_MINUTE:
            logger.warning(f"Service account rate limit exceeded for {identifier}")
            return False
        
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
        redis_client = cls._get_redis_client()
        
        minute_key = f"sse_token_limit:{user_id}:{int(time.time() // 60)}"
        count = redis_client.incr(minute_key)
        redis_client.expire(minute_key, 60)
        
        if count > cls.SSE_TOKEN_REQUESTS_PER_MINUTE:
            logger.warning(f"SSE token rate limit exceeded for user {user_id}")
            return False
        
        return True
    
    @classmethod
    def record_failed_auth(cls, identifier: str) -> None:
        """
        Record a failed authentication attempt for tracking.
        
        Args:
            identifier: IP address or user identifier
        """
        redis_client = cls._get_redis_client()
        
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
    
    @classmethod
    def is_blocked(cls, identifier: str) -> bool:
        """
        Check if an identifier is temporarily blocked due to too many failures.
        
        Args:
            identifier: IP address or user identifier
            
        Returns:
            True if blocked, False otherwise
        """
        redis_client = cls._get_redis_client()
        
        fail_key = f"auth_failures:{identifier}"
        failures = redis_client.get(fail_key)
        
        if failures and int(failures) > 10:
            logger.warning(f"Identifier {identifier} is temporarily blocked")
            return True
        
        return False
    
    @classmethod
    def reset_limits(cls, identifier: str) -> None:
        """
        Reset rate limits for an identifier (e.g., after successful auth).
        
        Args:
            identifier: IP address or user identifier
        """
        redis_client = cls._get_redis_client()
        
        # Clear failure counter on successful auth
        fail_key = f"auth_failures:{identifier}"
        redis_client.delete(fail_key)
    
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