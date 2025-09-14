"""
Submissions app service module.

This module provides service classes for business logic
following the service layer pattern to separate business
logic from views.
"""

from .submission_service import SubmissionService

__all__ = [
    'SubmissionService',
]