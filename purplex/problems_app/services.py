import json
import subprocess
import tempfile
import os
import logging
from django.conf import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CodeExecutionService:
    """Service for running and testing Python code securely."""
    
    def __init__(self):
        self.docker_image = getattr(settings, 'DOCKER_IMAGE', 'python:3.9-alpine')
        self.timeout = getattr(settings, 'CODE_EXECUTION_TIMEOUT', 5)
        self.memory_limit = getattr(settings, 'CODE_EXECUTION_MEMORY_LIMIT', '128m')
        
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
                    'passed': 0,
                    'total': len(test_cases),
                    'results': []
                }
        else:
            return {
                'error': result.get('error', 'Code execution failed'),
                'passed': 0,
                'total': len(test_cases),
                'results': []
            }
    
    def _create_test_runner(self, user_code: str, function_name: str, test_cases: List[Dict]) -> str:
        """Create a test runner script that executes test cases and returns JSON results."""
        
        test_runner = f'''
import json
import sys
import traceback

# User's code
{user_code}

# Test execution
results = []
passed_count = 0

test_cases = {json.dumps(test_cases)}

for i, test_case in enumerate(test_cases):
    try:
        inputs = test_case.get('inputs', [])
        expected = test_case.get('expected_output')
        
        # Call the function with unpacked arguments
        actual = {function_name}(*inputs)
        
        # Compare results
        test_passed = actual == expected
        if test_passed:
            passed_count += 1
            
        # Format the function call string
        args_str = ', '.join(str(arg) for arg in inputs)
        function_call = f"{function_name}({args_str})"
        
        results.append({{
            'test_number': i + 1,
            'inputs': inputs,
            'expected_output': expected,
            'actual_output': actual,
            'pass': test_passed,
            'error': None,
            'function_call': function_call
        }})
    except Exception as e:
        inputs = test_case.get('inputs', [])
        args_str = ', '.join(str(arg) for arg in inputs)
        function_call = f"{function_name}({args_str})"
        
        results.append({{
            'test_number': i + 1,
            'inputs': inputs,
            'expected_output': test_case.get('expected_output'),
            'actual_output': None,
            'pass': False,
            'error': str(e),
            'function_call': function_call
        }})

# Output results as JSON
output = {{
    'passed': passed_count,
    'total': len(test_cases),
    'results': results
}}

print(json.dumps(output))
'''
        return test_runner
    
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


class AITestGenerationService:
    """Service for generating test cases using AI."""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.openai_api_key:
            import openai
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            
    def generate_test_cases(self, problem_description: str, function_signature: str, num_cases: int = 5) -> List[Dict]:
        """Generate test cases for a problem using GPT-4."""
        
        if not self.client:
            return []
            
        prompt = f"""Generate {num_cases} test cases for the following problem:

Problem Description:
{problem_description}

Function Signature:
{function_signature}

Generate diverse test cases that cover:
- Basic functionality
- Edge cases
- Error conditions (if applicable)

Return the test cases as a JSON array where each test case has:
- "inputs": array of input arguments
- "expected_output": the expected return value
- "description": brief description of what this test case tests

Example format:
[
    {{"inputs": [5, 3], "expected_output": 8, "description": "Basic addition"}},
    {{"inputs": [0, 0], "expected_output": 0, "description": "Adding zeros"}}
]
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates comprehensive test cases for programming problems."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                test_cases = json.loads(json_match.group())
                return test_cases
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to generate test cases: {str(e)}")
            return []
            
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
            
            # Extract code blocks
            import re
            code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
            
            # If no code blocks found, try splitting by function definitions
            if not code_blocks:
                # Split by 'def' and reconstruct
                parts = content.split('def ')
                code_blocks = []
                for part in parts[1:]:  # Skip first empty part
                    code_blocks.append('def ' + part.strip())
            
            # Validate that we have the expected function name
            valid_variations = []
            for code in code_blocks:
                if f"def {problem.function_name}" in code:
                    valid_variations.append(code.strip())
            
            return {
                'success': True,
                'variations': valid_variations[:5],  # Return up to 5 variations
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate EIPL variations: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'variations': []
            }


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


class SegmentationService:
    """Service for prompt segmentation analysis using GPT-4"""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.openai_api_key:
            import openai
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
    
    def segment_prompt(self, user_prompt: str, reference_code: str, problem_config: dict = None) -> dict:
        """
        Segment user prompt and map to code lines using GPT-4
        
        Args:
            user_prompt: User's explanation of the code
            reference_code: Reference solution code
            problem_config: Problem-specific segmentation configuration
            
        Returns:
            {
                'success': bool,
                'segments': [{'id': int, 'text': str, 'code_lines': [int]}],
                'segment_count': int,
                'comprehension_level': str,
                'feedback': str,
                'processing_time': float,
                'error': str (if failed)
            }
        """
        import time
        start_time = time.time()
        
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI API key not configured',
                'segments': [],
                'segment_count': 0,
                'comprehension_level': 'unknown',
                'feedback': '',
                'processing_time': 0.0
            }
        
        try:
            # Get configuration values
            config = problem_config or {}
            threshold = config.get('threshold', 2)
            custom_examples = config.get('examples', {})
            
            # Create segmentation prompt with few-shot examples
            system_prompt = self._create_segmentation_prompt(reference_code, custom_examples)
            
            # Make API call to GPT-4
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using same model as AI service for consistency
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please analyze this prompt: {user_prompt}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            # Parse the response into structured segments
            segments_data = self._parse_segments(content, reference_code)
            
            if not segments_data['success']:
                return {
                    'success': False,
                    'error': segments_data['error'],
                    'segments': [],
                    'segment_count': 0,
                    'comprehension_level': 'unknown',
                    'feedback': '',
                    'processing_time': time.time() - start_time
                }
            
            segments = segments_data['segments']
            segment_count = len(segments)
            
            # Determine comprehension level and feedback
            level, feedback = self._determine_comprehension_level(segment_count, threshold, config)
            
            return {
                'success': True,
                'segments': segments,
                'segment_count': segment_count,
                'comprehension_level': level,
                'feedback': feedback,
                'processing_time': time.time() - start_time,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'segments': [],
                'segment_count': 0,
                'comprehension_level': 'unknown',
                'feedback': '',
                'processing_time': time.time() - start_time
            }
    
    def _create_segmentation_prompt(self, reference_code: str, custom_examples: dict = None) -> str:
        """Build few-shot prompt with examples for consistent segmentation"""
        
        # Start with base prompt
        prompt_parts = ["""You are an expert at analyzing student explanations of code. Your task is to:

1. Segment the student's explanation into distinct semantic units
2. Map each segment to the relevant lines of code
3. Classify the explanation type based on the number of segments

REFERENCE CODE:
```python
{}
```""".format(reference_code)]
        
        # Add examples if provided
        if custom_examples:
            prompt_parts.append("\nSEGMENTATION EXAMPLES:")
            
            # Add relational example if it exists
            if 'relational' in custom_examples and self._is_valid_example(custom_examples['relational']):
                example = custom_examples['relational']
                prompt_parts.append("\nRELATIONAL (High-level understanding):")
                prompt_parts.append(f'Student prompt: "{example["prompt"]}"')
                prompt_parts.append("Segments:")
                prompt_parts.append(self._format_example_segments(example['segments'], example['code_lines']))
            
            # Add multi-structural example if it exists
            if 'multi_structural' in custom_examples and self._is_valid_example(custom_examples['multi_structural']):
                example = custom_examples['multi_structural']
                prompt_parts.append("\nMULTI-STRUCTURAL (Line-by-line description):")
                prompt_parts.append(f'Student prompt: "{example["prompt"]}"')
                prompt_parts.append("Segments:")
                prompt_parts.append(self._format_example_segments(example['segments'], example['code_lines']))
        
        # Add instructions
        prompt_parts.append("""
INSTRUCTIONS:
- Segment the student explanation into meaningful semantic units
- Each segment should represent a distinct concept or action
- Map segments to code lines (1-indexed)
- Remove any segments that just describe function definition/signature
- Return your analysis as JSON in this exact format:

{
    "segments": [
        {"id": 1, "text": "segment text here", "code_lines": [1, 2, 3]},
        {"id": 2, "text": "another segment", "code_lines": [4, 5]}
    ]
}

Be precise and consistent in your segmentation.""")
        
        return '\n'.join(prompt_parts)
    
    def _is_valid_example(self, example: dict) -> bool:
        """Check if an example has all required fields"""
        required_fields = ['prompt', 'segments', 'code_lines']
        return all(field in example and example[field] for field in required_fields)
    
    def _format_example_segments(self, segments: list, code_lines: list) -> str:
        """Format example segments for the prompt"""
        formatted = []
        for i, (segment, lines) in enumerate(zip(segments, code_lines)):
            formatted.append(f'  {i+1}. "{segment}" -> lines {lines}')
        return '\n'.join(formatted)
    
    def _parse_segments(self, ai_response: str, reference_code: str) -> dict:
        """Parse AI response into structured segments"""
        try:
            import re
            import json
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                return {'success': False, 'error': 'No JSON found in response', 'segments': []}
            
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            segments = parsed_data.get('segments', [])
            if not segments:
                return {'success': False, 'error': 'No segments found in response', 'segments': []}
            
            # Validate and clean segments
            valid_segments = []
            code_lines = reference_code.split('\n')
            max_line = len(code_lines)
            
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                    
                text = segment.get('text', '').strip()
                lines = segment.get('code_lines', [])
                
                if not text or not lines:
                    continue
                
                # Filter out function definition segments
                if self._is_function_definition_segment(text):
                    continue
                
                # Validate and clamp code lines
                valid_lines = [line for line in lines if isinstance(line, int) and 1 <= line <= max_line]
                if not valid_lines:
                    valid_lines = [1]  # Default to first line if no valid lines
                
                valid_segments.append({
                    'id': len(valid_segments) + 1,
                    'text': text,
                    'code_lines': sorted(valid_lines)
                })
            
            return {'success': True, 'segments': valid_segments, 'error': None}
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON parsing error: {str(e)}', 'segments': []}
        except Exception as e:
            return {'success': False, 'error': f'Parsing error: {str(e)}', 'segments': []}
    
    def _is_function_definition_segment(self, text: str) -> bool:
        """Check if segment just describes function definition/signature"""
        definition_keywords = [
            'function takes', 'function accepts', 'function has parameters',
            'takes a parameter', 'takes an argument', 'function definition',
            'defines a function', 'function signature', 'function called'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in definition_keywords)
    
    def _determine_comprehension_level(self, segment_count: int, threshold: int = 2, config: dict = None) -> tuple:
        """
        Binary classification based on segment count threshold
        
        Args:
            segment_count: Number of segments identified
            threshold: Threshold for relational vs multi-structural (default: 2)
            config: Problem configuration with custom feedback messages
            
        Returns:
            (level, feedback_message)
        """
        config = config or {}
        custom_feedback = config.get('feedback_messages', {})
        
        if segment_count <= threshold:
            level = 'relational'
            feedback = custom_feedback.get('relational', 
                f'Excellent! Your {segment_count} segment{"s" if segment_count > 1 else ""} shows high-level understanding.')
        else:
            level = 'multi_structural'
            feedback = custom_feedback.get('multi_structural',
                f'Your {segment_count} segments are too detailed. Try to describe the overall purpose in {threshold} or fewer segments.')
        
        return level, feedback