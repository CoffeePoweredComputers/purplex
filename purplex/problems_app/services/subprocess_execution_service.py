"""
Subprocess-based code execution service.
Replaces Docker-in-Docker with simpler subprocess execution.
"""

import json
import subprocess
import tempfile
import os
import signal
import resource
import time
from typing import Dict, List
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SubprocessExecutionService:
    """Service for running Python code securely using subprocess with resource limits."""

    def __init__(self):
        """Initialize the subprocess execution service."""
        # Load security settings
        security_config = getattr(settings, 'CODE_EXECUTION', {})
        self.max_execution_time = security_config.get('MAX_EXECUTION_TIME', 5)
        self.max_memory_mb = int(security_config.get('MAX_MEMORY', '256m').rstrip('m'))
        self.rate_limit_per_minute = security_config.get('RATE_LIMIT_PER_MINUTE', 10)
        self.forbidden_imports = security_config.get('FORBIDDEN_IMPORTS', [
            'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
            '__builtin__', '__builtins__', 'compile', 'eval', 'exec',
            'importlib', 'open', 'file', 'input', 'raw_input'
        ])
        self.log_executions = security_config.get('LOG_EXECUTIONS', True)

    def test_solution(self, user_code: str, function_name: str, test_cases: List[Dict]) -> Dict:
        """
        Test a solution against provided test cases using subprocess.

        Args:
            user_code: The user's code to test
            function_name: Name of the function to test
            test_cases: List of test cases with inputs and expected outputs

        Returns:
            Dict with test results
        """
        user_id = getattr(self, '_current_user_id', 'anonymous')

        # Check rate limiting
        if not self._check_rate_limit(user_id):
            return {
                'error': 'Rate limit exceeded. Please wait before submitting again.',
                'testsPassed': 0,
                'totalTests': len(test_cases),
                'results': [],
                'success': False
            }

        # Validate code
        try:
            self._validate_code(user_code)
        except ValueError as e:
            return {
                'error': str(e),
                'testsPassed': 0,
                'totalTests': len(test_cases),
                'results': [],
                'success': False
            }

        # Create test runner code
        test_runner = self._create_test_runner(user_code, function_name, test_cases)

        # Execute using subprocess
        result = self._execute_code(test_runner)

        # Log execution if enabled
        if self.log_executions:
            self._log_execution(user_id, user_code, result)

        # Parse and return results
        if result['success']:
            try:
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

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        current_minute = timezone.now().strftime('%Y%m%d%H%M')
        rate_key = f'exec_rate:{user_id}:{current_minute}'

        count = cache.get(rate_key, 0)
        if count >= self.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False

        cache.set(rate_key, count + 1, 60)
        return True

    def _validate_code(self, user_code: str):
        """Validate code for forbidden patterns."""
        code_lower = user_code.lower()

        # Check for forbidden imports
        for forbidden in self.forbidden_imports:
            patterns = [
                f'import {forbidden}',
                f'from {forbidden}',
                f'__import__("{forbidden}")',
                f"__import__('{forbidden}')",
            ]
            for pattern in patterns:
                if pattern in code_lower:
                    raise ValueError(f"Forbidden import detected: {forbidden}")

        # Check for suspicious patterns
        suspicious_patterns = [
            'exec(', 'eval(', 'compile(', 'open(',
            'globals(', 'locals(', 'vars(',
            '__dict__', '__class__', '__bases__',
            '__subclasses__', '__code__', '__builtins__'
        ]

        for pattern in suspicious_patterns:
            if pattern in user_code:
                logger.warning(f"Suspicious pattern detected: {pattern}")
                raise ValueError(f"Suspicious code pattern detected: {pattern}")

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

    # Handle list/tuple equivalence
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return False
        return all(compare_results(a, e) for a, e in zip(actual, expected))

    # Handle dict comparison
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(compare_results(actual[k], expected[k]) for k in actual.keys())

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

        # Call the function
        actual = {function_name}(*inputs)

        # Compare results
        test_passed = compare_results(actual, expected)

        if test_passed:
            passed_count += 1

        # Format the function call string
        args_str = ', '.join(json.dumps(arg) if isinstance(arg, str) else repr(arg) for arg in inputs)
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
        args_str = ', '.join(json.dumps(arg) if isinstance(arg, str) else repr(arg) for arg in inputs)
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

    def _set_resource_limits(self):
        """Set resource limits for the subprocess."""
        # Set memory limit (in bytes)
        memory_limit = self.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

        # Set CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (self.max_execution_time, self.max_execution_time))

        # Set process limits
        resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))

        # Set file descriptor limits
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

    def _execute_code(self, code: str) -> Dict:
        """Execute code in a subprocess with resource limits."""

        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute the code with timeout
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=self.max_execution_time,
                preexec_fn=self._set_resource_limits if os.name != 'nt' else None
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
                    'output': None,
                    'error': result.stderr or 'Code execution failed'
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': None,
                'error': f'Code execution exceeded {self.max_execution_time} seconds'
            }
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return {
                'success': False,
                'output': None,
                'error': str(e)
            }
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass

    def _log_execution(self, user_id: str, code: str, result: Dict):
        """Log code execution for auditing."""
        logger.info(f"Code execution by user {user_id}: success={result['success']}")
        if not result['success']:
            logger.warning(f"Code execution failed for user {user_id}: {result.get('error', 'Unknown error')}")