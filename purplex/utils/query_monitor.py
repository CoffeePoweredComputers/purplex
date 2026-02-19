"""
Query monitoring utility for development profiling.

Provides a context manager that counts Django ORM queries within a block.
Used in views/services to detect N+1 queries during development.
"""

import logging
from contextlib import contextmanager

from django.db import connection

logger = logging.getLogger(__name__)


@contextmanager
def query_counter(label: str = "", warning_threshold: int = 10):
    """
    Context manager that counts DB queries and logs a warning if threshold is exceeded.

    Usage:
        with query_counter("my_view", warning_threshold=5):
            # ... ORM queries ...

    Args:
        label: Human-readable label for the log message.
        warning_threshold: Number of queries above which a warning is logged.
    """
    initial_count = len(connection.queries)
    try:
        yield
    finally:
        final_count = len(connection.queries)
        query_count = final_count - initial_count
        if query_count > warning_threshold:
            logger.warning(
                "[QueryMonitor] %s executed %d queries (threshold: %d)",
                label,
                query_count,
                warning_threshold,
            )
