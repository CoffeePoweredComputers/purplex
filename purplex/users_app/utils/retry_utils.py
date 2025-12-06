"""
Retry utilities for handling database connection issues and other transient failures.
Includes exponential backoff and circuit breaker patterns.
"""

import time
import logging
import random
from functools import wraps
from typing import Tuple, Type, Callable, Any
from django.db import OperationalError, DatabaseError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: Type[Exception] = OperationalError
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == self.OPEN:
            if self._should_attempt_recovery():
                self.state = self.HALF_OPEN
            else:
                raise OperationalError("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure > timedelta(seconds=self.recovery_timeout)

    def _on_success(self):
        """Handle successful call."""
        if self.state == self.HALF_OPEN:
            logger.info("Circuit breaker recovered, closing circuit")

        self.failure_count = 0
        self.state = self.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
        elif self.state == self.HALF_OPEN:
            self.state = self.OPEN
            logger.warning("Circuit breaker reopened after failure in half-open state")


# Global circuit breaker for database operations
db_circuit_breaker = CircuitBreaker(
    failure_threshold=10,
    recovery_timeout=30,
    expected_exception=OperationalError
)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retriable_exceptions: Tuple[Type[Exception], ...] = (OperationalError, DatabaseError)
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        retriable_exceptions: Exceptions that trigger retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    # Use circuit breaker if this is a database operation
                    if attempt == 0:
                        # First attempt, just try normally
                        return func(*args, **kwargs)
                    else:
                        # Retry attempt, add logging
                        logger.debug(f"Retry attempt {attempt} for {func.__name__}")
                        return func(*args, **kwargs)

                except retriable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate next delay with exponential backoff
                    if jitter:
                        # Add random jitter (0.5x to 1.5x the delay)
                        jittered_delay = delay * (0.5 + random.random())
                    else:
                        jittered_delay = delay

                    # Cap at max delay
                    sleep_time = min(jittered_delay, max_delay)

                    logger.warning(
                        f"Retriable error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )

                    time.sleep(sleep_time)

                    # Exponential backoff for next iteration
                    delay *= backoff_factor

                except Exception as e:
                    # Non-retriable exception, propagate immediately
                    logger.error(f"Non-retriable error in {func.__name__}: {e}")
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator
