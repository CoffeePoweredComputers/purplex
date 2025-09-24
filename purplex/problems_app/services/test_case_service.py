"""Service for managing test cases with proper abstraction."""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from django.contrib.auth.models import User

from ..repositories import TestCaseRepository

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import Problem, TestCase


class TestCaseService:
    """Service for managing test cases and related operations."""
    
    @staticmethod
    def get_problem_test_cases(
        problem: 'Problem',
        include_hidden: bool = True
    ) -> List['TestCase']:
        """
        Get all test cases for a problem.
        
        Args:
            problem: The problem to get test cases for
            include_hidden: Whether to include hidden test cases
            
        Returns:
            List of TestCase objects
        """
        return TestCaseRepository.get_problem_test_cases(
            problem=problem,
            include_hidden=include_hidden
        )
    
    @staticmethod
    def get_test_cases_for_testing(
        problem: 'Problem',
        include_hidden: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get test cases formatted for code execution.
        
        Args:
            problem: The problem to get test cases for
            include_hidden: Whether to include hidden test cases
            
        Returns:
            List of dictionaries with 'inputs' and 'expected_output' keys
        """
        test_cases = TestCaseRepository.get_problem_test_cases(
            problem=problem,
            include_hidden=include_hidden
        )
        
        # Convert TestCase objects to the format needed for testing
        return [
            {
                'id': tc.id,  # Include the ID for TestExecution tracking
                'inputs': tc.inputs,
                'expected_output': tc.expected_output
            }
            for tc in test_cases
        ]
    
    @staticmethod
    def get_visible_test_cases(problem: 'Problem') -> List['TestCase']:
        """
        Get only visible (non-hidden) test cases for a problem.
        
        Args:
            problem: The problem to get test cases for
            
        Returns:
            List of visible TestCase objects
        """
        return TestCaseRepository.get_visible_test_cases(problem)
    
    @staticmethod
    def get_sample_test_cases(problem: 'Problem') -> List['TestCase']:
        """
        Get only sample test cases for a problem.
        
        Args:
            problem: The problem to get sample test cases for
            
        Returns:
            List of sample TestCase objects
        """
        return TestCaseRepository.get_sample_test_cases(problem)
    
    @staticmethod
    def count_problem_test_cases(
        problem: 'Problem',
        include_hidden: bool = True
    ) -> int:
        """
        Count test cases for a problem.
        
        Args:
            problem: The problem to count test cases for
            include_hidden: Whether to include hidden test cases
            
        Returns:
            Number of test cases
        """
        return TestCaseRepository.count_problem_test_cases(
            problem=problem,
            include_hidden=include_hidden
        )
    
    @staticmethod
    def create_test_case(
        problem: 'Problem',
        inputs: List,
        expected_output: Any,
        **kwargs
    ) -> 'TestCase':
        """
        Create a new test case for a problem.
        
        Args:
            problem: The problem this test case belongs to
            inputs: List of input arguments
            expected_output: Expected output value
            **kwargs: Additional fields (description, is_hidden, is_sample, order)
            
        Returns:
            Created TestCase instance
        """
        return TestCaseRepository.create_test_case(
            problem=problem,
            inputs=inputs,
            expected_output=expected_output,
            **kwargs
        )
    
    @staticmethod
    def update_test_case(test_case_id: int, **kwargs) -> bool:
        """
        Update a test case by ID.
        
        Args:
            test_case_id: The test case ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        return TestCaseRepository.update_test_case(test_case_id, **kwargs)
    
    @staticmethod
    def delete_test_case(test_case_id: int) -> bool:
        """
        Delete a test case by ID.
        
        Args:
            test_case_id: The test case ID
            
        Returns:
            True if deleted, False if not found
        """
        return TestCaseRepository.delete_test_case(test_case_id)
    
    @staticmethod
    def delete_problem_test_cases(problem: 'Problem') -> int:
        """
        Delete all test cases for a problem.
        
        Args:
            problem: The problem whose test cases to delete
            
        Returns:
            Number of test cases deleted
        """
        return TestCaseRepository.delete_problem_test_cases(problem)