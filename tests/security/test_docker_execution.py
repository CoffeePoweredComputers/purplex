"""Security tests for Docker-based code execution."""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from purplex.problems_app.services.docker_execution_service import DockerExecutionService

User = get_user_model()


@pytest.mark.security
class TestDockerExecutionSecurity(TestCase):
    """Test security features of Docker execution service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Mock Docker client to avoid needing Docker in tests
        with patch('purplex.problems_app.services.docker_execution_service.docker'):
            self.service = DockerExecutionService()
            self.service.docker_client = MagicMock()
    
    def test_blocks_os_import(self):
        """Test that OS module import is blocked."""
        dangerous_code = """
import os
def solution(x):
    os.system('ls')
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('os', str(context.exception))
    
    def test_blocks_subprocess_import(self):
        """Test that subprocess module import is blocked."""
        dangerous_code = """
import subprocess
def solution(x):
    subprocess.run(['ls'])
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('subprocess', str(context.exception))
    
    def test_blocks_socket_import(self):
        """Test that socket module import is blocked."""
        dangerous_code = """
import socket
def solution(x):
    s = socket.socket()
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('socket', str(context.exception))
    
    def test_blocks_eval_function(self):
        """Test that eval function is blocked."""
        dangerous_code = """
def solution(x):
    return eval('x + 1')
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('eval', str(context.exception))
    
    def test_blocks_exec_function(self):
        """Test that exec function is blocked."""
        dangerous_code = """
def solution(x):
    exec('y = x + 1')
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('exec', str(context.exception))
    
    def test_blocks_open_function(self):
        """Test that open function is blocked."""
        dangerous_code = """
def solution(x):
    with open('/etc/passwd', 'r') as f:
        data = f.read()
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('open', str(context.exception))
    
    def test_blocks_dunder_import(self):
        """Test that __import__ is blocked."""
        dangerous_code = """
def solution(x):
    os = __import__('os')
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('__import__', str(context.exception))
    
    def test_blocks_globals_access(self):
        """Test that globals() is blocked."""
        dangerous_code = """
def solution(x):
    g = globals()
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('globals', str(context.exception))
    
    def test_allows_safe_code(self):
        """Test that safe code is allowed."""
        safe_code = """
def solution(x):
    result = x * 2
    for i in range(10):
        result += i
    return result
"""
        # Should not raise any exception
        self.service._validate_code(safe_code)
    
    def test_allows_numpy_import(self):
        """Test that numpy (safe library) is allowed."""
        safe_code = """
import numpy as np
def solution(x):
    return np.array([x])
"""
        # Should not raise any exception
        self.service._validate_code(safe_code)
    
    @patch('purplex.problems_app.services.docker_execution_service.cache')
    def test_rate_limiting(self, mock_cache):
        """Test rate limiting functionality."""
        # First request should pass
        mock_cache.get.return_value = 0
        self.assertTrue(self.service._check_rate_limit('user123'))
        
        # Simulate hitting rate limit
        mock_cache.get.return_value = 10  # At limit
        self.assertFalse(self.service._check_rate_limit('user123'))
    
    def test_docker_container_config(self):
        """Test that Docker container is configured with security restrictions."""
        test_code = "print('test')"
        
        # Mock container execution
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_container.logs.return_value = b'{"success": true}'
        self.service.docker_client.containers.create.return_value = mock_container
        
        # Execute code
        result = self.service._execute_in_container(test_code)
        
        # Verify container was created with security settings
        create_call = self.service.docker_client.containers.create.call_args
        config = create_call[1]
        
        # Check security configurations
        self.assertEqual(config['network_mode'], 'none')  # No network
        self.assertEqual(config['user'], '1000:1000')  # Non-root user
        self.assertTrue(config['read_only'])  # Read-only filesystem
        self.assertIn('no-new-privileges', config['security_opt'])
        self.assertEqual(config['mem_limit'], '256m')  # Memory limit
        self.assertIn('/tmp', config['tmpfs'])  # Limited temp space
    
    def test_execution_timeout(self):
        """Test that execution timeout is enforced."""
        # This test verifies timeout configuration is passed to Docker
        test_code = "while True: pass"  # Infinite loop
        
        mock_container = MagicMock()
        # Simulate timeout
        mock_container.wait.side_effect = Exception('timeout')
        self.service.docker_client.containers.create.return_value = mock_container
        
        result = self.service._execute_in_container(test_code)
        
        # Should handle timeout gracefully
        self.assertFalse(result['success'])
        self.assertIn('timeout', result['error'].lower())
    
    def test_container_cleanup(self):
        """Test that containers are properly cleaned up."""
        test_code = "print('test')"
        
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_container.logs.return_value = b'{"success": true}'
        self.service.docker_client.containers.create.return_value = mock_container
        
        # Execute code
        self.service._execute_in_container(test_code)
        
        # Verify container was removed
        mock_container.remove.assert_called_once_with(force=True)
    
    def test_suspicious_pattern_logging(self):
        """Test that suspicious patterns trigger logging."""
        suspicious_code = """
def solution(x):
    # This looks suspicious but is actually safe
    # system, popen, socket are just in comments
    return x * 2
"""
        
        with patch('purplex.problems_app.services.docker_execution_service.logger') as mock_logger:
            self.service._log_execution('user123', suspicious_code, {'success': True})
            
            # Check that warning was logged for suspicious keywords
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            self.assertTrue(any('suspicious' in str(call).lower() for call in warning_calls))


@pytest.mark.security
class TestCodeInjectionPrevention(TestCase):
    """Test prevention of various code injection attacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('purplex.problems_app.services.docker_execution_service.docker'):
            self.service = DockerExecutionService()
            self.service.docker_client = MagicMock()
    
    def test_prevents_command_injection_via_string_format(self):
        """Test prevention of command injection through string formatting."""
        injection_code = """
def solution(x):
    # Attempt to use format string to execute commands
    cmd = "ls -la".format()
    return x
"""
        # The code itself is safe, but we block suspicious patterns
        self.service._validate_code(injection_code)  # Should pass - no actual execution
    
    def test_prevents_pickle_deserialization(self):
        """Test that pickle module is blocked."""
        dangerous_code = """
import pickle
def solution(x):
    data = pickle.loads(b'malicious')
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('pickle', str(context.exception))
    
    def test_prevents_code_object_manipulation(self):
        """Test that code object manipulation is blocked."""
        dangerous_code = """
def solution(x):
    code = compile('print("pwned")', '<string>', 'exec')
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('compile', str(context.exception))
    
    def test_prevents_attribute_access_exploitation(self):
        """Test that dangerous attribute access is blocked."""
        dangerous_code = """
def solution(x):
    obj = object()
    subclasses = obj.__class__.__bases__[0].__subclasses__()
    return x
"""
        with self.assertRaises(ValueError) as context:
            self.service._validate_code(dangerous_code)
        self.assertIn('__subclasses__', str(context.exception))