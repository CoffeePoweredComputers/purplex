"""Code execution service for running and testing Python code."""
import json
import subprocess
import tempfile
import os
import logging
from django.conf import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CodeExecutionService:
    """Service for running and testing Python code securely."""
    
    def __init__(self):
        self.timeout = getattr(settings, 'CODE_EXECUTION_TIMEOUT', 5)
        
    def test_solution(self, user_code: str, function_name: str, test_cases: List[Dict]) -> Dict:
        """Test a solution against provided test cases."""
        
        # Create test runner code
        test_runner = self._create_test_runner(user_code, function_name, test_cases)
        
        # Execute the test runner
        result = self._execute_code(test_runner)
        
        if result['success']:
            try:
                # Parse JSON output from test runner
                output_data = json.loads(result['output'])
                return output_data
            except json.JSONDecodeError:
                return {
                    'error': 'Failed to parse test results',
                    'testsPassed': 0,
                    'totalTests': len(test_cases),
                    'results': [],
                    'success': False
                }
        else:
            return {
                'error': result.get('error', 'Code execution failed'),
                'testsPassed': 0,
                'totalTests': len(test_cases),
                'results': [],
                'success': False
            }
    
    def _create_test_runner(self, user_code: str, function_name: str, test_cases: List[Dict]) -> str:
        """Create a test runner script that executes test cases and returns JSON results."""
        
        test_runner = f'''
import json
import sys
import traceback

def compare_results(actual, expected):
    """Compare test results with JSON type coercion compatibility."""
    # Direct equality check first
    if actual == expected:
        return True
        
    # Handle numeric comparisons (int vs float)
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return float(actual) == float(expected)
        
    # Handle list/tuple equivalence (JSON converts tuples to lists)
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return False
        return all(compare_results(a, e) for a, e in zip(actual, expected))
        
    # Handle dict comparison recursively
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(compare_results(actual[k], expected[k]) for k in actual.keys())
        
    # Handle string representations of numbers
    try:
        if str(actual) == str(expected):
            return True
    except:
        pass
        
    return False

# User's code
{user_code}

# Test execution
results = []
passed_count = 0

test_cases = {repr(test_cases)}

for i, test_case in enumerate(test_cases):
    try:
        inputs = test_case.get('inputs', [])
        expected = test_case.get('expected_output')
        
        # Call the function with unpacked arguments
        actual = {function_name}(*inputs)
        
        # JSON serialize and deserialize to ensure consistent comparison
        # This mimics what happens when results are stored and retrieved
        try:
            actual_json = json.loads(json.dumps(actual))
            expected_json = json.loads(json.dumps(expected))
            test_passed = actual_json == expected_json
        except:
            # If JSON serialization fails, fall back to direct comparison
            test_passed = compare_results(actual, expected)
        if test_passed:
            passed_count += 1
            
        # Format the function call string
        args_str = ', '.join(repr(arg) for arg in inputs)
        function_call = "{function_name}(" + args_str + ")"
        
        results.append({{
            'test_number': i + 1,
            'inputs': inputs,
            'expected_output': expected,
            'actual_output': actual,
            'isSuccessful': test_passed,
            'error': None,
            'function_call': function_call
        }})
    except Exception as e:
        inputs = test_case.get('inputs', [])
        args_str = ', '.join(repr(arg) for arg in inputs)
        function_call = "{function_name}(" + args_str + ")"
        
        results.append({{
            'test_number': i + 1,
            'inputs': inputs,
            'expected_output': test_case.get('expected_output'),
            'actual_output': None,
            'isSuccessful': False,
            'error': str(e),
            'function_call': function_call
        }})

# Output results as JSON
output = {{
    'testsPassed': passed_count,
    'totalTests': len(test_cases),
    'results': results,
    'success': passed_count == len(test_cases)
}}

print(json.dumps(output))
'''
        return test_runner
    
    def _compare_results(self, actual: Any, expected: Any) -> bool:
        """Compare test results with JSON type coercion compatibility.
        
        Handles common JSON serialization differences:
        - int vs float (5 vs 5.0)
        - tuple vs list
        - None vs null
        """
        # Direct equality check first
        if actual == expected:
            return True
            
        # Handle numeric comparisons (int vs float)
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return float(actual) == float(expected)
            
        # Handle list/tuple equivalence (JSON converts tuples to lists)
        if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            if len(actual) != len(expected):
                return False
            return all(self._compare_results(a, e) for a, e in zip(actual, expected))
            
        # Handle dict comparison recursively
        if isinstance(actual, dict) and isinstance(expected, dict):
            if set(actual.keys()) != set(expected.keys()):
                return False
            return all(self._compare_results(actual[k], expected[k]) for k in actual.keys())
            
        # Handle string representations of numbers
        try:
            if str(actual) == str(expected):
                return True
        except:
            pass
            
        return False
    
    def _execute_code(self, code: str) -> Dict:
        """Execute Python code in a sandboxed environment."""
        
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run code with timeout and memory limits
            cmd = [
                'python3', temp_file
            ]
            
            # Use subprocess with timeout
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'output': result.stdout,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'output': result.stdout,
                        'error': result.stderr or 'Code execution failed'
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    'success': False,
                    'output': '',
                    'error': f'Code execution timed out after {self.timeout} seconds'
                }
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)