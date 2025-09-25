"""Docker-based secure code execution service with container pooling."""
import json
import logging
import hashlib
import time
import threading
import atexit
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

try:
    import docker
    from docker.errors import ContainerError, ImageNotFound, APIError
except ImportError:
    docker = None

logger = logging.getLogger(__name__)


class DockerExecutionService:
    """Service for running Python code securely in Docker containers."""
    
    def __init__(self):
        """Initialize the Docker execution service with container pooling."""
        if docker is None:
            raise ImportError("Docker SDK is not installed. Run: pip install docker")

        # Load security settings
        security_config = getattr(settings, 'CODE_EXECUTION', {})
        self.max_execution_time = security_config.get('MAX_EXECUTION_TIME', 5)
        self.max_memory = security_config.get('MAX_MEMORY', '256m')
        self.max_cpu_percent = security_config.get('MAX_CPU_PERCENT', 50)
        self.docker_image = security_config.get('DOCKER_IMAGE', 'purplex/python-sandbox:latest')
        self.forbidden_imports = security_config.get('FORBIDDEN_IMPORTS', [])
        self.forbidden_builtins = security_config.get('FORBIDDEN_BUILTINS', [])
        self.rate_limit_per_minute = security_config.get('RATE_LIMIT_PER_MINUTE', 10)
        self.log_executions = security_config.get('LOG_EXECUTIONS', True)

        # Container pool settings
        self.pool_enabled = security_config.get('POOL_ENABLED', True)
        self.pool_size = security_config.get('POOL_SIZE', 5)
        self.container_pool = []
        self.pool_lock = threading.Lock()
        self._pool_initialized = False
        self._closed = False

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self._ensure_image_exists()

            # Initialize container pool if enabled
            if self.pool_enabled:
                self._init_pool()
                # Register cleanup on exit
                atexit.register(self._cleanup_and_close)
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    
    def _ensure_image_exists(self):
        """Ensure the sandbox Docker image exists."""
        try:
            self.docker_client.images.get(self.docker_image)
            logger.info(f"Docker image {self.docker_image} found")
        except ImageNotFound:
            logger.warning(f"Docker image {self.docker_image} not found, attempting to build...")
            self._build_sandbox_image()
    
    def _build_sandbox_image(self):
        """Build the sandbox Docker image."""
        import os
        dockerfile_path = os.path.join(settings.BASE_DIR, 'docker', 'sandbox')
        
        try:
            image, logs = self.docker_client.images.build(
                path=dockerfile_path,
                tag=self.docker_image,
                rm=True,
                forcerm=True
            )
            logger.info(f"Successfully built Docker image {self.docker_image}")
            for log in logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            raise
    
    def _init_pool(self):
        """Initialize the container pool with warm containers."""
        if self._pool_initialized:
            return
            
        logger.info(f"Initializing container pool with {self.pool_size} containers")
        
        for i in range(self.pool_size):
            try:
                container = self._create_pool_container()
                if container:
                    self.container_pool.append(container)
                    logger.debug(f"Created pool container {i+1}/{self.pool_size}")
            except Exception as e:
                logger.warning(f"Failed to create pool container {i+1}: {e}")
        
        self._pool_initialized = True
        logger.info(f"Container pool initialized with {len(self.container_pool)} containers")
    
    def _create_pool_container(self):
        """Create a warm container for the pool."""
        # Container with a keep-alive Python process
        keep_alive_script = '''
import sys
import time
import signal

def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Keep the container alive
while True:
    time.sleep(1)
'''
        
        try:
            container = self.docker_client.containers.run(
                self.docker_image,
                command=['python', '-c', keep_alive_script],
                detach=True,
                network_mode='none',  # No network access
                mem_limit=self.max_memory,
                memswap_limit=self.max_memory,
                cpu_quota=self.max_cpu_percent * 1000,
                cpu_period=100000,
                pids_limit=50,
                read_only=True,
                security_opt=['no-new-privileges'],
                user='1000:1000',
                working_dir='/sandbox',
                tmpfs={
                    '/tmp': 'size=10M,mode=1777',
                    '/sandbox': 'size=1M,mode=755'
                },
                environment={
                    'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONUNBUFFERED': '1',
                    'PYTHONNOUSERSITE': '1'
                },
                ulimits=[docker.types.Ulimit(name='nofile', soft=64, hard=64)] if docker else [],
                labels={'purplex-pool': 'true'},  # Mark as pool container
                auto_remove=False  # Don't auto-remove, we'll manage lifecycle
            )
            
            # Wait a moment for container to stabilize
            time.sleep(0.1)
            
            # Verify container is running
            container.reload()
            if container.status == 'running':
                return container
            else:
                logger.warning(f"Container {container.id[:12]} not running, status: {container.status}")
                container.remove(force=True)
                return None
                
        except Exception as e:
            logger.error(f"Failed to create pool container: {e}")
            return None
    
    def _get_container_from_pool(self):
        """Get a container from the pool or create a new one."""
        with self.pool_lock:
            while self.container_pool:
                container = self.container_pool.pop()
                
                # Check if container is healthy
                try:
                    container.reload()
                    if container.status == 'running':
                        logger.debug(f"Retrieved container {container.id[:12]} from pool")
                        return container
                    else:
                        # Container is not healthy, remove it
                        logger.warning(f"Removing unhealthy container {container.id[:12]} from pool")
                        try:
                            container.remove(force=True)
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"Error checking container health: {e}")
                    continue
        
        # Pool is empty or all containers were unhealthy
        logger.info("Pool empty, creating new container")
        return self._create_pool_container()
    
    def _return_container_to_pool(self, container):
        """Return a container to the pool after cleaning it."""
        if not self.pool_enabled:
            # If pooling is disabled, just remove the container
            try:
                container.remove(force=True)
            except:
                pass
            return
        
        try:
            # Check if container is still healthy
            container.reload()
            if container.status != 'running':
                logger.warning(f"Container {container.id[:12]} not running, removing")
                container.remove(force=True)
                return
            
            # Restart container to clean state
            logger.debug(f"Restarting container {container.id[:12]} to clean state")
            container.restart(timeout=2)
            
            # Give it a moment to restart
            time.sleep(0.2)
            
            # Verify it's running again
            container.reload()
            if container.status == 'running':
                with self.pool_lock:
                    if len(self.container_pool) < self.pool_size:
                        self.container_pool.append(container)
                        logger.debug(f"Returned container {container.id[:12]} to pool")
                    else:
                        # Pool is full, remove container
                        logger.debug(f"Pool full, removing container {container.id[:12]}")
                        container.remove(force=True)
            else:
                logger.warning(f"Container {container.id[:12]} failed to restart, removing")
                container.remove(force=True)
                
        except Exception as e:
            logger.error(f"Error returning container to pool: {e}")
            try:
                container.remove(force=True)
            except:
                pass
    
    def _cleanup_pool(self):
        """Clean up all pool containers on shutdown."""
        logger.info("Cleaning up container pool")

        with self.pool_lock:
            for container in self.container_pool:
                try:
                    container.remove(force=True)
                    logger.debug(f"Removed pool container {container.id[:12]}")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

            self.container_pool.clear()

        # Clean up orphaned containers only on full cleanup (not every time)
        # This prevents excessive cleanup during normal operations
        if getattr(self, '_do_orphan_cleanup', False):
            try:
                if hasattr(self, 'docker_client') and self.docker_client:
                    containers = self.docker_client.containers.list(
                        all=True,
                        filters={'label': 'purplex-pool=true'}
                    )
                    if containers:
                        logger.info(f"Cleaning up {len(containers)} orphaned pool containers")
                        for container in containers:
                            try:
                                container.remove(force=True)
                                logger.debug(f"Removed orphaned pool container {container.id[:12]}")
                            except:
                                pass
            except Exception as e:
                logger.warning(f"Error cleaning orphaned containers: {e}")

    def close(self):
        """Close Docker client connection and clean up resources."""
        if self._closed:
            return

        logger.info("Closing Docker execution service")

        # Clean up container pool first
        self._cleanup_pool()

        # Close Docker client connection
        if hasattr(self, 'docker_client') and self.docker_client:
            try:
                self.docker_client.close()
                logger.debug("Docker client connection closed")
            except Exception as e:
                logger.warning(f"Error closing Docker client: {e}")
            finally:
                self.docker_client = None

        self._closed = True

    def _cleanup_and_close(self):
        """Cleanup method called by atexit."""
        self.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.close()

    def __del__(self):
        """Destructor - ensure cleanup if not already done."""
        try:
            self.close()
        except:
            # Ignore errors during destruction
            pass
    
    def test_solution(self, user_code: str, function_name: str, test_cases: List[Dict]) -> Dict:
        """
        Test a solution against provided test cases in a secure Docker container.
        
        Args:
            user_code: The user's code to test
            function_name: Name of the function to test
            test_cases: List of test cases with inputs and expected outputs
            
        Returns:
            Dict with test results matching the original service format
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
        
        # Validate and sanitize code
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
        
        # Execute in Docker container
        result = self._execute_in_container(test_runner)
        
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
        
        # Check for forbidden builtins
        for forbidden in self.forbidden_builtins:
            if forbidden + '(' in user_code:
                raise ValueError(f"Forbidden function detected: {forbidden}")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'exec(', 'eval(', 'compile(',
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
        
        # Same test runner as original service to maintain compatibility
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
        try:
            actual_json = json.loads(json.dumps(actual))
            expected_json = json.loads(json.dumps(expected))
            test_passed = actual_json == expected_json
        except:
            # If JSON serialization fails, fall back to direct comparison
            test_passed = compare_results(actual, expected)
            
        if test_passed:
            passed_count += 1
            
        # Format the function call string with proper repr for all arguments
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
    
    def _execute_in_container(self, code: str) -> Dict:
        """Execute code in a Docker container with pooling support."""
        
        # Use pooled container if enabled
        if self.pool_enabled:
            return self._execute_in_pooled_container(code)
        else:
            return self._execute_in_new_container(code)
    
    def _execute_in_pooled_container(self, code: str) -> Dict:
        """Execute code in a pooled container."""
        container = None
        
        try:
            # Get container from pool
            container = self._get_container_from_pool()
            if not container:
                # Fallback to creating new container
                logger.warning("Failed to get pooled container, falling back to new container")
                return self._execute_in_new_container(code)
            
            # Execute code in the container
            start_time = time.time()
            
            try:
                # Use exec_run to execute code in existing container
                exec_result = container.exec_run(
                    cmd=['python', '-c', code],
                    stdout=True,
                    stderr=True,
                    user='sandbox',
                    workdir='/sandbox',
                    environment={
                        'PYTHONDONTWRITEBYTECODE': '1',
                        'PYTHONUNBUFFERED': '1',
                        'PYTHONNOUSERSITE': '1'
                    },
                    demux=False  # Return combined stdout/stderr
                )
                
                # Check if execution took too long
                execution_time = time.time() - start_time
                if execution_time > self.max_execution_time:
                    logger.warning(f"Execution took {execution_time:.2f}s, exceeding timeout")
                    # Container might be compromised, don't return it to pool
                    try:
                        container.remove(force=True)
                    except:
                        pass
                    return {
                        'success': False,
                        'output': '',
                        'error': f'Code execution timed out after {self.max_execution_time} seconds'
                    }
                
                # Parse result
                exit_code = exec_result.exit_code
                output = exec_result.output.decode('utf-8') if exec_result.output else ''
                
                if exit_code == 0:
                    result = {
                        'success': True,
                        'output': output,
                        'error': None
                    }
                else:
                    result = {
                        'success': False,
                        'output': '',
                        'error': output if output else 'Code execution failed'
                    }
                
                # Return container to pool
                self._return_container_to_pool(container)
                return result
                
            except Exception as e:
                logger.error(f"Error executing in pooled container: {e}")
                # Container might be compromised, remove it
                try:
                    container.remove(force=True)
                except:
                    pass
                
                # Fallback to new container
                return self._execute_in_new_container(code)
                
        except Exception as e:
            logger.error(f"Unexpected error in pooled execution: {e}")
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
            return {
                'success': False,
                'output': '',
                'error': 'Unexpected execution error'
            }
    
    def _execute_in_new_container(self, code: str) -> Dict:
        """Execute code in a new Docker container (original implementation)."""
        
        # Container configuration with security restrictions
        container_config = {
            'image': self.docker_image,
            'command': ['python', '-c', code],
            'detach': True,
            'network_mode': 'none',  # No network access
            'mem_limit': self.max_memory,
            'memswap_limit': self.max_memory,  # Prevent swap usage
            'cpu_quota': self.max_cpu_percent * 1000,  # Convert percentage to microseconds
            'cpu_period': 100000,  # 100ms period
            'pids_limit': 50,  # Limit number of processes
            'read_only': True,  # Read-only root filesystem
            'security_opt': ['no-new-privileges'],  # Prevent privilege escalation
            'user': '1000:1000',  # Run as non-root user
            'working_dir': '/sandbox',
            'tmpfs': {
                '/tmp': 'size=10M,mode=1777',  # Limited temp space
                '/sandbox': 'size=1M,mode=755'  # Tiny working directory
            },
            'environment': {
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONUNBUFFERED': '1',
                'PYTHONNOUSERSITE': '1'
            },
            'ulimits': [
                docker.types.Ulimit(name='nofile', soft=64, hard=64)
            ] if docker else []
        }
        
        container = None
        try:
            # Create and start container
            container = self.docker_client.containers.create(**container_config)
            container.start()
            
            # Wait for completion with timeout
            exit_code = container.wait(timeout=self.max_execution_time)
            
            # Get output
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            # Check exit code
            if exit_code['StatusCode'] == 0:
                return {
                    'success': True,
                    'output': logs,
                    'error': None
                }
            else:
                # Execution failed
                return {
                    'success': False,
                    'output': '',
                    'error': logs if logs else 'Code execution failed'
                }
                
        except ContainerError as e:
            logger.error(f"Container execution error: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
        except APIError as e:
            if 'timeout' in str(e).lower():
                return {
                    'success': False,
                    'output': '',
                    'error': f'Code execution timed out after {self.max_execution_time} seconds'
                }
            logger.error(f"Docker API error: {e}")
            return {
                'success': False,
                'output': '',
                'error': 'Docker execution error'
            }
        except Exception as e:
            logger.error(f"Unexpected error during Docker execution: {e}")
            return {
                'success': False,
                'output': '',
                'error': 'Unexpected execution error'
            }
        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
    
    def _log_execution(self, user_id: str, code: str, result: Dict):
        """Log code execution for security audit."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'user_id': user_id,
            'code_hash': code_hash,
            'success': result.get('success', False),
            'error': result.get('error')
        }
        
        logger.info(f"Code execution: {json.dumps(log_entry)}")
        
        # Check for suspicious patterns and alert if needed
        suspicious_keywords = ['system', 'popen', 'socket', 'eval', 'exec']
        if any(keyword in code.lower() for keyword in suspicious_keywords):
            logger.warning(f"Suspicious code pattern detected for user {user_id}, hash: {code_hash}")
    
    def set_user_context(self, user_id: Optional[str]):
        """Set the current user context for rate limiting."""
        self._current_user_id = user_id or 'anonymous'
        return self