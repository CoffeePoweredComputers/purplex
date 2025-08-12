"""Problem validation service."""
from typing import Optional


class ProblemValidationService:
    """Service for validating problem definitions"""
    
    @staticmethod
    def validate_problem_data(data: dict) -> tuple[bool, Optional[str]]:
        """
        Validate problem data before saving
        
        Returns:
            (is_valid, error_message)
        """
        # Required fields
        required_fields = ['title', 'description', 'function_name', 'function_signature']
        for field in required_fields:
            if not data.get(field):
                return False, f"{field} is required"
        
        # Function name validation
        function_name = data['function_name']
        if not function_name.isidentifier():
            return False, "Function name must be a valid Python identifier"
        
        # Function signature validation
        function_signature = data['function_signature']
        if not function_signature.strip().startswith('def'):
            return False, "Function signature must start with 'def'"
        
        # Reference solution validation (if provided)
        if data.get('reference_solution'):
            ref_solution = data['reference_solution'].strip()
            if ref_solution and not ref_solution.startswith('def'):
                return False, "Reference solution must be a valid function definition"
        
        return True, None
    
    @staticmethod
    def validate_test_case(test_case: dict, function_signature: str) -> tuple[bool, Optional[str]]:
        """
        Validate a test case against the function signature
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(test_case.get('inputs'), list):
            return False, "Test case inputs must be a list"
        
        if 'expected_output' not in test_case:
            return False, "Test case must have expected_output"
        
        # TODO: Add more sophisticated validation based on function signature
        
        return True, None