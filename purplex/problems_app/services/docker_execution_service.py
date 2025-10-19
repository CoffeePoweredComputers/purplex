"""Docker-based secure code execution service with container pooling."""
import json
import logging
import hashlib
import time
import threading
import atexit
import concurrent.futures
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

        # Health monitoring settings
        self.health_check_interval = security_config.get('POOL_HEALTH_CHECK_INTERVAL', 60)  # Check every 60s
        self.container_max_age = security_config.get('POOL_CONTAINER_MAX_AGE', 3600)  # Rotate after 1 hour
        self.max_restart_attempts = security_config.get('POOL_MAX_RESTART_ATTEMPTS', 3)

        # Container metadata tracking: {container_id: {'created_at': timestamp, 'restart_count': int, 'last_health_check': timestamp}}
        self.container_metadata = {}
        self.pool_metrics = {
            'total_created': 0,
            'total_removed': 0,
            'health_checks_performed': 0,
            'unhealthy_containers_removed': 0,
            'age_rotations': 0,
            'docker_errors': 0,
            'last_health_check': None,
            # Enhanced monitoring metrics
            'pool_requests_total': 0,       # Total _get_container_from_pool calls
            'pool_hits': 0,                 # Got container from pool
            'pool_misses': 0,               # Had to create new container
            'pool_wait_time_total': 0.0,    # Cumulative time spent acquiring containers
            'containers_active_peak': 0,    # Most containers in use at once
            'cleanup_failures': 0,          # Failed container cleanup attempts
            'last_metrics_log': time.time(), # Last time metrics were logged
        }

        # Health monitor thread
        self._health_monitor_thread = None
        self._stop_health_monitor = threading.Event()
        self._docker_available = True  # Track Docker daemon availability

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self._ensure_image_exists()

            # Initialize container pool if enabled
            if self.pool_enabled:
                self._init_pool()
                # Start health monitoring
                self._start_health_monitor()
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
                # Track container metadata
                container_id = container.id
                self.container_metadata[container_id] = {
                    'created_at': time.time(),
                    'restart_count': 0,
                    'last_health_check': time.time(),
                    'execution_count': 0
                }
                self.pool_metrics['total_created'] += 1
                return container
            else:
                logger.warning(f"Container {container.id[:12]} not running, status: {container.status}")
                container.remove(force=True)
                return None
                
        except Exception as e:
            logger.error(f"Failed to create pool container: {e}")
            return None

    def _start_health_monitor(self):
        """Start the background health monitoring thread."""
        if self._health_monitor_thread is not None:
            logger.warning("Health monitor already running")
            return

        self._stop_health_monitor.clear()
        self._health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True,
            name='DockerPoolHealthMonitor'
        )
        self._health_monitor_thread.start()
        logger.info(f"Started container pool health monitor (interval: {self.health_check_interval}s)")

    def _stop_health_monitor_thread(self):
        """Stop the background health monitoring thread."""
        if self._health_monitor_thread is None:
            return

        logger.info("Stopping health monitor thread")
        self._stop_health_monitor.set()

        # Wait for thread to finish (with timeout)
        self._health_monitor_thread.join(timeout=5.0)
        if self._health_monitor_thread.is_alive():
            logger.warning("Health monitor thread did not stop gracefully")
        else:
            logger.info("Health monitor thread stopped")

        self._health_monitor_thread = None

    def _health_monitor_loop(self):
        """Main loop for health monitoring - runs in background thread."""
        logger.info("Health monitor thread started")

        while not self._stop_health_monitor.is_set():
            try:
                # Wait for interval or stop signal
                if self._stop_health_monitor.wait(timeout=self.health_check_interval):
                    break  # Stop signal received

                # Perform health check
                self._perform_health_check()

            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}", exc_info=True)
                # Continue monitoring despite errors

        logger.info("Health monitor thread exiting")

    def _perform_health_check(self):
        """Perform health check on all pool containers."""
        if not self.pool_enabled or not self._docker_available:
            return

        start_time = time.time()
        checked_count = 0
        removed_count = 0
        rotated_count = 0

        try:
            # Check Docker daemon availability first
            try:
                self.docker_client.ping()
            except Exception as e:
                logger.error(f"Docker daemon unavailable: {e}")
                self._handle_docker_unavailable()
                return

            # If we reach here, Docker is available again
            if not self._docker_available:
                logger.info("Docker daemon available again, re-enabling pool")
                self._docker_available = True

            with self.pool_lock:
                current_time = time.time()
                containers_to_check = list(self.container_pool)

                for container in containers_to_check:
                    checked_count += 1
                    container_id = container.id

                    try:
                        # Reload container state
                        container.reload()

                        # Get metadata
                        metadata = self.container_metadata.get(container_id, {})
                        created_at = metadata.get('created_at', current_time)
                        restart_count = metadata.get('restart_count', 0)
                        container_age = current_time - created_at

                        # Health check criteria
                        is_running = container.status == 'running'
                        is_too_old = container_age > self.container_max_age
                        is_restarted_too_much = restart_count > self.max_restart_attempts

                        # Remove unhealthy containers
                        if not is_running:
                            logger.warning(
                                f"Container {container_id[:12]} unhealthy (status: {container.status}), removing"
                            )
                            self.container_pool.remove(container)
                            container.remove(force=True)
                            removed_count += 1
                            self.pool_metrics['unhealthy_containers_removed'] += 1

                            # Clean up metadata
                            self.container_metadata.pop(container_id, None)

                        elif is_too_old:
                            logger.info(
                                f"Container {container_id[:12]} exceeded max age "
                                f"({container_age:.0f}s > {self.container_max_age}s), rotating"
                            )
                            self.container_pool.remove(container)
                            container.remove(force=True)
                            rotated_count += 1
                            self.pool_metrics['age_rotations'] += 1

                            # Clean up metadata
                            self.container_metadata.pop(container_id, None)

                            # Create replacement
                            try:
                                new_container = self._create_pool_container()
                                if new_container:
                                    self.container_pool.append(new_container)
                                    logger.debug(f"Created replacement container {new_container.id[:12]}")
                            except Exception as e:
                                logger.error(f"Failed to create replacement container: {e}")

                        elif is_restarted_too_much:
                            logger.warning(
                                f"Container {container_id[:12]} restarted too many times ({restart_count}), removing"
                            )
                            self.container_pool.remove(container)
                            container.remove(force=True)
                            removed_count += 1
                            self.pool_metrics['unhealthy_containers_removed'] += 1

                            # Clean up metadata
                            self.container_metadata.pop(container_id, None)

                        else:
                            # Container is healthy, update last check time
                            if container_id in self.container_metadata:
                                self.container_metadata[container_id]['last_health_check'] = current_time

                    except Exception as e:
                        logger.warning(f"Error checking container {container_id[:12]}: {e}")
                        # Try to remove problematic container
                        try:
                            self.container_pool.remove(container)
                            container.remove(force=True)
                            removed_count += 1
                            self.container_metadata.pop(container_id, None)
                        except:
                            pass

                # Replenish pool if needed
                current_pool_size = len(self.container_pool)
                if current_pool_size < self.pool_size:
                    needed = self.pool_size - current_pool_size
                    logger.info(f"Replenishing pool: creating {needed} containers")

                    for i in range(needed):
                        try:
                            container = self._create_pool_container()
                            if container:
                                self.container_pool.append(container)
                        except Exception as e:
                            logger.error(f"Failed to replenish container {i+1}/{needed}: {e}")
                            break  # Don't overwhelm on repeated failures

            # Update metrics
            self.pool_metrics['health_checks_performed'] += 1
            self.pool_metrics['last_health_check'] = current_time

            duration = time.time() - start_time

            if removed_count > 0 or rotated_count > 0:
                logger.info(
                    f"Health check complete: checked={checked_count}, removed={removed_count}, "
                    f"rotated={rotated_count}, pool_size={len(self.container_pool)}, duration={duration:.2f}s"
                )
            else:
                logger.debug(
                    f"Health check complete: pool_size={len(self.container_pool)}, duration={duration:.2f}s"
                )

        except Exception as e:
            logger.error(f"Critical error in health check: {e}", exc_info=True)
            self.pool_metrics['docker_errors'] += 1

    def _handle_docker_unavailable(self):
        """Handle Docker daemon being unavailable."""
        if self._docker_available:
            logger.critical("Docker daemon unavailable - disabling container pool")
            self._docker_available = False
            self.pool_metrics['docker_errors'] += 1

        # Clear pool since containers are likely invalid
        with self.pool_lock:
            self.container_pool.clear()
            self.container_metadata.clear()

    def get_pool_metrics(self):
        """Get current pool metrics for monitoring/debugging."""
        with self.pool_lock:
            total_requests = self.pool_metrics['pool_requests_total']
            hit_rate = (self.pool_metrics['pool_hits'] / total_requests * 100) if total_requests > 0 else 0.0
            avg_wait_time = (self.pool_metrics['pool_wait_time_total'] / total_requests) if total_requests > 0 else 0.0

            return {
                'pool_size': len(self.container_pool),
                'pool_max_size': self.pool_size,
                'pool_hit_rate': round(hit_rate, 2),
                'pool_avg_wait_time': round(avg_wait_time, 3),
                'docker_available': self._docker_available,
                'containers_tracked': len(self.container_metadata),
                **self.pool_metrics
            }

    def log_metrics_if_needed(self):
        """Log metrics periodically (every hour)"""
        current_time = time.time()
        last_log = self.pool_metrics.get('last_metrics_log', 0)

        # Log every hour (3600 seconds)
        if current_time - last_log > 3600:
            metrics = self.get_pool_metrics()
            logger.info(f"HOURLY_POOL_METRICS: {json.dumps(metrics)}")
            with self.pool_lock:
                self.pool_metrics['last_metrics_log'] = current_time

    def _get_container_from_pool(self):
        """Get a container from the pool or create a new one."""
        start_time = time.time()

        # Track request
        with self.pool_lock:
            self.pool_metrics['pool_requests_total'] += 1

            while self.container_pool:
                self.pool_metrics['pool_hits'] += 1
                container = self.container_pool.pop()

                # Check if container is healthy
                try:
                    container.reload()
                    if container.status == 'running':
                        # Track wait time
                        wait_time = time.time() - start_time
                        self.pool_metrics['pool_wait_time_total'] += wait_time

                        logger.debug(f"Retrieved container {container.id[:12]} from pool (wait: {wait_time:.3f}s)")

                        # Log metrics periodically
                        self.log_metrics_if_needed()

                        return container
                    else:
                        # Container is not healthy, remove it
                        logger.warning(f"Removing unhealthy container {container.id[:12]} from pool")
                        try:
                            container.remove(force=True)
                        except:
                            self.pool_metrics['cleanup_failures'] += 1
                except Exception as e:
                    logger.warning(f"Error checking container health: {e}")
                    continue

        # Pool is empty - track miss
        with self.pool_lock:
            self.pool_metrics['pool_misses'] += 1
            total_requests = self.pool_metrics['pool_requests_total']
            hit_rate = (self.pool_metrics['pool_hits'] / total_requests * 100) if total_requests > 0 else 0

            logger.info(
                f"Pool miss: creating new container "
                f"(requests={total_requests}, hit_rate={hit_rate:.1f}%, "
                f"pool_size={len(self.container_pool)}/{self.pool_size})"
            )

        container = self._create_pool_container()

        # Track wait time
        wait_time = time.time() - start_time
        with self.pool_lock:
            self.pool_metrics['pool_wait_time_total'] += wait_time

        # Log metrics periodically
        self.log_metrics_if_needed()

        return container
    
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

            # Track execution count
            container_id = container.id
            if container_id in self.container_metadata:
                self.container_metadata[container_id]['execution_count'] = \
                    self.container_metadata[container_id].get('execution_count', 0) + 1

            # PERFORMANCE FIX: Clean tmpfs directories between executions
            # Previously: No cleanup led to stale state accumulation
            # Now: Explicit cleanup ensures isolation while maintaining pool performance
            try:
                # Clean /tmp and /sandbox tmpfs mounts
                cleanup_script = '''
import os
import shutil

# Clean /tmp (keeping directory structure)
for item in os.listdir('/tmp'):
    item_path = os.path.join('/tmp', item)
    try:
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
    except Exception:
        pass

# Clean /sandbox (keeping directory structure)
for item in os.listdir('/sandbox'):
    if item != '__pycache__':  # Keep cache dir
        item_path = os.path.join('/sandbox', item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception:
            pass
'''
                # Execute cleanup in container (fast, ~50ms)
                cleanup_result = container.exec_run(
                    cmd=['python', '-c', cleanup_script],
                    user='sandbox',
                    workdir='/sandbox'
                )

                if cleanup_result.exit_code != 0:
                    logger.warning(f"Container {container.id[:12]} cleanup failed, removing from pool")
                    container.remove(force=True)
                    return

            except Exception as cleanup_error:
                logger.warning(f"Container {container.id[:12]} cleanup error: {cleanup_error}, removing")
                container.remove(force=True)
                return

            # Return directly to pool after cleanup
            with self.pool_lock:
                if len(self.container_pool) < self.pool_size:
                    self.container_pool.append(container)
                    logger.debug(f"Returned container {container.id[:12]} to pool (cleaned)")
                else:
                    # Pool is full, remove container
                    logger.debug(f"Pool full, removing container {container.id[:12]}")
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

        # Stop health monitor first
        if self._health_monitor_thread:
            self._stop_health_monitor_thread()

        # BUGFIX: Always enable orphan cleanup on shutdown
        # Previously: orphan cleanup was conditional and rarely ran
        # Now: ensures all pool containers are cleaned up
        self._do_orphan_cleanup = True

        # Clean up container pool
        self._cleanup_pool()

        # Log final metrics
        if self.pool_metrics['health_checks_performed'] > 0:
            logger.info(f"Final pool metrics: {self.get_pool_metrics()}")

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

        # Validate function name first (prevent code injection)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', function_name):
            return {
                'error': f'Invalid function name: {function_name}',
                'testsPassed': 0,
                'totalTests': len(test_cases),
                'results': [],
                'success': False
            }

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
            except json.JSONDecodeError as e:
                # BUGFIX: When JSON parsing fails, create proper error results
                # Previously: Returned empty results array with non-zero totalTests
                # Now: Generate error results for each test case to preserve test execution data
                logger.error(f"Failed to parse Docker output as JSON: {e}")
                logger.debug(f"Raw output (first 500 chars): {result['output'][:500]}")

                error_results = [
                    {
                        'test_number': i + 1,
                        'inputs': test_cases[i].get('inputs', []),
                        'expected_output': test_cases[i].get('expected_output'),
                        'actual_output': None,
                        'isSuccessful': False,
                        'error': 'Failed to parse test results - output may have been truncated or corrupted',
                        'function_call': f"{function_name}(...)"
                    }
                    for i in range(len(test_cases))
                ]

                return {
                    'error': f'Failed to parse test results: {str(e)}',
                    'testsPassed': 0,
                    'totalTests': len(test_cases),
                    'results': error_results,
                    'success': False
                }
        else:
            # BUGFIX: When execution fails, create proper error results
            # Previously: Returned empty results array with non-zero totalTests
            # Now: Generate error results for each test case to preserve test execution data
            error_message = result.get('error', 'Code execution failed')
            logger.warning(f"Docker execution failed: {error_message}")

            error_results = [
                {
                    'test_number': i + 1,
                    'inputs': test_cases[i].get('inputs', []),
                    'expected_output': test_cases[i].get('expected_output'),
                    'actual_output': None,
                    'isSuccessful': False,
                    'error': error_message,
                    'function_call': f"{function_name}(...)"
                }
                for i in range(len(test_cases))
            ]

            return {
                'error': error_message,
                'testsPassed': 0,
                'totalTests': len(test_cases),
                'results': error_results,
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
            '__subclasses__', '__code__', '__builtins__',
            '__globals__',  # Prevent __globals__ attribute access
            '__import__',   # Catch __import__ calls
            'getattr(',     # Already in forbidden_builtins, double-check here
            # Removed: chr(), ord(), .encode(), .decode() - these are legitimate for string/encoding problems
            'base64',       # Base64 encoding bypass attempts (keep this - not common in intro problems)
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
        # Check if Docker is available
        if not self._docker_available:
            logger.warning("Docker unavailable, attempting fallback to new container")
            return self._execute_in_new_container(code)

        container = None

        try:
            # Get container from pool
            container = self._get_container_from_pool()
            if not container:
                # Fallback to creating new container
                logger.warning("Failed to get pooled container, falling back to new container")
                return self._execute_in_new_container(code)
            
            # Execute code in the container with enforced timeout
            try:
                # Use ThreadPoolExecutor to enforce timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    # Submit exec_run as a future
                    future = executor.submit(
                        container.exec_run,
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
                        demux=False
                    )

                    try:
                        # Wait for result with timeout
                        exec_result = future.result(timeout=self.max_execution_time)
                    except concurrent.futures.TimeoutError:
                        # Timeout exceeded - kill the container
                        logger.warning(f"Execution exceeded {self.max_execution_time}s timeout")
                        try:
                            container.kill()
                            container.remove(force=True)
                        except:
                            pass
                        return {
                            'success': False,
                            'output': '',
                            'error': f'Code execution timed out after {self.max_execution_time} seconds'
                        }

                # Parse result with output size limit
                MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
                exit_code = exec_result.exit_code

                if exec_result.output:
                    output_bytes = exec_result.output
                    if len(output_bytes) > MAX_OUTPUT_SIZE:
                        # Truncate output
                        output = output_bytes[:MAX_OUTPUT_SIZE].decode('utf-8', errors='ignore')
                        output += f"\n\n... (output truncated at {MAX_OUTPUT_SIZE} bytes)"
                        logger.warning(f"Output truncated: {len(output_bytes)} bytes > {MAX_OUTPUT_SIZE} bytes")
                    else:
                        output = output_bytes.decode('utf-8', errors='ignore')
                else:
                    output = ''

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

            # Get output with size limit
            MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
            logs_bytes = container.logs(stdout=True, stderr=True)

            if len(logs_bytes) > MAX_OUTPUT_SIZE:
                # Truncate output
                logs = logs_bytes[:MAX_OUTPUT_SIZE].decode('utf-8', errors='ignore')
                logs += f"\n\n... (output truncated at {MAX_OUTPUT_SIZE} bytes)"
                logger.warning(f"Output truncated: {len(logs_bytes)} bytes > {MAX_OUTPUT_SIZE} bytes")
            else:
                logs = logs_bytes.decode('utf-8', errors='ignore')

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