"""
Celery tasks for Purplex problems app.

This module contains the new clean pipeline tasks.
"""

# Import the main pipeline task
from .pipeline import execute_eipl_pipeline

__all__ = [
    "execute_eipl_pipeline",
]
