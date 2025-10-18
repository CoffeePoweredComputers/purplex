"""Service layer for student-related business logic."""

import logging
from typing import List, Optional, TYPE_CHECKING
from django.http import Http404

from ..repositories import (
    ProblemRepository, 
    ProblemCategoryRepository,
    TestCaseRepository,
    ProblemSetMembershipRepository
)

# Import models only for type hints
if TYPE_CHECKING:
    from django.db.models import QuerySet
    from ..models import Problem, ProblemSet, ProblemCategory

logger = logging.getLogger(__name__)


class StudentService:
    """Handle all student-related business logic."""
    
    @staticmethod
    def get_active_problems(user=None) -> List['Problem']:
        """
        Get all active problems visible to students.
        
        Args:
            user: Optional user for filtering (future use)
            
        Returns:
            List of active problems with optimized queries
        """
        return ProblemRepository.get_active_problems()
    
    @staticmethod
    def get_problem_detail(slug: str) -> 'Problem':
        """
        Get detailed problem information for students.
        
        Args:
            slug: Problem slug
            
        Returns:
            Problem instance
            
        Raises:
            Http404: If problem not found or not active
        """
        problem = ProblemRepository.get_problem_by_slug(slug)
        if not problem or not problem.is_active:
            raise Http404("Problem not found")
        return problem
    
    @staticmethod
    def get_visible_test_cases(problem: 'Problem') -> 'QuerySet':
        """
        Get only non-hidden test cases for a problem.
        
        Args:
            problem: Problem instance
            
        Returns:
            QuerySet of visible test cases
        """
        return TestCaseRepository.get_visible_test_cases(problem)
    
    @staticmethod
    def get_public_problem_sets() -> 'QuerySet':
        """
        Get all public problem sets with optimized queries.
        
        Returns:
            QuerySet of public problem sets
        """
        # Get all problem sets and filter for public ones
        all_sets = ProblemRepository.get_all_problem_sets()
        # Filter for public sets only
        public_sets = [ps for ps in all_sets if ps.is_public]
        return public_sets
    
    @staticmethod
    def get_problem_set_detail(slug: str) -> 'ProblemSet':
        """
        Get detailed problem set information.
        
        Args:
            slug: Problem set slug
            
        Returns:
            ProblemSet instance with related data
            
        Raises:
            Http404: If problem set not found or not public
        """
        problem_set = ProblemRepository.get_problem_set_with_problems(slug)
        if not problem_set or not problem_set.is_public:
            raise Http404("Problem set not found")
        return problem_set
    
    @staticmethod
    def get_problem_set_problems(problem_set: 'ProblemSet', user=None) -> List[dict]:
        """
        Get ordered problems for a problem set with test cases.

        Performance: Uses prefetched data from repository to avoid N+1 queries.
        Test cases, counts, and categories are all fetched in a single query.

        Args:
            problem_set: ProblemSet instance
            user: Optional user for progress filtering

        Returns:
            List of problem data with ordering, categories, and test cases
        """
        # Get problems through the membership table to preserve order
        # Repository returns structured data with categories AND test cases (optimized)
        memberships_data = ProblemSetMembershipRepository.get_problem_set_memberships_with_categories(problem_set)

        problems_data = []
        for membership in memberships_data:
            problem = membership['problem']
            if problem['is_active']:
                problem_data = {
                    'slug': problem['slug'],
                    'title': problem['title'],
                    'description': problem['description'],
                    'difficulty': problem['difficulty'],
                    'problem_type': problem['problem_type'],
                    'segmentation_enabled': problem['segmentation_enabled'],
                    'reference_solution': problem['reference_solution'],
                    'order': membership['order'],
                    'categories': problem['categories'],
                    'test_cases': problem['test_cases'],  # ✅ From prefetched data (no query)
                    'test_case_count': problem['test_case_count'],  # ✅ From prefetched data (no query)
                    'visible_test_case_count': problem['visible_test_case_count']  # ✅ From prefetched data (no query)
                }
                problems_data.append(problem_data)

        return problems_data
    
    @staticmethod
    def get_all_categories() -> 'QuerySet':
        """
        Get all problem categories ordered by their display order.
        
        Returns:
            QuerySet of ProblemCategory instances
        """
        return ProblemCategoryRepository.get_all_categories()