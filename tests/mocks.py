"""
Mock services for testing the submission pipeline, hints, and progress tracking.
"""
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock
import json


class MockCodeExecutionService:
    """Mock for CodeExecutionService to test without actual code execution."""
    
    def __init__(self, default_behavior='success'):
        """
        Initialize mock with configurable behavior.
        
        Args:
            default_behavior: 'success', 'failure', 'timeout', 'syntax_error'
        """
        self.default_behavior = default_behavior
        self.call_count = 0
        self.last_code = None
        self.last_function_name = None
        self.last_test_cases = None
        
    def test_solution(self, user_code: str, function_name: str, test_cases: List[Dict]) -> Dict:
        """Mock test_solution method."""
        self.call_count += 1
        self.last_code = user_code
        self.last_function_name = function_name
        self.last_test_cases = test_cases
        
        if self.default_behavior == 'success':
            # All tests pass
            results = []
            for i, tc in enumerate(test_cases):
                results.append({
                    'test_number': i + 1,
                    'inputs': tc.get('inputs'),
                    'expected_output': tc.get('expected_output'),
                    'actual_output': tc.get('expected_output'),  # Mock passes all tests
                    'pass': True,
                    'error': None,
                    'function_call': f"{function_name}({tc.get('inputs')})"
                })
            
            return {
                'passed': len(test_cases),
                'total': len(test_cases),
                'results': results
            }
            
        elif self.default_behavior == 'partial_success':
            # Half tests pass
            results = []
            passed = 0
            for i, tc in enumerate(test_cases):
                test_passes = i % 2 == 0
                if test_passes:
                    passed += 1
                    
                results.append({
                    'test_number': i + 1,
                    'inputs': tc.get('inputs'),
                    'expected_output': tc.get('expected_output'),
                    'actual_output': tc.get('expected_output') if test_passes else 'wrong_output',
                    'pass': test_passes,
                    'error': None if test_passes else 'Assertion failed',
                    'function_call': f"{function_name}({tc.get('inputs')})"
                })
            
            return {
                'passed': passed,
                'total': len(test_cases),
                'results': results
            }
            
        elif self.default_behavior == 'timeout':
            return {
                'error': 'Code execution timed out after 5 seconds',
                'passed': 0,
                'total': len(test_cases),
                'results': []
            }
            
        elif self.default_behavior == 'syntax_error':
            return {
                'error': 'SyntaxError: invalid syntax',
                'passed': 0,
                'total': len(test_cases),
                'results': []
            }
            
        else:  # failure
            return {
                'error': 'Code execution failed',
                'passed': 0,
                'total': len(test_cases),
                'results': []
            }


class MockAsyncAIService:
    """Mock for AsyncAIService to test AI-powered features."""
    
    def __init__(self, default_behavior='success'):
        self.default_behavior = default_behavior
        self.generation_call_count = 0
        self.segmentation_call_count = 0
        self.test_call_count = 0
        
    @staticmethod
    def generate_eipl_variations(problem, user_prompt):
        """Mock AI code generation."""
        if MockAsyncAIService._ai_behavior == 'success':
            return {
                'success': True,
                'variations': [
                    '''def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []''',
                    '''def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []'''
                ],
                'comprehension_level': 'intermediate',
                'feedback': 'Generated 2 variations successfully'
            }
        elif MockAsyncAIService._ai_behavior == 'timeout':
            # Simulate a future that times out
            future = MagicMock()
            future.result.side_effect = TimeoutError("AI service timeout")
            return future
        else:
            return {
                'success': False,
                'error': 'AI generation failed',
                'variations': []
            }
    
    @staticmethod
    def segment_prompt(problem, user_prompt):
        """Mock prompt segmentation with updated format."""
        # Mock segments that would be verbatim from a typical user prompt
        mock_segments = [
            {'id': 1, 'text': 'iterate through the array', 'code_lines': [1, 2]},
            {'id': 2, 'text': 'find two numbers', 'code_lines': [3]},
            {'id': 3, 'text': 'sum to target', 'code_lines': [4]}
        ]
        
        # Mock groups in EiPL Grader format
        mock_groups = [
            {'explanation_portion': 'iterate through the array', 'code': 'for i in range(len(arr)):'},
            {'explanation_portion': 'find two numbers', 'code': '    for j in range(i+1, len(arr)):'},
            {'explanation_portion': 'sum to target', 'code': '        if arr[i] + arr[j] == target:'}
        ]
        
        return {
            'success': True,
            'segments': mock_segments,
            'groups': mock_groups,  # EiPL Grader format
            'segment_count': 3,
            'comprehension_level': 'multi_structural',
            'feedback': 'Good line-by-line explanation',
            'processing_time': 0.5,
            'error': None
        }
    
    @staticmethod
    def test_code_variations(code_variations, function_name, test_data):
        """Mock testing of code variations."""
        # Use MockCodeExecutionService for each variation
        mock_executor = MockCodeExecutionService('partial_success')
        results = []
        
        for code in code_variations:
            result = mock_executor.test_solution(code, function_name, test_data)
            results.append(result)
            
        return results

# Class variable to control AI behavior
MockAsyncAIService._ai_behavior = 'success'


class MockOpenAIClient:
    """Mock for OpenAI client."""
    
    def __init__(self):
        self.chat = MagicMock()
        self.completions = MagicMock()
        
        # Setup default response
        self.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps([
                            {
                                "inputs": [2, 7, 11, 15],
                                "target": 9,
                                "expected_output": [0, 1],
                                "description": "Basic test case"
                            },
                            {
                                "inputs": [3, 2, 4],
                                "target": 6,
                                "expected_output": [1, 2],
                                "description": "Another test case"
                            }
                        ])
                    )
                )
            ]
        )


class MockFirebaseAuth:
    """Mock for Firebase authentication."""
    
    def __init__(self):
        self.verified_tokens = {
            'valid_token': {'uid': 'test_user_123', 'email': 'test@example.com'},
            'admin_token': {'uid': 'admin_123', 'email': 'admin@example.com', 'admin': True}
        }
        
    def verify_id_token(self, token):
        """Mock token verification."""
        if token in self.verified_tokens:
            return self.verified_tokens[token]
        raise Exception("Invalid token")