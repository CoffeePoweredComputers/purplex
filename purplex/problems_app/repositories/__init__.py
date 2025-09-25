"""
Repository layer for data access.

This module provides a clean separation between business logic (services)
and data access (repositories). All database queries should go through
these repositories.
"""

from .base_repository import BaseRepository
from .course_repository import CourseRepository
from .problem_repository import ProblemRepository
from .hint_repository import HintRepository
from .progress_repository import ProgressRepository
from .problem_set_membership_repository import ProblemSetMembershipRepository
from .test_case_repository import TestCaseRepository
from .problem_category_repository import ProblemCategoryRepository

# New dedicated repositories
from .course_problem_set_repository import CourseProblemSetRepository
from .user_progress_repository import UserProgressRepository
from .problem_set_repository import ProblemSetRepository
from .progress_snapshot_repository import ProgressSnapshotRepository
from .course_enrollment_repository import CourseEnrollmentRepository
from .problem_hint_repository import ProblemHintRepository
from .user_problem_set_progress_repository import UserProblemSetProgressRepository

__all__ = [
    'BaseRepository',
    'CourseRepository',
    'ProblemRepository',
    'HintRepository',
    'ProgressRepository',
    'ProblemSetMembershipRepository',
    'TestCaseRepository',
    'ProblemCategoryRepository',
    # New dedicated repositories
    'CourseProblemSetRepository',
    'UserProgressRepository',
    'ProblemSetRepository',
    'ProgressSnapshotRepository',
    'CourseEnrollmentRepository',
    'ProblemHintRepository',
    'UserProblemSetProgressRepository',
]