"""Problem validation service."""
import re
from typing import Optional


class ProblemValidationService:
    """Service for validating problem definitions and user inputs"""
    
    # Python keywords that cannot be used as function names
    PYTHON_KEYWORDS = {
        'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
        'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global',
        'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'with', 'yield', 'None', 'True', 'False'
    }
    
    # Validation constants
    MIN_PROMPT_LENGTH = 10
    MAX_PROMPT_LENGTH = 2000
    MAX_CODE_LENGTH = 50000
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 200
    MIN_DESCRIPTION_LENGTH = 10
    
    # Injection patterns to detect
    INJECTION_PATTERNS = ['<script', '<?php', '<%', '<jsp']
    
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
        
        # Title validation
        title = data['title'].strip()
        if len(title) < ProblemValidationService.MIN_TITLE_LENGTH:
            return False, f"Title must be at least {ProblemValidationService.MIN_TITLE_LENGTH} characters long"
        if len(title) > ProblemValidationService.MAX_TITLE_LENGTH:
            return False, f"Title must not exceed {ProblemValidationService.MAX_TITLE_LENGTH} characters"
        
        # Description validation
        description = data['description'].strip()
        if len(description) < ProblemValidationService.MIN_DESCRIPTION_LENGTH:
            return False, f"Description must be at least {ProblemValidationService.MIN_DESCRIPTION_LENGTH} characters long"
        
        # Function name validation
        function_name = data['function_name']
        is_valid, error = ProblemValidationService.validate_function_name(function_name)
        if not is_valid:
            return False, error
        
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
    def validate_function_name(name: str) -> tuple[bool, str]:
        """
        Validate Python function name
        
        Args:
            name: Function name to validate
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not name:
            return False, "Function name cannot be empty"
        
        # Check Python identifier pattern
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            return False, "Function name must be a valid Python identifier"
        
        # Check against Python keywords
        if name.lower() in ProblemValidationService.PYTHON_KEYWORDS:
            return False, f"'{name}' is a Python keyword and cannot be used as a function name"
        
        # Check for common conventions
        if name.startswith('__') and name.endswith('__'):
            return False, "Dunder methods (names starting and ending with __) are not allowed"
        
        return True, ""
    
    @staticmethod
    def validate_test_case(test_case: dict, function_signature: str = None) -> tuple[bool, Optional[str]]:
        """
        Validate a test case against the function signature
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(test_case.get('inputs'), list):
            return False, "Test case inputs must be a list"
        
        if 'expected_output' not in test_case:
            return False, "Test case must have expected_output"
        
        # Validate boolean fields
        for field in ['is_hidden', 'is_sample']:
            if field in test_case and not isinstance(test_case[field], bool):
                return False, f"{field} must be a boolean value"
        
        # Validate order if present
        if 'order' in test_case:
            order = test_case['order']
            if not isinstance(order, int) or order < 0:
                return False, "Order must be a non-negative integer"
        
        return True, None
    
    @staticmethod
    def validate_user_prompt(prompt: str) -> tuple[bool, Optional[str]]:
        """
        Validate user EiPL prompt for length and content
        
        Returns:
            (is_valid, error_message)
        """
        if not prompt or not prompt.strip():
            return False, "user_prompt is required and cannot be empty"
        
        prompt = prompt.strip()
        
        # Length validation
        if len(prompt) < ProblemValidationService.MIN_PROMPT_LENGTH:
            return False, f"user_prompt must be at least {ProblemValidationService.MIN_PROMPT_LENGTH} characters long"
        
        if len(prompt) > ProblemValidationService.MAX_PROMPT_LENGTH:
            return False, f"user_prompt must not exceed {ProblemValidationService.MAX_PROMPT_LENGTH} characters"
        
        # Content validation - prevent potential injection attempts
        if any(pattern in prompt for pattern in ProblemValidationService.INJECTION_PATTERNS):
            return False, "Invalid characters detected in prompt"
        
        return True, None
    
    @staticmethod
    def validate_user_code(code: str) -> tuple[bool, Optional[str]]:
        """
        Validate user submitted code for length
        
        Returns:
            (is_valid, error_message)
        """
        if not code or not code.strip():
            return False, "Code is required and cannot be empty"
        
        if len(code) > ProblemValidationService.MAX_CODE_LENGTH:
            return False, f"Code must not exceed {ProblemValidationService.MAX_CODE_LENGTH} characters"
        
        return True, None