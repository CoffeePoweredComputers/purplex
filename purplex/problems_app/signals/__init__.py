"""
Signal handlers for the problems app.

Import signal handlers to ensure they're registered.
"""

# Import Celery signal handlers to register them
from .celery_signals import *  # noqa: F401, F403
