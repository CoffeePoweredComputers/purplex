"""
Query monitoring utilities for performance debugging.

This module provides tools to track and log database query counts,
helping identify N+1 query problems and other performance issues.
"""

import logging
import functools
from contextlib import contextmanager
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


@contextmanager
def query_counter(operation_name: str, warning_threshold: int = 10):
    """
    Context manager to count database queries within a block.

    Args:
        operation_name: Name to identify this operation in logs
        warning_threshold: Number of queries before logging a warning

    Usage:
        with query_counter("CSV export", warning_threshold=5):
            # Your code here
            pass
    """
    if not settings.DEBUG:
        # Skip monitoring in production
        yield
        return

    initial_queries = len(connection.queries)

    try:
        yield
    finally:
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries

        # Always log in debug
        logger.debug(f"{operation_name} executed with {query_count} queries")

        # Log warning if threshold exceeded
        if query_count > warning_threshold:
            logger.warning(
                f"High query count detected in {operation_name}: "
                f"{query_count} queries (threshold: {warning_threshold})"
            )

            # Optionally log the actual queries for debugging
            if settings.DEBUG and query_count > warning_threshold * 2:
                logger.warning("Query details (showing last 10):")
                for query in connection.queries[-10:]:
                    logger.warning(f"  - {query['sql'][:100]}...")


def monitor_queries(warning_threshold: int = 10):
    """
    Decorator to monitor query count for a method or function.

    Args:
        warning_threshold: Number of queries before logging a warning

    Usage:
        @monitor_queries(warning_threshold=5)
        def my_function():
            # Your code here
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            with query_counter(operation_name, warning_threshold):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class QueryStats:
    """
    Class to collect and report query statistics.

    Usage:
        stats = QueryStats()
        stats.start()
        # Your code here
        report = stats.get_report()
        print(report)
    """

    def __init__(self):
        self.initial_queries = 0
        self.checkpoints = []

    def start(self):
        """Start tracking queries."""
        if settings.DEBUG:
            self.initial_queries = len(connection.queries)

    def checkpoint(self, label: str):
        """Create a checkpoint to track queries at this point."""
        if settings.DEBUG:
            current_queries = len(connection.queries)
            queries_since_last = current_queries - (
                self.checkpoints[-1]['total'] if self.checkpoints else self.initial_queries
            )
            self.checkpoints.append({
                'label': label,
                'total': current_queries,
                'since_last': queries_since_last
            })

    def get_report(self) -> str:
        """Get a formatted report of query statistics."""
        if not settings.DEBUG:
            return "Query monitoring disabled (not in DEBUG mode)"

        final_queries = len(connection.queries)
        total_queries = final_queries - self.initial_queries

        report_lines = [
            f"Query Statistics Report",
            f"=" * 50,
            f"Total Queries: {total_queries}",
            ""
        ]

        if self.checkpoints:
            report_lines.append("Checkpoints:")
            for checkpoint in self.checkpoints:
                report_lines.append(
                    f"  - {checkpoint['label']}: "
                    f"+{checkpoint['since_last']} queries "
                    f"(total: {checkpoint['total'] - self.initial_queries})"
                )

        if total_queries > 10:
            report_lines.append("")
            report_lines.append(f"⚠️  WARNING: High query count detected ({total_queries} queries)")

        return "\n".join(report_lines)


# Helper function for quick debugging
def log_query_count(label: str = "Operation"):
    """
    Quick helper to log current query count.

    Usage:
        # At any point in your code:
        log_query_count("After loading submissions")
    """
    if settings.DEBUG:
        query_count = len(connection.queries)
        logger.debug(f"{label}: {query_count} queries so far")