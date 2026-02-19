"""
Repository layer for data access.

This module provides a clean separation between business logic (services)
and data access (repositories). All database queries should go through
these repositories.
"""

from .base_repository import BaseRepository
from .course_enrollment_repository import CourseEnrollmentRepository

# New dedicated repositories
from .course_instructor_repository import CourseInstructorRepository
from .course_problem_set_repository import CourseProblemSetRepository
from .course_repository import CourseRepository
from .hint_repository import HintRepository
from .problem_category_repository import ProblemCategoryRepository
from .problem_repository import ProblemRepository
from .problem_set_membership_repository import ProblemSetMembershipRepository
from .problem_set_repository import ProblemSetRepository
from .progress_repository import ProgressRepository
from .test_case_repository import TestCaseRepository
from .user_progress_repository import UserProgressRepository

__all__ = [
    "BaseRepository",
    "CourseRepository",
    "ProblemRepository",
    "HintRepository",
    "ProgressRepository",
    "ProblemSetMembershipRepository",
    "TestCaseRepository",
    "ProblemCategoryRepository",
    # New dedicated repositories
    "CourseInstructorRepository",
    "CourseProblemSetRepository",
    "UserProgressRepository",
    "ProblemSetRepository",
    "CourseEnrollmentRepository",
]
