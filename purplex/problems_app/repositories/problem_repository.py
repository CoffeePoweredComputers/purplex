"""
Repository for Problem and ProblemSet model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Count, Prefetch
from django.contrib.auth.models import User

from purplex.problems_app.models import (
    Problem, ProblemSet, ProblemSetMembership, 
    ProblemCategory, TestCase
)
from .base_repository import BaseRepository


class ProblemRepository(BaseRepository):
    """
    Repository for all Problem-related database queries.
    
    This repository handles all data access for problems,
    problem sets, test cases, and categories.
    """
    
    model_class = Problem
    
    @classmethod
    def get_problem_by_slug(cls, slug: str) -> Optional[Problem]:
        """Get a problem by its slug."""
        return Problem.objects.filter(slug=slug).first()
    
    @classmethod
    def get_all_problems(cls) -> List[Problem]:
        """Get all problems with optimizations."""
        return list(
            Problem.objects.all().select_related(
                'created_by'
            ).prefetch_related(
                'categories'
            ).order_by('-created_at')
        )
    
    @classmethod
    def get_active_problems(cls) -> List[Problem]:
        """Get all active (non-draft) problems."""
        return list(
            Problem.objects.filter(
                is_active=True
            ).select_related(
                'created_by'
            ).prefetch_related(
                'categories'
            ).order_by('-created_at')
        )
    
    @classmethod
    def get_problems_by_category(cls, category: ProblemCategory) -> List[Problem]:
        """Get all problems in a specific category."""
        return list(
            Problem.objects.filter(
                categories=category
            ).select_related('created_by').order_by('title')
        )
    
    @classmethod
    def get_problems_by_difficulty(cls, difficulty: int) -> List[Problem]:
        """Get problems by difficulty level."""
        return list(
            Problem.objects.filter(
                difficulty=difficulty
            ).select_related('created_by').prefetch_related('categories').order_by('title')
        )
    
    @classmethod
    def search_problems(cls, query: str) -> List[Problem]:
        """Search problems by title or description."""
        return list(
            Problem.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query),
                is_active=True
            ).select_related('created_by').prefetch_related('categories')
        )
    
    @classmethod
    def get_problem_with_test_cases(cls, slug: str) -> Optional[Problem]:
        """Get a problem with all its test cases prefetched."""
        return Problem.objects.prefetch_related('test_cases').filter(
            slug=slug
        ).first()
    
    @classmethod
    def get_problem_test_cases(cls, problem: Problem, include_hidden: bool = False) -> List[TestCase]:
        """Get test cases for a problem."""
        queryset = TestCase.objects.filter(problem=problem)
        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)
        return list(queryset.order_by('id'))
    
    @classmethod
    def create_test_case(cls, problem: Problem, **kwargs) -> TestCase:
        """Create a test case for a problem."""
        return TestCase.objects.create(problem=problem, **kwargs)
    
    @classmethod
    def bulk_create_test_cases(cls, test_cases: List[TestCase]) -> List[TestCase]:
        """Bulk create test cases."""
        return list(TestCase.objects.bulk_create(test_cases))
    
    @classmethod
    def delete_test_cases(cls, problem: Problem) -> int:
        """Delete all test cases for a problem."""
        deleted, _ = TestCase.objects.filter(problem=problem).delete()
        return deleted
    
    # ProblemSet methods
    @classmethod
    def get_all_problem_sets(cls) -> List[ProblemSet]:
        """Get all problem sets."""
        return list(
            ProblemSet.objects.all().select_related(
                'created_by'
            ).annotate(
                problem_count=Count('problemsetmembership')
            ).order_by('-created_at')
        )
    
    @classmethod
    def get_problem_set_by_slug(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set by slug."""
        return ProblemSet.objects.filter(slug=slug).first()
    
    @classmethod
    def get_problem_set_with_problems(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set with all its problems prefetched."""
        return ProblemSet.objects.prefetch_related(
            Prefetch(
                'problemsetmembership_set',
                queryset=ProblemSetMembership.objects.select_related(
                    'problem'
                ).prefetch_related('problem__categories').order_by('order')
            )
        ).filter(slug=slug).first()
    
    @classmethod
    def get_problems_in_set(cls, problem_set: ProblemSet) -> List[Problem]:
        """Get all problems in a problem set, ordered."""
        return list(
            Problem.objects.filter(
                problem_set_memberships__problem_set=problem_set
            ).prefetch_related(
                'categories'
            ).order_by('problem_set_memberships__order')
        )
    
    @classmethod
    def get_problem_sets_containing_problem(cls, problem: Problem) -> List[ProblemSet]:
        """Get all problem sets that contain a specific problem."""
        return list(
            ProblemSet.objects.filter(
                memberships__problem=problem
            ).distinct()
        )
    
    @classmethod
    def add_problem_to_set(cls, problem: Problem, problem_set: ProblemSet, 
                          order: int = 0, weight: float = 1.0) -> ProblemSetMembership:
        """Add a problem to a problem set."""
        return ProblemSetMembership.objects.create(
            problem=problem,
            problem_set=problem_set,
            order=order,
            weight=weight
        )
    
    @classmethod
    def remove_problem_from_set(cls, problem: Problem, problem_set: ProblemSet) -> bool:
        """Remove a problem from a problem set."""
        deleted, _ = ProblemSetMembership.objects.filter(
            problem=problem,
            problem_set=problem_set
        ).delete()
        return deleted > 0
    
    @classmethod
    def update_problem_order_in_set(cls, problem: Problem, problem_set: ProblemSet, 
                                   new_order: int) -> bool:
        """Update the order of a problem in a set."""
        updated = ProblemSetMembership.objects.filter(
            problem=problem,
            problem_set=problem_set
        ).update(order=new_order)
        return updated > 0
    
    @classmethod
    def problem_in_set(cls, problem: Problem, problem_set: ProblemSet) -> bool:
        """Check if a problem is in a problem set."""
        return ProblemSetMembership.objects.filter(
            problem=problem,
            problem_set=problem_set
        ).exists()
    
    @classmethod
    def get_membership(cls, problem: Problem, problem_set: ProblemSet) -> Optional[ProblemSetMembership]:
        """Get the membership relationship between a problem and set."""
        return ProblemSetMembership.objects.filter(
            problem=problem,
            problem_set=problem_set
        ).first()
    
    # Category methods
    @classmethod
    def get_all_categories(cls) -> List[ProblemCategory]:
        """Get all problem categories."""
        return list(
            ProblemCategory.objects.all().annotate(
                problem_count=Count('problems')
            ).order_by('name')
        )
    
    @classmethod
    def get_category_by_slug(cls, slug: str) -> Optional[ProblemCategory]:
        """Get a category by slug."""
        return ProblemCategory.objects.filter(slug=slug).first()
    
    @classmethod
    def create_category(cls, **kwargs) -> ProblemCategory:
        """Create a new category."""
        return ProblemCategory.objects.create(**kwargs)
    
    @classmethod
    def search_categories(cls, query: str) -> List[ProblemCategory]:
        """Search categories by name or description."""
        return list(
            ProblemCategory.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        )
    
    @classmethod
    def find_category_by_exact_name(cls, name: str) -> Optional[ProblemCategory]:
        """Find a category by exact name (case-insensitive)."""
        return ProblemCategory.objects.filter(name__iexact=name).first()
    
    @classmethod
    def get_user_created_problems(cls, user: User) -> List[Problem]:
        """Get all problems created by a specific user."""
        return list(
            Problem.objects.filter(
                created_by=user
            ).prefetch_related('categories').order_by('-created_at')
        )
    
    @classmethod
    def get_user_created_problem_sets(cls, user: User) -> List[ProblemSet]:
        """Get all problem sets created by a specific user."""
        return list(
            ProblemSet.objects.filter(
                created_by=user
            ).annotate(
                problem_count=Count('problemsetmembership')
            ).order_by('-created_at')
        )
    
    @classmethod
    def count_problems_by_difficulty(cls) -> Dict[int, int]:
        """Get count of problems grouped by difficulty."""
        counts = Problem.objects.filter(
            is_active=True
        ).values('difficulty').annotate(
            count=Count('id')
        )
        return {item['difficulty']: item['count'] for item in counts}
    
    @classmethod
    def count_problems_in_set(cls, problem_set: ProblemSet) -> int:
        """
        Count the number of problems in a problem set.
        
        Args:
            problem_set: The problem set to count problems for
            
        Returns:
            Number of problems in the set
        """
        return problem_set.problems.count()
    
    @classmethod
    def get_problem_test_case_by_id(cls, problem: Problem, test_case_id: int, include_hidden: bool = False) -> Optional[TestCase]:
        """Get a specific test case for a problem by ID."""
        queryset = TestCase.objects.filter(problem=problem, id=test_case_id)
        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)
        return queryset.first()
    
    @classmethod
    def update_problem(cls, problem: Problem, **kwargs) -> Problem:
        """Update a problem with given fields."""
        for attr, value in kwargs.items():
            setattr(problem, attr, value)
        problem.save()
        return problem
    
    @classmethod
    def set_problem_sets(cls, problem: Problem, problem_sets: List[ProblemSet]) -> None:
        """Set the problem sets for a problem."""
        problem.problem_sets.set(problem_sets)