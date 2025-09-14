"""Service for managing problems with proper abstraction."""
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from django.contrib.auth.models import User
from django.db.models import QuerySet

from ..repositories import ProblemRepository

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import Problem, ProblemSet, ProblemCategory, TestCase


class ProblemService:
    """Service for managing problems and related operations."""
    
    @staticmethod
    def get_problem_by_id(problem_id: int) -> Optional['Problem']:
        """
        Get a problem by its ID.
        
        Args:
            problem_id: The problem ID
            
        Returns:
            Problem instance or None
        """
        return ProblemRepository.get_by_id(problem_id)
    
    @staticmethod
    def get_problem_by_slug(slug: str) -> Optional['Problem']:
        """
        Get a problem by its slug.
        
        Args:
            slug: The problem slug
            
        Returns:
            Problem instance or None
        """
        return ProblemRepository.get_problem_by_slug(slug)
    
    @staticmethod
    def get_all_problems() -> List['Problem']:
        """
        Get all problems with optimizations.
        
        Returns:
            List of all Problem instances
        """
        return ProblemRepository.get_all_problems()
    
    @staticmethod
    def get_active_problems() -> List['Problem']:
        """
        Get all active (non-draft) problems.
        
        Returns:
            List of active Problem instances
        """
        return ProblemRepository.get_active_problems()
    
    @staticmethod
    def get_problems_by_category(category: 'ProblemCategory') -> List['Problem']:
        """
        Get all problems in a specific category.
        
        Args:
            category: The problem category
            
        Returns:
            List of Problem instances in the category
        """
        return ProblemRepository.get_problems_by_category(category)
    
    @staticmethod
    def get_problems_by_difficulty(difficulty: int) -> List['Problem']:
        """
        Get problems by difficulty level.
        
        Args:
            difficulty: The difficulty level (1-5)
            
        Returns:
            List of Problem instances with the specified difficulty
        """
        return ProblemRepository.get_problems_by_difficulty(difficulty)
    
    @staticmethod
    def search_problems(query: str) -> List['Problem']:
        """
        Search problems by title or description.
        
        Args:
            query: The search query
            
        Returns:
            List of matching Problem instances
        """
        return ProblemRepository.search_problems(query)
    
    @staticmethod
    def get_problem_with_test_cases(slug: str) -> Optional['Problem']:
        """
        Get a problem with all its test cases prefetched.
        
        Args:
            slug: The problem slug
            
        Returns:
            Problem instance with test cases or None
        """
        return ProblemRepository.get_problem_with_test_cases(slug)
    
    @staticmethod
    def get_user_created_problems(user: User) -> List['Problem']:
        """
        Get all problems created by a specific user.
        
        Args:
            user: The user who created the problems
            
        Returns:
            List of Problem instances created by the user
        """
        return ProblemRepository.get_user_created_problems(user)
    
    @staticmethod
    def count_problems_by_difficulty() -> Dict[int, int]:
        """
        Get count of problems grouped by difficulty.
        
        Returns:
            Dictionary mapping difficulty level to count
        """
        return ProblemRepository.count_problems_by_difficulty()
    
    @staticmethod
    def update_problem(problem: 'Problem', **kwargs) -> 'Problem':
        """
        Update a problem with given fields.
        
        Args:
            problem: The problem to update
            **kwargs: Fields to update
            
        Returns:
            Updated Problem instance
        """
        return ProblemRepository.update_problem(problem, **kwargs)
    
    @staticmethod
    def create_problem(**kwargs) -> 'Problem':
        """
        Create a new problem.
        
        Args:
            **kwargs: Problem fields
            
        Returns:
            Created Problem instance
        """
        return ProblemRepository.create(**kwargs)
    
    @staticmethod
    def delete_problem(problem_id: int) -> bool:
        """
        Delete a problem by ID.
        
        Args:
            problem_id: The problem ID
            
        Returns:
            True if deleted, False if not found
        """
        return ProblemRepository.delete(problem_id)
    
    # ProblemSet related methods
    @staticmethod
    def get_problem_set_by_id(problem_set_id: int) -> Optional['ProblemSet']:
        """
        Get a problem set by its ID.
        
        Args:
            problem_set_id: The problem set ID
            
        Returns:
            ProblemSet instance or None
        """
        from ..repositories import ProblemSetRepository
        return ProblemSetRepository.get_by_id(problem_set_id)
    
    @staticmethod
    def get_problem_set_by_slug(slug: str) -> Optional['ProblemSet']:
        """
        Get a problem set by slug.
        
        Args:
            slug: The problem set slug
            
        Returns:
            ProblemSet instance or None
        """
        return ProblemRepository.get_problem_set_by_slug(slug)
    
    @staticmethod
    def get_all_problem_sets() -> List['ProblemSet']:
        """
        Get all problem sets.
        
        Returns:
            List of all ProblemSet instances
        """
        return ProblemRepository.get_all_problem_sets()
    
    @staticmethod
    def get_problem_set_with_problems(slug: str) -> Optional['ProblemSet']:
        """
        Get a problem set with all its problems prefetched.
        
        Args:
            slug: The problem set slug
            
        Returns:
            ProblemSet instance with problems or None
        """
        return ProblemRepository.get_problem_set_with_problems(slug)
    
    @staticmethod
    def get_problems_in_set(problem_set: 'ProblemSet') -> List['Problem']:
        """
        Get all problems in a problem set, ordered.
        
        Args:
            problem_set: The problem set
            
        Returns:
            List of Problem instances in the set
        """
        return ProblemRepository.get_problems_in_set(problem_set)
    
    @staticmethod
    def verify_problem_in_set(problem: 'Problem', problem_set: 'ProblemSet') -> bool:
        """
        Check if a problem is in a problem set.
        
        Args:
            problem: The problem to check
            problem_set: The problem set to check against
            
        Returns:
            True if the problem is in the set, False otherwise
        """
        return ProblemRepository.problem_in_set(problem, problem_set)