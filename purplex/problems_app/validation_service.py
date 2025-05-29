from typing import Dict, List, Any, Tuple, Optional
import json
import re
from django.core.exceptions import ValidationError
from .types import ValidationResult, ValidationError as CustomValidationError

class ProblemValidationService:
    """Comprehensive validation service for problems and test cases"""
    
    # Python keywords that cannot be used as function names
    PYTHON_KEYWORDS = {
        'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
        'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global',
        'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'with', 'yield', 'None', 'True', 'False'
    }
    
    def validate_problem_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete problem data
        
        Args:
            data: Problem data dictionary to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Required field validations
        required_fields = ['title', 'description', 'function_name', 'reference_solution']
        for field in required_fields:
            if not data.get(field, '').strip():
                errors.append(CustomValidationError(
                    field=field,
                    message=f'{field.replace("_", " ").title()} is required',
                    code='REQUIRED'
                ))
        
        # Title validation
        if data.get('title'):
            title = data['title'].strip()
            if len(title) < 3:
                errors.append(CustomValidationError(
                    field='title',
                    message='Title must be at least 3 characters long',
                    code='MIN_LENGTH'
                ))
            elif len(title) > 200:
                errors.append(CustomValidationError(
                    field='title',
                    message='Title must not exceed 200 characters',
                    code='MAX_LENGTH'
                ))
        
        # Description validation
        if data.get('description'):
            description = data['description'].strip()
            if len(description) < 10:
                errors.append(CustomValidationError(
                    field='description',
                    message='Description must be at least 10 characters long',
                    code='MIN_LENGTH'
                ))
        
        # Function name validation
        if data.get('function_name'):
            function_name = data['function_name'].strip()
            validation_result = self.validate_function_name(function_name)
            if not validation_result[0]:
                errors.append(CustomValidationError(
                    field='function_name',
                    message=validation_result[1],
                    code='INVALID_FORMAT'
                ))
        
        # Reference solution validation
        if data.get('reference_solution'):
            solution = data['reference_solution'].strip()
            if len(solution) < 10:
                errors.append(CustomValidationError(
                    field='reference_solution',
                    message='Reference solution must be at least 10 characters long',
                    code='MIN_LENGTH'
                ))
            
            # Check if solution contains the function name
            function_name = data.get('function_name', '').strip()
            if function_name and f'def {function_name}' not in solution:
                warnings.append(CustomValidationError(
                    field='reference_solution',
                    message=f'Reference solution should define function "{function_name}"',
                    code='MISSING_FUNCTION_DEF'
                ))
        
        # Numeric field validations
        if 'memory_limit' in data:
            value = data['memory_limit']
            if not isinstance(value, int) or value < 32:
                errors.append(CustomValidationError(
                    field='memory_limit',
                    message='Memory limit must be at least 32 MB',
                    code='MIN_VALUE'
                ))
            elif value > 1024:
                errors.append(CustomValidationError(
                    field='memory_limit',
                    message='Memory limit must not exceed 1024 MB',
                    code='MAX_VALUE'
                ))
        
        # Test cases validation
        if 'test_cases' in data:
            test_cases = data['test_cases']
            if not isinstance(test_cases, list) or len(test_cases) == 0:
                errors.append(CustomValidationError(
                    field='test_cases',
                    message='At least one test case is required',
                    code='MIN_LENGTH'
                ))
            else:
                # Validate each test case
                for i, test_case in enumerate(test_cases):
                    tc_errors = self.validate_test_case_data(test_case)
                    for error in tc_errors:
                        errors.append(CustomValidationError(
                            field=f'test_cases.{i}.{error.field}',
                            message=error.message,
                            code=error.code
                        ))
                
                # Check for sample test cases
                has_sample = any(tc.get('is_sample', False) for tc in test_cases)
                if not has_sample:
                    warnings.append(CustomValidationError(
                        field='test_cases',
                        message='Consider marking at least one test case as a sample',
                        code='NO_SAMPLE_TESTS'
                    ))
        
        # Tags validation
        if 'tags' in data:
            tags = data['tags']
            if not isinstance(tags, list):
                errors.append(CustomValidationError(
                    field='tags',
                    message='Tags must be a list of strings',
                    code='INVALID_TYPE'
                ))
            else:
                for i, tag in enumerate(tags):
                    if not isinstance(tag, str):
                        errors.append(CustomValidationError(
                            field=f'tags.{i}',
                            message='Each tag must be a string',
                            code='INVALID_TYPE'
                        ))
                    elif len(tag.strip()) == 0:
                        errors.append(CustomValidationError(
                            field=f'tags.{i}',
                            message='Tags cannot be empty',
                            code='EMPTY_VALUE'
                        ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_function_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate Python function name
        
        Args:
            name: Function name to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not name:
            return False, "Function name cannot be empty"
        
        # Check Python identifier pattern
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            return False, "Function name must be a valid Python identifier"
        
        # Check against Python keywords
        if name.lower() in self.PYTHON_KEYWORDS:
            return False, f"'{name}' is a Python keyword and cannot be used as a function name"
        
        # Check for common conventions
        if name.startswith('__') and name.endswith('__'):
            return False, "Dunder methods (names starting and ending with __) are not allowed"
        
        return True, ""
    
    def validate_test_case_data(self, test_case: Dict[str, Any]) -> List[CustomValidationError]:
        """
        Validate individual test case data
        
        Args:
            test_case: Test case data dictionary
            
        Returns:
            List[CustomValidationError]: List of validation errors
        """
        errors = []
        
        # Required fields
        if 'inputs' not in test_case:
            errors.append(CustomValidationError(
                field='inputs',
                message='Test case inputs are required',
                code='REQUIRED'
            ))
        else:
            inputs = test_case['inputs']
            if not isinstance(inputs, list):
                errors.append(CustomValidationError(
                    field='inputs',
                    message='Test case inputs must be a list',
                    code='INVALID_TYPE'
                ))
        
        if 'expected_output' not in test_case:
            errors.append(CustomValidationError(
                field='expected_output',
                message='Test case expected output is required',
                code='REQUIRED'
            ))
        else:
            # Validate that expected_output is JSON serializable
            try:
                json.dumps(test_case['expected_output'])
            except (TypeError, ValueError):
                errors.append(CustomValidationError(
                    field='expected_output',
                    message='Expected output must be JSON serializable',
                    code='INVALID_JSON'
                ))
        
        # Boolean field validation
        for field in ['is_hidden', 'is_sample']:
            if field in test_case and not isinstance(test_case[field], bool):
                errors.append(CustomValidationError(
                    field=field,
                    message=f'{field} must be a boolean value',
                    code='INVALID_TYPE'
                ))
        
        # Order validation
        if 'order' in test_case:
            order = test_case['order']
            if not isinstance(order, int) or order < 0:
                errors.append(CustomValidationError(
                    field='order',
                    message='Order must be a non-negative integer',
                    code='INVALID_VALUE'
                ))
        
        # Description validation
        if 'description' in test_case:
            description = test_case['description']
            if description and len(str(description).strip()) > 200:
                errors.append(CustomValidationError(
                    field='description',
                    message='Test case description must not exceed 200 characters',
                    code='MAX_LENGTH'
                ))
        
        return errors
    
    def validate_test_case_json(self, json_string: str) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate JSON string for test case data
        
        Args:
            json_string: JSON string to validate
            
        Returns:
            Tuple[bool, Any, Optional[str]]: (is_valid, parsed_value, error_message)
        """
        try:
            parsed = json.loads(json_string)
            return True, parsed, None
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"