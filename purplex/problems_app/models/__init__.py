"""
Problems app models package.

This package provides all models for the problems_app.
Re-exports maintain backward compatibility with existing imports.

Model hierarchy:
    Problem (PolymorphicModel base)
    ├── StaticProblem (abstract) - no code execution
    │   ├── McqProblem
    │   └── RefuteProblem
    ├── SpecProblem (abstract) - NL -> LLM -> code -> test
    │   ├── EiplProblem
    │   ├── PromptProblem
    │   ├── DebugFixProblem
    │   ├── ProbeableCodeProblem
    │   └── ProbeableSpecProblem
    └── (Future) CodeProblem (abstract) - student code -> execute
"""

# Category
from .category import ProblemCategory

# Base problem model (polymorphic)
from .base import Problem, DEFAULT_COMPLETION_THRESHOLD

# Static problem types (no code execution)
from .static import StaticProblem, McqProblem, RefuteProblem

# Spec problem types (NL -> LLM -> code -> test)
from .spec import (
    SpecProblem, EiplProblem, PromptProblem, DebugFixProblem,
    ProbeableCodeProblem, ProbeableSpecProblem
)

# Test cases
from .test_case import TestCase

# Problem sets
from .problem_set import ProblemSet, ProblemSetMembership

# Courses
from .course import Course, CourseProblemSet, CourseEnrollment

# Progress tracking
from .progress import UserProgress, UserProblemSetProgress, ProgressSnapshot

# Hints
from .hint import ProblemHint

# Re-export all for backward compatibility
__all__ = [
    # Constants
    'DEFAULT_COMPLETION_THRESHOLD',
    # Category
    'ProblemCategory',
    # Problems - base
    'Problem',
    # Problems - static (no code)
    'StaticProblem',
    'McqProblem',
    'RefuteProblem',
    # Problems - spec (NL -> LLM -> code)
    'SpecProblem',
    'EiplProblem',
    'PromptProblem',
    'DebugFixProblem',
    'ProbeableCodeProblem',
    'ProbeableSpecProblem',
    # Test cases
    'TestCase',
    # Problem sets
    'ProblemSet',
    'ProblemSetMembership',
    # Courses
    'Course',
    'CourseProblemSet',
    'CourseEnrollment',
    # Progress
    'UserProgress',
    'UserProblemSetProgress',
    'ProgressSnapshot',
    # Hints
    'ProblemHint',
]
