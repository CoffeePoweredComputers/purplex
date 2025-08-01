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
                    'inputs': inputs,
                    'function_call': self._format_function_call(function_name, inputs)
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
                'inputs': inputs,
                'function_call': self._format_function_call(function_name, inputs)
            }
            
        except Exception as e:
            return {
                'pass': False,
                'error': str(e),
                'actual_output': None,
                'expected_output': expected_output,
                'inputs': inputs,
                'traceback': traceback.format_exc(),
                'function_call': self._format_function_call(function_name, inputs)
            }
    
    def _format_function_call(self, function_name: str, inputs: List[Any]) -> str:
        """Format a function call string for display"""
        args = []
        for arg in inputs:
            if isinstance(arg, str):
                args.append(f'"{arg}"')
            elif isinstance(arg, list):
                # Format list with proper string representation
                formatted_items = []
                for item in arg:
                    if isinstance(item, str):
                        formatted_items.append(f'"{item}"')
                    else:
                        formatted_items.append(str(item))
                args.append(f"[{', '.join(formatted_items)}]")
            elif isinstance(arg, dict):
                args.append(str(arg))
            else:
                args.append(str(arg))
        return f"{function_name}({', '.join(args)})"
    
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


class SegmentationService:
    """Service for prompt segmentation analysis using GPT-4"""
    
    # Few-shot examples for consistent segmentation analysis
    SEGMENTATION_EXAMPLES = {
        'relational': {
            'prompt': 'The function checks if a word is a palindrome by comparing it with its reverse',
            'segments': [
                'checks if a word is a palindrome by comparing it with its reverse'
            ],
            'code_lines': [[1, 2, 3, 4, 5]],  # Maps to entire function
            'explanation': 'High-level description of overall purpose in 1-2 segments'
        },
        'multi_structural': {
            'prompt': 'It starts by taking the input string. Then it converts each character to lowercase. After that it creates a new empty string. It loops through each character from the end. It adds each character to the new string. Finally it checks if the original and reversed strings are equal.',
            'segments': [
                'takes the input string',
                'converts each character to lowercase', 
                'creates a new empty string',
                'loops through each character from the end',
                'adds each character to the new string',
                'checks if the original and reversed strings are equal'
            ],
            'code_lines': [[1], [2], [3], [4], [4], [5]],  # Line-by-line mapping
            'explanation': 'Detailed line-by-line description with many segments'
        }
    }
    
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
        
        # Use custom examples if provided, otherwise use defaults
        examples = custom_examples if custom_examples else self.SEGMENTATION_EXAMPLES
        
        prompt = """You are an expert at analyzing student explanations of code. Your task is to:

1. Segment the student's explanation into distinct semantic units
2. Map each segment to the relevant lines of code
3. Classify the explanation type

REFERENCE CODE:
```python
{}
```

SEGMENTATION EXAMPLES:

RELATIONAL (High-level understanding):
Student prompt: "{}"
Segments:
{}

MULTI-STRUCTURAL (Line-by-line description):
Student prompt: "{}"
Segments:
{}

INSTRUCTIONS:
- Segment the student explanation into meaningful semantic units
- Each segment should represent a distinct concept or action
- Map segments to code lines (1-indexed)
- Remove any segments that just describe function definition/signature
- Return your analysis as JSON in this exact format:

{{
    "segments": [
        {{"id": 1, "text": "segment text here", "code_lines": [1, 2, 3]}},
        {{"id": 2, "text": "another segment", "code_lines": [4, 5]}}
    ]
}}

Be precise and consistent in your segmentation.""".format(
            reference_code,
            examples['relational']['prompt'],
            self._format_example_segments(examples['relational']['segments'], examples['relational']['code_lines']),
            examples['multi_structural']['prompt'],
            self._format_example_segments(examples['multi_structural']['segments'], examples['multi_structural']['code_lines'])
        )
        
        return prompt
    
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
