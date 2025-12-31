"""
Centralized Redis client management for Purplex.

This module provides Redis clients for different use cases:
- Pub/Sub for task events and real-time updates (db=0)
- Rate limiting with isolated database (db=2)

Connection pooling and health checks are handled automatically.
No manual ping() needed - prevents connection pool leaks.

Usage:
    from purplex.utils.redis_client import get_pubsub_client, get_rate_limit_client

    # For pub/sub (task events, SSE)
    client = get_pubsub_client()
    client.publish(channel, message)

    # For rate limiting
    client = get_rate_limit_client()
    client.incr(key)
"""

import logging
import socket

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy-initialized Redis clients (module-level singletons)
_pubsub_client = None
_rate_limit_client = None


class RedisClientManager:
    """
    Centralized Redis client management with automatic connection pooling.

    This class manages singleton Redis clients for different use cases.
    Each client has its own connection pool with automatic health checks.

    Use the module-level convenience functions (get_pubsub_client, get_rate_limit_client)
    rather than calling this class directly.
    """

    @classmethod
    def get_pubsub_client(cls) -> redis.Redis:
        """
        Get Redis client for pub/sub operations (db=0).

        Used by:
        - Celery signal handlers (celery_signals.py)
        - Pipeline task progress events (pipeline.py)
        - SSE streaming views (sse.py - creates per-request clients)

        Returns:
            Redis client configured for pub/sub on db=0

        Note:
            This is a singleton. The same client instance is reused across calls.
            Connection pooling is handled internally by redis-py.
        """
        global _pubsub_client

        if _pubsub_client is None:
            _pubsub_client = cls._create_client(
                db=0, max_connections=10, purpose="pub/sub (task events)"
            )
            logger.info("✅ Created Redis pub/sub client (db=0, max_connections=10)")

        return _pubsub_client

    @classmethod
    def get_rate_limit_client(cls) -> redis.Redis:
        """
        Get Redis client for rate limiting operations (db=2).

        Used by:
        - Authentication rate limiting (rate_limit_service.py)
        - SSE token request rate limiting
        - Service account rate limiting

        Returns:
            Redis client configured for rate limiting on db=2

        Note:
            Uses db=2 for isolation from other Redis operations.
            Higher max_connections (20) to handle concurrent auth requests.
        """
        global _rate_limit_client

        if _rate_limit_client is None:
            _rate_limit_client = cls._create_client(
                db=2, max_connections=20, purpose="rate limiting"
            )
            logger.info(
                "✅ Created Redis rate limiting client (db=2, max_connections=20)"
            )

        return _rate_limit_client

    @classmethod
    def _create_client(cls, db: int, max_connections: int, purpose: str) -> redis.Redis:
        """
        Create a Redis client with proper connection pooling.

        Args:
            db: Redis database number (0, 1, 2, etc.)
            max_connections: Maximum connections in pool
            purpose: Description for logging (e.g., "pub/sub", "rate limiting")

        Returns:
            Configured Redis client with connection pool

        Connection Pool Features:
            - Automatic health checks every 30 seconds
            - TCP keepalive to detect dead connections
            - Connection recycling for stale connections
            - Max connections enforced to prevent pool exhaustion
        """
        client = redis.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            password=getattr(settings, "REDIS_PASSWORD", None),
            db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=max_connections,
            socket_keepalive=True,
            socket_keepalive_options={
                socket.TCP_KEEPIDLE: 1,  # Seconds before keepalive probes start
                socket.TCP_KEEPINTVL: 1,  # Seconds between keepalive probes
                socket.TCP_KEEPCNT: 3,  # Number of keepalive probes
            },
            health_check_interval=30,  # Automatic health checks every 30 seconds
        )

        logger.debug(
            f"Created Redis client for {purpose} (db={db}, max_conn={max_connections})"
        )
        return client

    @classmethod
    def reset_clients(cls):
        """
        Reset all cached clients (for testing).

        WARNING: Only use in tests or during graceful shutdown.
        This will close all existing connections and clear the cached clients.

        After calling this, the next call to get_pubsub_client() or
        get_rate_limit_client() will create fresh clients.
        """
        global _pubsub_client, _rate_limit_client

        if _pubsub_client:
            try:
                _pubsub_client.close()
                logger.debug("Closed pub/sub Redis client")
            except Exception as e:
                logger.warning(f"Error closing pub/sub client: {e}")
            _pubsub_client = None

        if _rate_limit_client:
            try:
                _rate_limit_client.close()
                logger.debug("Closed rate limit Redis client")
            except Exception as e:
                logger.warning(f"Error closing rate limit client: {e}")
            _rate_limit_client = None

        logger.info("Reset all Redis clients")


# Convenience functions for backward compatibility and ease of use
def get_pubsub_client() -> redis.Redis:
    """
    Get Redis client for pub/sub operations.

    Convenience function that calls RedisClientManager.get_pubsub_client().
    Use this in your code for cleaner imports.

    Returns:
        Redis client for pub/sub (db=0)
    """
    return RedisClientManager.get_pubsub_client()


def get_rate_limit_client() -> redis.Redis:
    """
    Get Redis client for rate limiting operations.

    Convenience function that calls RedisClientManager.get_rate_limit_client().
    Use this in your code for cleaner imports.

    Returns:
        Redis client for rate limiting (db=2)
    """
    return RedisClientManager.get_rate_limit_client()
