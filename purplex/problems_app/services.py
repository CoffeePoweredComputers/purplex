import json
import tempfile
import subprocess
import sys
from typing import Dict, List, Any, Tuple
from django.conf import settings
import ast
import traceback
from .validation_service import ProblemValidationService

class CodeExecutionService:
    """Service for executing and testing code submissions"""
    
    def __init__(self):
        self.timeout = 30  # seconds
        self.memory_limit = 128  # MB
    
    def validate_python_code(self, code: str) -> Tuple[bool, str]:
        """Validate that code is syntactically correct Python"""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax Error: {str(e)}"
        except Exception as e:
            return False, f"Parse Error: {str(e)}"
    
    def extract_function(self, code: str, function_name: str) -> Tuple[bool, str]:
        """Extract a specific function from code"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return True, ""
            return False, f"Function '{function_name}' not found in code"
        except Exception as e:
            return False, f"Error analyzing code: {str(e)}"
    
    def run_test_case(self, code: str, function_name: str, inputs: List[Any], expected_output: Any) -> Dict[str, Any]:
        """Run a single test case"""
        try:
            # Create a safe execution environment
            namespace = {'__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                'range': range, 'enumerate': enumerate, 'zip': zip,
                'min': min, 'max': max, 'sum': sum, 'abs': abs,
                'sorted': sorted, 'reversed': reversed,
                'print': print  # Allow print for debugging
            }}
            
            # Execute the user's code
            exec(code, namespace)
            
            # Get the function
            if function_name not in namespace:
                return {
                    'pass': False,
                    'error': f"Function '{function_name}' not found",
                    'actual_output': None,
                    'expected_output': expected_output,
                    'inputs': inputs
                }
            
            user_function = namespace[function_name]
            
            # Call the function with inputs
            actual_output = user_function(*inputs)
            
            # Compare outputs
            passed = actual_output == expected_output
            
            return {
                'pass': passed,
                'error': None,
                'actual_output': actual_output,
                'expected_output': expected_output,
                'inputs': inputs
            }
            
        except Exception as e:
            return {
                'pass': False,
                'error': str(e),
                'actual_output': None,
                'expected_output': expected_output,
                'inputs': inputs,
                'traceback': traceback.format_exc()
            }
    
    def test_solution(self, code: str, function_name: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """Test a solution against multiple test cases"""
        # First validate the code
        is_valid, error_msg = self.validate_python_code(code)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'results': [],
                'passed': 0,
                'total': len(test_cases),
                'score': 0.0
            }
        
        # Check if function exists
        has_function, error_msg = self.extract_function(code, function_name)
        if not has_function:
            return {
                'success': False,
                'error': error_msg,
                'results': [],
                'passed': 0,
                'total': len(test_cases),
                'score': 0.0
            }
        
        results = []
        passed_count = 0
        
        for i, test_case in enumerate(test_cases):
            inputs = test_case['inputs']
            expected_output = test_case['expected_output']
            
            result = self.run_test_case(code, function_name, inputs, expected_output)
            result['test_number'] = i + 1
            result['description'] = test_case.get('description', f'Test {i + 1}')
            
            if result['pass']:
                passed_count += 1
            
            results.append(result)
        
        total_tests = len(test_cases)
        score = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'success': True,
            'error': None,
            'results': results,
            'passed': passed_count,
            'total': total_tests,
            'score': score
        }

class AITestGenerationService:
    """Service for AI-based code generation (EiPL only - test case generation removed)"""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        import openai
        self.client = openai.OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
    
    def generate_eipl_variations(self, problem, user_prompt: str) -> Dict[str, Any]:
        """Generate code variations for EiPL problems based on user's description"""
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI API key not configured',
                'variations': []
            }
        
        try:
            # Create a system prompt specific to the problem
            system_prompt = f"""
Create five different implementations of a function called {problem.function_name} based on the user's description.
The function should match this problem:

Guidelines:
1. Each implementation MUST be different 
2. Make the code beginner-friendly and avoid unnecessary built-in functions
3. Each function MUST be named exactly: {problem.function_name}. If it is not the grading mechanism will fail.
4. Return only the function implementations, no additional text or comments

Format your response as:
```python
def {problem.function_name}(...):
    # implementation 1
```
```python
def {problem.function_name}(...):
    # implementation 2
```
```python
def {problem.function_name}(...):
    # implementation 3
```
```python
def {problem.function_name}(...):
    # implementation 4
```
```python
def {problem.function_name}(...):
    # implementation 5
```
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Extract code blocks from the response
            import re
            code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
            
            # Filter out empty blocks and ensure we have exactly 5
            code_blocks = [block.strip() for block in code_blocks if block.strip()]
            
            if len(code_blocks) < 5:
                # Try alternative extraction method
                code_blocks = re.findall(r'def\s+' + re.escape(problem.function_name) + r'.*?(?=def\s+' + re.escape(problem.function_name) + r'|$)', content, re.DOTALL)
                code_blocks = [block.strip() for block in code_blocks if block.strip()]
            
            # Ensure we have exactly 5 variations
            if len(code_blocks) > 5:
                code_blocks = code_blocks[:5]
            elif len(code_blocks) < 5:
                # Pad with duplicates if necessary (this shouldn't happen with proper prompting)
                while len(code_blocks) < 5:
                    code_blocks.append(code_blocks[-1] if code_blocks else f"def {problem.function_name}():\n    pass")
            
            return {
                'success': True,
                'variations': code_blocks,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'variations': []
            }

class ProblemValidationService:
    """Service for validating problem definitions"""
    
    def __init__(self):
        self.code_service = CodeExecutionService()
    
    def validate_problem(self, problem_data: Dict) -> Tuple[bool, List[str]]:
        """Validate a complete problem definition"""
        errors = []
        
        # Validate required fields
        required_fields = ['title', 'description', 'function_name', 'reference_solution']
        for field in required_fields:
            if not problem_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate function name
        function_name = problem_data.get('function_name', '')
        if function_name and not function_name.isidentifier():
            errors.append("Function name must be a valid Python identifier")
        
        # Validate reference solution
        reference_solution = problem_data.get('reference_solution', '')
        if reference_solution:
            is_valid, error_msg = self.code_service.validate_python_code(reference_solution)
            if not is_valid:
                errors.append(f"Reference solution error: {error_msg}")
            else:
                has_function, error_msg = self.code_service.extract_function(reference_solution, function_name)
                if not has_function:
                    errors.append(f"Reference solution error: {error_msg}")
        
        # Validate test cases
        test_cases = problem_data.get('test_cases', [])
        if not test_cases:
            errors.append("At least one test case is required")
        else:
            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case.get('inputs'), list):
                    errors.append(f"Test case {i+1}: inputs must be a list")
                if 'expected_output' not in test_case:
                    errors.append(f"Test case {i+1}: expected_output is required")
        
        # Test reference solution against test cases
        if not errors and reference_solution and test_cases:
            test_result = self.code_service.test_solution(
                reference_solution, function_name, test_cases
            )
            if not test_result['success']:
                errors.append(f"Reference solution failed: {test_result['error']}")
            elif test_result['passed'] != test_result['total']:
                errors.append(f"Reference solution passed {test_result['passed']}/{test_result['total']} test cases")
        
        return len(errors) == 0, errors
