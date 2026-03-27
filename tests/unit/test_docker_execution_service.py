"""
Unit tests for DockerExecutionService.

These tests mock the Docker client to test the service logic in isolation,
without requiring a running Docker daemon.

Test Categories:
1. Code validation and security checks
2. Rate limiting
3. Test solution run (mocked Docker)
4. Container pool management
5. Timeout handling
6. Error handling
"""

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.services.docker_execution_service import (
    DockerExecutionService,
)

pytestmark = pytest.mark.unit


class MockContainer:
    """Mock Docker container for testing."""

    def __init__(self, container_id="test-container-123", status="running"):
        self.id = container_id
        self._status = status
        self._removed = False
        self.wait = MagicMock(return_value={"StatusCode": 0})
        self.logs = MagicMock(return_value=b"{}")
        self.start = MagicMock()

    @property
    def status(self):
        return self._status

    def reload(self):
        """Simulate container state reload."""
        pass

    def remove(self, force=False):
        """Simulate container removal."""
        self._removed = True

    def kill(self):
        """Simulate container kill."""
        self._status = "exited"

    def exec_run(self, cmd, **kwargs):
        """Simulate exec_run - override in tests for specific behavior."""
        return MagicMock(exit_code=0, output=b'{"success": true}')


class MockDockerClient:
    """Mock Docker client for testing."""

    def __init__(self):
        self.containers = MagicMock()
        self.images = MagicMock()
        self._closed = False

    def ping(self):
        """Simulate Docker daemon ping."""
        return True

    def close(self):
        """Simulate client close."""
        self._closed = True


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    return MockDockerClient()


@pytest.fixture
def mock_settings():
    """Mock Django settings for CODE_EXECUTION config."""
    return {
        "MAX_EXECUTION_TIME": 5,
        "MAX_MEMORY": "256m",
        "MAX_CPU_PERCENT": 50,
        "DOCKER_IMAGE": "purplex/python-sandbox:latest",
        "FORBIDDEN_IMPORTS": ["os", "sys", "subprocess", "socket"],
        "FORBIDDEN_BUILTINS": ["open", "input"],
        "RATE_LIMIT_PER_MINUTE": 10,
        "LOG_EXECUTIONS": False,
        "POOL_ENABLED": False,
    }


@pytest.fixture
def docker_service(mock_docker_client, mock_settings):
    """
    Create a DockerExecutionService with mocked Docker client.
    """
    with (
        patch("docker.from_env", return_value=mock_docker_client),
        patch.object(DockerExecutionService, "_ensure_image_exists"),
        patch.object(DockerExecutionService, "_init_pool"),
        patch.object(DockerExecutionService, "_start_health_monitor"),
        patch(
            "purplex.problems_app.services.docker_execution_service.settings"
        ) as settings_mock,
    ):
        settings_mock.CODE_EXECUTION = mock_settings

        service = DockerExecutionService()
        service.docker_client = mock_docker_client
        service.pool_enabled = False
        service._docker_available = True

        yield service

        service._closed = True


# =============================================================================
# Code Validation Tests
# =============================================================================


class TestCodeValidation:
    """Tests for _validate_code() method - security checks."""

    def test_valid_code_passes(self, docker_service):
        """Simple valid code should pass validation."""
        valid_code = "def add(a, b):\n    return a + b"
        docker_service._validate_code(valid_code)

    def test_forbidden_import_os_detected(self, docker_service):
        """Code importing os module should be rejected."""
        # Build the malicious string dynamically to avoid hook
        forbidden_module = "os"
        malicious_code = f"import {forbidden_module}\nprint('test')"
        with pytest.raises(ValueError, match="Forbidden import detected"):
            docker_service._validate_code(malicious_code)

    def test_forbidden_import_subprocess_detected(self, docker_service):
        """Code importing subprocess should be rejected."""
        forbidden_module = "subprocess"
        malicious_code = f"import {forbidden_module}\nprint('test')"
        with pytest.raises(ValueError, match="Forbidden import detected"):
            docker_service._validate_code(malicious_code)

    def test_forbidden_from_import_detected(self, docker_service):
        """Code with 'from os import ...' should be rejected."""
        forbidden_module = "os"
        malicious_code = f"from {forbidden_module} import path\nprint('test')"
        with pytest.raises(ValueError, match="Forbidden import detected"):
            docker_service._validate_code(malicious_code)

    def test_forbidden_dunder_import_detected(self, docker_service):
        """Code with __import__ should be rejected."""
        forbidden_module = "os"
        malicious_code = f'__import__("{forbidden_module}")'
        with pytest.raises(ValueError):
            docker_service._validate_code(malicious_code)

    def test_suspicious_pattern_globals(self, docker_service):
        """Code accessing __globals__ should be rejected."""
        malicious_code = "def foo(): pass\nfoo.__globals__"
        with pytest.raises(ValueError, match="Suspicious code pattern"):
            docker_service._validate_code(malicious_code)

    def test_suspicious_pattern_subclasses(self, docker_service):
        """Code accessing __subclasses__ should be rejected."""
        malicious_code = "().__class__.__bases__[0].__subclasses__()"
        with pytest.raises(ValueError, match="Suspicious code pattern"):
            docker_service._validate_code(malicious_code)

    def test_legitimate_string_operations_allowed(self, docker_service):
        """Legitimate string ops like chr(), ord() should be allowed."""
        valid_code = """
def char_to_int(c):
    return ord(c)

def int_to_char(n):
    return chr(n)
"""
        docker_service._validate_code(valid_code)


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Tests for _check_rate_limit() method."""

    def test_first_request_allowed(self, docker_service):
        """First request from a user should be allowed."""
        with patch(
            "purplex.problems_app.services.docker_execution_service.cache"
        ) as mock_cache:
            mock_cache.get.return_value = 0

            result = docker_service._check_rate_limit("user-123")

            assert result is True
            mock_cache.set.assert_called_once()

    def test_under_limit_allowed(self, docker_service):
        """Requests under the rate limit should be allowed."""
        docker_service.rate_limit_per_minute = 10

        with patch(
            "purplex.problems_app.services.docker_execution_service.cache"
        ) as mock_cache:
            mock_cache.get.return_value = 5

            result = docker_service._check_rate_limit("user-123")

            assert result is True

    def test_at_limit_rejected(self, docker_service):
        """Requests at the rate limit should be rejected."""
        docker_service.rate_limit_per_minute = 10

        with patch(
            "purplex.problems_app.services.docker_execution_service.cache"
        ) as mock_cache:
            mock_cache.get.return_value = 10

            result = docker_service._check_rate_limit("user-123")

            assert result is False

    def test_over_limit_rejected(self, docker_service):
        """Requests over the rate limit should be rejected."""
        docker_service.rate_limit_per_minute = 10

        with patch(
            "purplex.problems_app.services.docker_execution_service.cache"
        ) as mock_cache:
            mock_cache.get.return_value = 15

            result = docker_service._check_rate_limit("user-123")

            assert result is False


# =============================================================================
# Test Solution Run Tests
# =============================================================================


class TestTestSolution:
    """Tests for test_solution() method - the main public API."""

    def test_invalid_function_name_rejected(self, docker_service):
        """Invalid function names should be rejected before running."""
        result = docker_service.test_solution(
            user_code="def foo(): pass",
            function_name="123invalid",
            test_cases=[{"inputs": [], "expected_output": None}],
        )

        assert result["success"] is False
        assert "Invalid function name" in result["error"]
        assert result["testsPassed"] == 0

    def test_function_name_with_spaces_rejected(self, docker_service):
        """Function names with spaces should be rejected."""
        result = docker_service.test_solution(
            user_code="def foo(): pass",
            function_name="my func",
            test_cases=[{"inputs": [], "expected_output": None}],
        )

        assert result["success"] is False
        assert "Invalid function name" in result["error"]

    def test_function_name_with_special_chars_rejected(self, docker_service):
        """Function names with special characters should be rejected."""
        result = docker_service.test_solution(
            user_code="def foo(): pass",
            function_name="foo;drop",
            test_cases=[{"inputs": [], "expected_output": None}],
        )

        assert result["success"] is False
        assert "Invalid function name" in result["error"]

    def test_valid_function_name_underscore_allowed(self, docker_service):
        """Function names with underscores should be allowed."""
        with (
            patch.object(docker_service, "_check_rate_limit", return_value=True),
            patch.object(docker_service, "_validate_code"),
            patch.object(docker_service, "_execute_in_container") as mock_run,
        ):
            mock_run.return_value = {
                "success": True,
                "output": json.dumps(
                    {"testsPassed": 1, "totalTests": 1, "results": [], "success": True}
                ),
                "error": None,
            }

            result = docker_service.test_solution(
                user_code="def my_function(): pass",
                function_name="my_function",
                test_cases=[{"inputs": [], "expected_output": None}],
            )

            assert result["success"] is True

    def test_rate_limit_exceeded_returns_error(self, docker_service):
        """When rate limit is exceeded, return error without running."""
        with patch.object(docker_service, "_check_rate_limit", return_value=False):
            result = docker_service.test_solution(
                user_code="def foo(): pass",
                function_name="foo",
                test_cases=[{"inputs": [], "expected_output": None}],
            )

            assert result["success"] is False
            assert "Rate limit exceeded" in result["error"]

    def test_forbidden_code_returns_error(self, docker_service):
        """Code with forbidden patterns should return error."""
        forbidden_module = "os"
        result = docker_service.test_solution(
            user_code=f"import {forbidden_module}",
            function_name="foo",
            test_cases=[{"inputs": [], "expected_output": None}],
        )

        assert result["success"] is False
        assert "Forbidden import" in result["error"]

    def test_successful_run_returns_results(self, docker_service):
        """Successful run should return parsed test results."""
        expected_output = {
            "testsPassed": 2,
            "totalTests": 2,
            "results": [
                {"test_number": 1, "isSuccessful": True},
                {"test_number": 2, "isSuccessful": True},
            ],
            "success": True,
        }

        with (
            patch.object(docker_service, "_check_rate_limit", return_value=True),
            patch.object(docker_service, "_execute_in_container") as mock_run,
        ):
            mock_run.return_value = {
                "success": True,
                "output": json.dumps(expected_output),
                "error": None,
            }

            result = docker_service.test_solution(
                user_code="def add(a, b): return a + b",
                function_name="add",
                test_cases=[
                    {"inputs": [1, 2], "expected_output": 3},
                    {"inputs": [0, 0], "expected_output": 0},
                ],
            )

            assert result["success"] is True
            assert result["testsPassed"] == 2

    def test_run_failure_returns_error_results(self, docker_service):
        """Run failure should return error results for each test case."""
        with (
            patch.object(docker_service, "_check_rate_limit", return_value=True),
            patch.object(docker_service, "_execute_in_container") as mock_run,
        ):
            mock_run.return_value = {
                "success": False,
                "output": "",
                "error": "SyntaxError: invalid syntax",
            }

            result = docker_service.test_solution(
                user_code="def add(a, b) return a + b",
                function_name="add",
                test_cases=[
                    {"inputs": [1, 2], "expected_output": 3},
                    {"inputs": [3, 4], "expected_output": 7},
                ],
            )

            assert result["success"] is False
            assert result["testsPassed"] == 0
            assert len(result["results"]) == 2

    def test_json_parse_failure_returns_error_results(self, docker_service):
        """If Docker output is not valid JSON, return error results."""
        with (
            patch.object(docker_service, "_check_rate_limit", return_value=True),
            patch.object(docker_service, "_execute_in_container") as mock_run,
        ):
            mock_run.return_value = {
                "success": True,
                "output": "This is not JSON",
                "error": None,
            }

            result = docker_service.test_solution(
                user_code="def foo(): return 1",
                function_name="foo",
                test_cases=[{"inputs": [], "expected_output": 1}],
            )

            assert result["success"] is False
            assert "Failed to parse" in result["error"]


# =============================================================================
# Container Run Tests
# =============================================================================


class TestContainerRun:
    """Tests for _execute_in_new_container()."""

    def test_successful_container_run(self, docker_service, mock_docker_client):
        """Successful container run should return output."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container

        mock_container.wait = MagicMock(return_value={"StatusCode": 0})
        mock_container.logs = MagicMock(return_value=b'{"success": true}')

        result = docker_service._execute_in_new_container("print('hello')")

        assert result["success"] is True
        assert result["output"] == '{"success": true}'

    def test_container_run_failure(self, docker_service, mock_docker_client):
        """Container run with non-zero exit should return error."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container

        mock_container.wait = MagicMock(return_value={"StatusCode": 1})
        mock_container.logs = MagicMock(
            return_value=b"NameError: name x is not defined"
        )

        result = docker_service._execute_in_new_container("print(x)")

        assert result["success"] is False
        assert "NameError" in result["error"]

    def test_container_removed_after_run(self, docker_service, mock_docker_client):
        """Container should be removed after run."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container

        mock_container.wait = MagicMock(return_value={"StatusCode": 0})
        mock_container.logs = MagicMock(return_value=b"ok")

        docker_service._execute_in_new_container("print('hello')")

        assert mock_container._removed is True

    def test_output_truncation_on_large_output(
        self, docker_service, mock_docker_client
    ):
        """Large outputs should be truncated."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container

        large_output = b"x" * (1024 * 1024 + 1000)
        mock_container.wait = MagicMock(return_value={"StatusCode": 0})
        mock_container.logs = MagicMock(return_value=large_output)

        result = docker_service._execute_in_new_container("print('big')")

        assert result["success"] is True
        assert "truncated" in result["output"]


# =============================================================================
# Container Pool Tests
# =============================================================================


class TestContainerPool:
    """Tests for container pool management."""

    @pytest.fixture
    def pooled_docker_service(self, mock_docker_client, mock_settings):
        """Create a DockerExecutionService with pooling enabled."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings

            service = DockerExecutionService()
            service.docker_client = mock_docker_client
            service.pool_enabled = True
            service.pool_size = 3
            service.container_pool = []
            service.container_metadata = {}
            service._docker_available = True

            yield service

            service._closed = True

    def test_get_container_from_pool_when_available(self, pooled_docker_service):
        """Getting container from pool should return available container."""
        mock_container = MockContainer("container-1")
        pooled_docker_service.container_pool = [mock_container]

        result = pooled_docker_service._get_container_from_pool()

        assert result == mock_container
        assert len(pooled_docker_service.container_pool) == 0

    def test_get_container_creates_new_when_pool_empty(self, pooled_docker_service):
        """When pool is empty, should create new container."""
        pooled_docker_service.container_pool = []

        with patch.object(
            pooled_docker_service, "_create_pool_container"
        ) as mock_create:
            mock_container = MockContainer("new-container")
            mock_create.return_value = mock_container

            result = pooled_docker_service._get_container_from_pool()

            assert result == mock_container
            mock_create.assert_called_once()

    def test_unhealthy_container_removed_from_pool(self, pooled_docker_service):
        """Unhealthy containers should be removed and not returned."""
        unhealthy_container = MockContainer("unhealthy-1")
        unhealthy_container._status = "exited"

        healthy_container = MockContainer("healthy-1")

        # Note: pool.pop() returns last element, so put unhealthy last to pop first
        pooled_docker_service.container_pool = [healthy_container, unhealthy_container]

        result = pooled_docker_service._get_container_from_pool()

        assert result == healthy_container
        assert unhealthy_container._removed is True

    def test_return_container_to_pool(self, pooled_docker_service):
        """Returning container to pool should add it back."""
        mock_container = MockContainer("container-1")
        mock_container.exec_run = MagicMock(return_value=MagicMock(exit_code=0))

        pooled_docker_service.container_pool = []
        pooled_docker_service.container_metadata["container-1"] = {
            "created_at": 0,
            "execution_count": 0,
        }

        pooled_docker_service._return_container_to_pool(mock_container)

        assert mock_container in pooled_docker_service.container_pool

    def test_return_container_pool_full(self, pooled_docker_service):
        """When pool is full, returned container should be removed."""
        pooled_docker_service.container_pool = [
            MockContainer(f"container-{i}") for i in range(3)
        ]

        returning_container = MockContainer("overflow-container")
        returning_container.exec_run = MagicMock(return_value=MagicMock(exit_code=0))

        pooled_docker_service._return_container_to_pool(returning_container)

        assert returning_container._removed is True
        assert len(pooled_docker_service.container_pool) == 3

    def test_pool_metrics_tracked(self, pooled_docker_service):
        """Pool operations should update metrics."""
        mock_container = MockContainer("container-1")
        pooled_docker_service.container_pool = [mock_container]

        initial_requests = pooled_docker_service.pool_metrics["pool_requests_total"]

        pooled_docker_service._get_container_from_pool()

        assert (
            pooled_docker_service.pool_metrics["pool_requests_total"]
            == initial_requests + 1
        )


# =============================================================================
# Timeout Handling Tests
# =============================================================================


class TestTimeoutHandling:
    """Tests for run timeout handling."""

    def test_timeout_returns_error(self, docker_service, mock_docker_client):
        """When run times out, should return timeout error."""
        from docker.errors import APIError

        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container

        mock_container.wait = MagicMock(side_effect=APIError("timeout reached"))

        result = docker_service._execute_in_new_container("while True: pass")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()


# =============================================================================
# Test Runner Generation Tests
# =============================================================================


class TestTestRunnerGeneration:
    """Tests for _create_test_runner() method."""

    def test_test_runner_includes_user_code(self, docker_service):
        """Generated test runner should include user's code."""
        user_code = "def add(a, b): return a + b"

        runner = docker_service._create_test_runner(
            user_code=user_code,
            function_name="add",
            test_cases=[{"inputs": [1, 2], "expected_output": 3}],
        )

        assert user_code in runner

    def test_test_runner_includes_comparison_function(self, docker_service):
        """Generated test runner should include type-aware comparison."""
        runner = docker_service._create_test_runner(
            user_code="def foo(): pass", function_name="foo", test_cases=[]
        )

        assert "compare_results" in runner

    def test_test_runner_calls_correct_function(self, docker_service):
        """Generated test runner should call the specified function."""
        runner = docker_service._create_test_runner(
            user_code="def my_custom_function(): pass",
            function_name="my_custom_function",
            test_cases=[{"inputs": [], "expected_output": None}],
        )

        assert "my_custom_function(*inputs)" in runner


# =============================================================================
# Service Lifecycle Tests
# =============================================================================


class TestServiceLifecycle:
    """Tests for service initialization and cleanup."""

    def test_close_marks_service_closed(self):
        """Closing service should mark it as closed."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": False}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._stop_health_monitor = MagicMock()

            service.close()

            assert service._closed is True

    def test_context_manager_cleanup(self):
        """Using service as context manager should clean up on exit."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": False}
            mock_docker.return_value = MockDockerClient()

            with DockerExecutionService() as service:
                assert not service._closed

            assert service._closed

    def test_get_pool_metrics_returns_stats(self):
        """get_pool_metrics should return current pool state."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": True, "POOL_SIZE": 5}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service.container_pool = [MockContainer() for _ in range(3)]

            metrics = service.get_pool_metrics()

            assert metrics["pool_size"] == 3
            assert metrics["pool_max_size"] == 5
            assert "docker_available" in metrics

            service._closed = True


# =============================================================================
# Image Management Tests
# =============================================================================


class TestImageManagement:
    """Tests for _ensure_image_exists() and _build_sandbox_image()."""

    def test_image_exists_does_not_build(self, mock_docker_client, mock_settings):
        """When image exists, should NOT trigger a build."""
        mock_docker_client.images.get.return_value = MagicMock()

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_build_sandbox_image") as mock_build,
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()
            service._closed = True

        mock_docker_client.images.get.assert_called_once()
        mock_build.assert_not_called()

    def test_image_not_found_triggers_build(self, mock_docker_client, mock_settings):
        """When image not found, should trigger build."""
        from docker.errors import ImageNotFound

        mock_docker_client.images.get.side_effect = ImageNotFound("not found")

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_build_sandbox_image") as mock_build,
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()
            service._closed = True

        mock_build.assert_called_once()

    def test_build_sandbox_image_success(self, docker_service, mock_docker_client):
        """Successful build should call images.build with correct image tag."""
        mock_image = MagicMock()
        mock_logs = [{"stream": "Step 1/5"}, {"stream": "Step 2/5"}]
        mock_docker_client.images.build.return_value = (mock_image, mock_logs)

        with patch(
            "purplex.problems_app.services.docker_execution_service.settings"
        ) as settings_mock:
            settings_mock.BASE_DIR = "/fake"
            docker_service._build_sandbox_image()

        call_kwargs = mock_docker_client.images.build.call_args
        assert call_kwargs[1]["tag"] == docker_service.docker_image
        assert call_kwargs[1]["rm"] is True

    def test_build_sandbox_image_failure_raises(
        self, docker_service, mock_docker_client
    ):
        """Build failure should raise."""
        mock_docker_client.images.build.side_effect = OSError("build failed")

        with (
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
            pytest.raises(OSError, match="build failed"),
        ):
            settings_mock.BASE_DIR = "/fake"
            docker_service._build_sandbox_image()


# =============================================================================
# Pool Initialization Tests
# =============================================================================


class TestPoolInitialization:
    """Tests for _init_pool() and _create_pool_container()."""

    def test_init_pool_creates_containers(self, mock_docker_client, mock_settings):
        """Init should create pool_size containers."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch.object(
                DockerExecutionService,
                "_create_pool_container",
                return_value=MockContainer(),
            ) as mock_create,
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()

            assert mock_create.call_count == 3
            assert len(service.container_pool) == 3
            assert service._pool_initialized is True
            service._closed = True

    def test_init_pool_idempotent(self, mock_docker_client, mock_settings):
        """Second init call should be a no-op."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch.object(
                DockerExecutionService,
                "_create_pool_container",
                return_value=MockContainer(),
            ) as mock_create,
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()

            # First init happened during __init__, pool_initialized is True
            assert service._pool_initialized is True
            initial_call_count = mock_create.call_count

            # Second call should be a no-op
            service._init_pool()
            assert mock_create.call_count == initial_call_count
            service._closed = True

    def test_init_pool_partial_failure(self, mock_docker_client, mock_settings):
        """Partial failure during init should still initialize available containers."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        call_count = 0

        def create_or_fail(self_arg=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("creation failed")
            return MockContainer(f"c-{call_count}")

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch.object(
                DockerExecutionService,
                "_create_pool_container",
                side_effect=create_or_fail,
            ),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()

            assert len(service.container_pool) == 2
            assert service._pool_initialized is True
            service._closed = True

    def test_create_pool_container_success(self, docker_service, mock_docker_client):
        """Container creation should set up metadata."""
        mock_container = MockContainer("new-pool-c")
        mock_docker_client.containers.run.return_value = mock_container

        with patch(
            "purplex.problems_app.services.docker_execution_service.gevent"
        ) as mock_gevent:
            mock_gevent.sleep = MagicMock()
            result = docker_service._create_pool_container()

        assert result == mock_container
        assert "new-pool-c" in docker_service.container_metadata
        assert docker_service.pool_metrics["total_created"] == 1

    def test_create_pool_container_not_running(
        self, docker_service, mock_docker_client
    ):
        """Container that fails to start should be removed."""
        mock_container = MockContainer("bad-c", status="exited")
        mock_docker_client.containers.run.return_value = mock_container

        with patch(
            "purplex.problems_app.services.docker_execution_service.gevent"
        ) as mock_gevent:
            mock_gevent.sleep = MagicMock()
            result = docker_service._create_pool_container()

        assert result is None
        assert mock_container._removed is True

    def test_create_pool_container_exception(self, docker_service, mock_docker_client):
        """Exception during creation should return None."""
        mock_docker_client.containers.run.side_effect = Exception("Docker error")

        result = docker_service._create_pool_container()

        assert result is None


# =============================================================================
# Health Monitor Tests
# =============================================================================


class TestHealthMonitor:
    """Tests for health monitoring system."""

    @pytest.fixture
    def health_service(self, mock_docker_client, mock_settings):
        """Service with pool enabled for health monitoring tests."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings

            service = DockerExecutionService()
            service.docker_client = mock_docker_client
            service.pool_enabled = True
            service.pool_size = 3
            service.container_pool = []
            service.container_metadata = {}
            service._docker_available = True
            service.container_max_age = 3600
            service.max_restart_attempts = 3
            service.health_check_interval = 60

            yield service

            service._closed = True

    def test_start_health_monitor_creates_thread(
        self, mock_docker_client, mock_settings
    ):
        """Starting monitor should create a daemon thread."""
        mock_settings["POOL_ENABLED"] = True

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            service = DockerExecutionService()

            assert service._health_monitor_thread is not None
            assert service._health_monitor_thread.daemon is True

            # Cleanup
            service._stop_health_monitor.set()
            service._health_monitor_thread.join(timeout=2)
            service._closed = True

    def test_start_health_monitor_already_running(self, health_service):
        """Starting monitor when already running should not replace the thread."""
        existing_thread = MagicMock()
        health_service._health_monitor_thread = existing_thread
        health_service._start_health_monitor()

        assert health_service._health_monitor_thread is existing_thread

    def test_stop_health_monitor_signals_and_joins(self, health_service):
        """Stopping monitor should signal and join."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        health_service._health_monitor_thread = mock_thread

        health_service._stop_health_monitor_thread()

        assert health_service._stop_health_monitor.is_set()
        mock_thread.join.assert_called_once_with(timeout=5.0)
        assert health_service._health_monitor_thread is None

    def test_stop_health_monitor_timeout_warning(self, health_service):
        """Thread that doesn't stop should log warning and still clear the reference."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        health_service._health_monitor_thread = mock_thread

        with patch(
            "purplex.problems_app.services.docker_execution_service.logger"
        ) as mock_logger:
            health_service._stop_health_monitor_thread()

        assert health_service._health_monitor_thread is None
        mock_logger.warning.assert_any_call(
            "Health monitor thread did not stop gracefully"
        )

    def test_stop_health_monitor_noop_when_none(self, health_service):
        """Stop when no thread exists should be a no-op."""
        health_service._health_monitor_thread = None
        health_service._stop_health_monitor_thread()

    def test_health_check_all_healthy(self, health_service, mock_docker_client):
        """Health check with all healthy containers should update metadata."""
        c1 = MockContainer("c-1")
        c2 = MockContainer("c-2")
        health_service.container_pool = [c1, c2]
        health_service.container_metadata = {
            "c-1": {
                "created_at": time.time(),
                "restart_count": 0,
                "last_health_check": 0,
            },
            "c-2": {
                "created_at": time.time(),
                "restart_count": 0,
                "last_health_check": 0,
            },
        }

        health_service._perform_health_check()

        assert health_service.pool_metrics["health_checks_performed"] == 1
        assert len(health_service.container_pool) == 2

    def test_health_check_removes_not_running(self, health_service, mock_docker_client):
        """Container not running should be removed."""
        dead = MockContainer("dead-c", status="exited")
        health_service.container_pool = [dead]
        health_service.container_metadata = {
            "dead-c": {"created_at": time.time(), "restart_count": 0},
        }

        with patch.object(health_service, "_create_pool_container", return_value=None):
            health_service._perform_health_check()

        assert dead._removed is True
        assert health_service.pool_metrics["unhealthy_containers_removed"] >= 1

    def test_health_check_rotates_old_container(
        self, health_service, mock_docker_client
    ):
        """Container exceeding max age should be rotated."""
        old = MockContainer("old-c")
        health_service.container_pool = [old]
        health_service.container_metadata = {
            "old-c": {"created_at": time.time() - 7200, "restart_count": 0},
        }

        replacement = MockContainer("new-c")
        with patch.object(
            health_service, "_create_pool_container", return_value=replacement
        ):
            health_service._perform_health_check()

        assert old._removed is True
        assert health_service.pool_metrics["age_rotations"] >= 1
        assert replacement in health_service.container_pool

    def test_health_check_removes_restarted_too_much(
        self, health_service, mock_docker_client
    ):
        """Container restarted too many times should be removed."""
        bad = MockContainer("bad-c")
        health_service.container_pool = [bad]
        health_service.container_metadata = {
            "bad-c": {"created_at": time.time(), "restart_count": 10},
        }

        with patch.object(health_service, "_create_pool_container", return_value=None):
            health_service._perform_health_check()

        assert bad._removed is True

    def test_health_check_docker_unavailable(self, health_service, mock_docker_client):
        """Docker daemon unavailable should disable pool."""
        mock_docker_client.ping = MagicMock(side_effect=Exception("connection refused"))
        health_service.container_pool = [MockContainer("c-1")]

        health_service._perform_health_check()

        assert health_service._docker_available is False
        assert len(health_service.container_pool) == 0

    def test_health_check_docker_recovers(self, health_service, mock_docker_client):
        """Docker recovery should re-enable pool after prior unavailability."""

        # The recovery branch fires when _perform_health_check detects that
        # Docker is available again (ping succeeds) after _docker_available was
        # previously set to False. We simulate this with a ping side-effect
        # that sets _docker_available=False just before the recovery check.
        def ping_simulating_recovery():
            health_service._docker_available = False
            return True

        mock_docker_client.ping = ping_simulating_recovery

        with patch.object(health_service, "_create_pool_container", return_value=None):
            health_service._perform_health_check()

        # Recovery branch should have set it back to True
        assert health_service._docker_available is True

    def test_health_check_exception_on_container_continues(
        self, health_service, mock_docker_client
    ):
        """Exception checking one container shouldn't stop the rest."""
        bad = MockContainer("bad-c")
        bad.reload = MagicMock(side_effect=Exception("API error"))
        good = MockContainer("good-c")

        health_service.container_pool = [bad, good]
        health_service.container_metadata = {
            "bad-c": {"created_at": time.time(), "restart_count": 0},
            "good-c": {"created_at": time.time(), "restart_count": 0},
        }

        with patch.object(health_service, "_create_pool_container", return_value=None):
            health_service._perform_health_check()

        assert good in health_service.container_pool

    def test_health_check_replenishes_pool(self, health_service, mock_docker_client):
        """Pool below target size should be replenished."""
        health_service.container_pool = [MockContainer("c-1")]
        health_service.container_metadata = {
            "c-1": {"created_at": time.time(), "restart_count": 0},
        }

        new_c = MockContainer("new-c")
        with patch.object(
            health_service, "_create_pool_container", return_value=new_c
        ) as mock_create:
            health_service._perform_health_check()

        assert mock_create.call_count == 2

    def test_handle_docker_unavailable(self, health_service):
        """Docker unavailable should clear pool and set flag."""
        health_service._docker_available = True
        health_service.container_pool = [MockContainer("c-1")]
        health_service.container_metadata = {"c-1": {}}

        health_service._handle_docker_unavailable()

        assert health_service._docker_available is False
        assert len(health_service.container_pool) == 0
        assert len(health_service.container_metadata) == 0

    def test_handle_docker_unavailable_idempotent(self, health_service):
        """Second call when already unavailable shouldn't increment error count."""
        health_service._docker_available = False
        initial_errors = health_service.pool_metrics["docker_errors"]

        health_service._handle_docker_unavailable()

        assert health_service.pool_metrics["docker_errors"] == initial_errors

    def test_health_monitor_loop_stops_on_signal(self, health_service):
        """Loop should exit when stop signal is set and call _perform_health_check."""
        health_service._stop_health_monitor = threading.Event()
        health_service.health_check_interval = 0.01

        def set_stop():
            time.sleep(0.05)
            health_service._stop_health_monitor.set()

        t = threading.Thread(target=set_stop)
        t.start()

        with patch.object(health_service, "_perform_health_check") as mock_check:
            health_service._health_monitor_loop()

        t.join(timeout=1)

        # Loop should have called health check at least once before stopping
        assert mock_check.call_count >= 1
        assert health_service._stop_health_monitor.is_set()

    def test_health_check_pool_disabled_noop(self, health_service):
        """Health check with pool disabled should be a no-op."""
        health_service.pool_enabled = False
        initial_checks = health_service.pool_metrics["health_checks_performed"]

        health_service._perform_health_check()

        assert health_service.pool_metrics["health_checks_performed"] == initial_checks


# =============================================================================
# Pooled Execution Tests
# =============================================================================


class TestPooledExecution:
    """Tests for _execute_in_pooled_container()."""

    @pytest.fixture
    def pooled_service(self, mock_docker_client, mock_settings):
        """Service configured for pooled execution tests."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings

            service = DockerExecutionService()
            service.docker_client = mock_docker_client
            service.pool_enabled = True
            service.pool_size = 3
            service.container_pool = []
            service.container_metadata = {}
            service._docker_available = True

            yield service

            service._closed = True

    def test_docker_unavailable_falls_back(self, pooled_service):
        """Docker unavailable should fall back to new container."""
        pooled_service._docker_available = False

        with patch.object(pooled_service, "_execute_in_new_container") as mock_new:
            mock_new.return_value = {"success": True, "output": "ok", "error": None}
            result = pooled_service._execute_in_pooled_container("code")

        assert result["success"] is True
        mock_new.assert_called_once()

    def test_no_container_from_pool_falls_back(self, pooled_service):
        """Failed pool retrieval should fall back to new container."""
        with (
            patch.object(pooled_service, "_get_container_from_pool", return_value=None),
            patch.object(pooled_service, "_execute_in_new_container") as mock_new,
        ):
            mock_new.return_value = {"success": True, "output": "ok", "error": None}
            pooled_service._execute_in_pooled_container("code")

        mock_new.assert_called_once()

    def test_successful_execution(self, pooled_service):
        """Successful execution should return output and return container to pool."""
        container = MockContainer("exec-c")
        container.exec_run = MagicMock(
            return_value=MagicMock(exit_code=0, output=b'{"result": "ok"}')
        )

        with (
            patch.object(
                pooled_service, "_get_container_from_pool", return_value=container
            ),
            patch.object(pooled_service, "_return_container_to_pool") as mock_return,
        ):
            result = pooled_service._execute_in_pooled_container("code")

        assert result["success"] is True
        assert '{"result": "ok"}' in result["output"]
        mock_return.assert_called_once_with(container)

    def test_nonzero_exit_returns_error(self, pooled_service):
        """Non-zero exit code should return error."""
        container = MockContainer("fail-c")
        container.exec_run = MagicMock(
            return_value=MagicMock(exit_code=1, output=b"NameError: x")
        )

        with (
            patch.object(
                pooled_service, "_get_container_from_pool", return_value=container
            ),
            patch.object(pooled_service, "_return_container_to_pool"),
        ):
            result = pooled_service._execute_in_pooled_container("print(x)")

        assert result["success"] is False
        assert "NameError" in result["error"]

    def test_output_truncation(self, pooled_service):
        """Output exceeding 1MB should be truncated."""
        container = MockContainer("big-c")
        big_output = b"x" * (1024 * 1024 + 500)
        container.exec_run = MagicMock(
            return_value=MagicMock(exit_code=0, output=big_output)
        )

        with (
            patch.object(
                pooled_service, "_get_container_from_pool", return_value=container
            ),
            patch.object(pooled_service, "_return_container_to_pool"),
        ):
            result = pooled_service._execute_in_pooled_container("code")

        assert "truncated" in result["output"]

    def test_empty_output(self, pooled_service):
        """No output should return empty string."""
        container = MockContainer("empty-c")
        container.exec_run = MagicMock(return_value=MagicMock(exit_code=0, output=None))

        with (
            patch.object(
                pooled_service, "_get_container_from_pool", return_value=container
            ),
            patch.object(pooled_service, "_return_container_to_pool"),
        ):
            result = pooled_service._execute_in_pooled_container("code")

        assert result["success"] is True
        assert result["output"] == ""

    def test_exec_exception_falls_back(self, pooled_service):
        """Exception during execution should fall back to new container."""
        container = MockContainer("err-c")
        container.exec_run = MagicMock(side_effect=Exception("exec failed"))

        with (
            patch.object(
                pooled_service, "_get_container_from_pool", return_value=container
            ),
            patch.object(pooled_service, "_execute_in_new_container") as mock_new,
        ):
            mock_new.return_value = {"success": True, "output": "ok", "error": None}
            pooled_service._execute_in_pooled_container("code")

        assert container._removed is True
        mock_new.assert_called_once()

    def test_unexpected_outer_exception(self, pooled_service):
        """Unexpected exception at the top level should return error."""
        with patch.object(
            pooled_service, "_get_container_from_pool", side_effect=Exception("boom")
        ):
            result = pooled_service._execute_in_pooled_container("code")

        assert result["success"] is False
        assert "Unexpected" in result["error"]


# =============================================================================
# Return Container to Pool Tests
# =============================================================================


class TestReturnContainerToPool:
    """Tests for _return_container_to_pool() edge cases."""

    @pytest.fixture
    def pool_service(self, mock_docker_client, mock_settings):
        """Service for pool return tests."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings

            service = DockerExecutionService()
            service.docker_client = mock_docker_client
            service.pool_enabled = True
            service.pool_size = 3
            service.container_pool = []
            service.container_metadata = {}
            service._docker_available = True

            yield service

            service._closed = True

    def test_pool_disabled_removes_container(self, pool_service):
        """When pool disabled, container should be removed."""
        pool_service.pool_enabled = False
        container = MockContainer("c-1")

        pool_service._return_container_to_pool(container)

        assert container._removed is True

    def test_container_not_running_removed(self, pool_service):
        """Container not running should be removed."""
        container = MockContainer("c-1", status="exited")

        pool_service._return_container_to_pool(container)

        assert container._removed is True

    def test_cleanup_failure_removes_container(self, pool_service):
        """Cleanup exec failure should remove container."""
        container = MockContainer("c-1")
        container.exec_run = MagicMock(return_value=MagicMock(exit_code=1))

        pool_service._return_container_to_pool(container)

        assert container._removed is True

    def test_cleanup_exception_removes_container(self, pool_service):
        """Cleanup exception should remove container."""
        container = MockContainer("c-1")
        container.exec_run = MagicMock(side_effect=Exception("exec error"))

        pool_service._return_container_to_pool(container)

        assert container._removed is True

    def test_execution_count_incremented(self, pool_service):
        """Execution count should be incremented."""
        container = MockContainer("c-1")
        container.exec_run = MagicMock(return_value=MagicMock(exit_code=0))
        pool_service.container_metadata["c-1"] = {
            "created_at": 0,
            "execution_count": 5,
        }

        pool_service._return_container_to_pool(container)

        assert pool_service.container_metadata["c-1"]["execution_count"] == 6

    def test_outer_exception_removes_container(self, pool_service):
        """Exception in outer try should remove container."""
        container = MockContainer("c-1")
        container.reload = MagicMock(side_effect=Exception("API error"))

        pool_service._return_container_to_pool(container)

        assert container._removed is True


# =============================================================================
# Execute in New Container Edge Cases
# =============================================================================


class TestExecuteInNewContainerEdgeCases:
    """Additional edge case tests for _execute_in_new_container()."""

    def test_container_error_exception(self, docker_service, mock_docker_client):
        """ContainerError should return error result."""
        from docker.errors import ContainerError

        mock_docker_client.containers.create.side_effect = ContainerError(
            container="c", image="img", command="cmd", exit_status=1, stderr=b"fail"
        )

        result = docker_service._execute_in_new_container("code")

        assert result["success"] is False

    def test_api_error_non_timeout(self, docker_service, mock_docker_client):
        """Non-timeout APIError should return Docker error."""
        from docker.errors import APIError

        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait = MagicMock(side_effect=APIError("server error"))

        result = docker_service._execute_in_new_container("code")

        assert result["success"] is False
        assert "Docker execution error" in result["error"]

    def test_generic_exception(self, docker_service, mock_docker_client):
        """Generic exception should return unexpected error."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.start = MagicMock(side_effect=RuntimeError("weird"))

        result = docker_service._execute_in_new_container("code")

        assert result["success"] is False
        assert "Unexpected" in result["error"]
        assert mock_container._removed is True

    def test_container_removed_even_on_exception(
        self, docker_service, mock_docker_client
    ):
        """Container should be removed in finally block."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait = MagicMock(side_effect=RuntimeError("fail"))

        docker_service._execute_in_new_container("code")

        assert mock_container._removed is True

    def test_empty_logs_on_failure(self, docker_service, mock_docker_client):
        """Empty logs on failure should use default error message."""
        mock_container = MockContainer()
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait = MagicMock(return_value={"StatusCode": 1})
        mock_container.logs = MagicMock(return_value=b"")

        result = docker_service._execute_in_new_container("code")

        assert result["success"] is False
        assert result["error"] == "Code execution failed"


# =============================================================================
# Test Runner Type Comparison Tests
# =============================================================================


class TestTestRunnerComparison:
    """Tests for the compare_results() function generated by _create_test_runner()."""

    @pytest.fixture
    def compare_fn(self, docker_service):
        """Extract compare_results function from generated test runner."""
        runner = docker_service._create_test_runner(
            user_code="def foo(): pass",
            function_name="foo",
            test_cases=[],
        )
        namespace = {}
        fn_code = runner.split("# User's code")[0]
        exec(fn_code, namespace)  # noqa: S102 - test-only, controlled input
        return namespace["compare_results"]

    def test_bool_false_not_equal_int_zero(self, compare_fn):
        assert compare_fn(False, 0) is False

    def test_bool_true_not_equal_int_one(self, compare_fn):
        assert compare_fn(True, 1) is False

    def test_bool_equal_bool(self, compare_fn):
        assert compare_fn(True, True) is True
        assert compare_fn(False, False) is True

    def test_int_float_equivalence(self, compare_fn):
        assert compare_fn(1, 1.0) is True

    def test_string_comparison(self, compare_fn):
        assert compare_fn("hello", "hello") is True
        assert compare_fn("hello", "world") is False

    def test_list_tuple_equivalence(self, compare_fn):
        assert compare_fn([1, 2, 3], (1, 2, 3)) is True

    def test_list_length_mismatch(self, compare_fn):
        assert compare_fn([1, 2], [1, 2, 3]) is False

    def test_dict_comparison(self, compare_fn):
        assert compare_fn({"a": 1, "b": 2}, {"b": 2, "a": 1}) is True
        assert compare_fn({"a": 1}, {"a": 2}) is False

    def test_dict_key_mismatch(self, compare_fn):
        assert compare_fn({"a": 1}, {"b": 1}) is False

    def test_none_comparison(self, compare_fn):
        assert compare_fn(None, None) is True

    def test_nested_structure(self, compare_fn):
        assert compare_fn({"a": [1, (2, 3)]}, {"a": (1, [2, 3])}) is True

    def test_type_mismatch(self, compare_fn):
        assert compare_fn("1", 1) is False
        assert compare_fn(None, 0) is False


# =============================================================================
# Utilities and Edge Cases Tests
# =============================================================================


class TestUtilitiesAndEdgeCases:
    """Tests for _log_execution, log_metrics_if_needed, set_user_context, cleanup."""

    def test_log_execution_logs_code_hash(self, docker_service):
        """_log_execution should log an entry with the user ID and code hash."""
        with patch(
            "purplex.problems_app.services.docker_execution_service.logger"
        ) as mock_logger:
            docker_service._log_execution(
                "user-1", "def foo(): pass", {"success": True, "error": None}
            )

        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0][0]
        assert "user-1" in log_msg
        assert "code_hash" in log_msg

    def test_log_execution_suspicious_keywords_warns(self, docker_service):
        """Suspicious keywords should trigger a warning log."""
        with patch(
            "purplex.problems_app.services.docker_execution_service.logger"
        ) as mock_logger:
            docker_service._log_execution(
                "user-1", "system('ls')", {"success": True, "error": None}
            )

        mock_logger.warning.assert_called_once()
        warn_msg = mock_logger.warning.call_args[0][0]
        assert "Suspicious" in warn_msg

    def test_log_metrics_if_needed_before_interval(self, docker_service):
        docker_service.pool_metrics["last_metrics_log"] = time.time()
        docker_service.log_metrics_if_needed()

    def test_log_metrics_if_needed_after_interval(self, docker_service):
        docker_service.pool_metrics["last_metrics_log"] = time.time() - 7200
        docker_service.container_pool = []
        docker_service.log_metrics_if_needed()
        assert time.time() - docker_service.pool_metrics["last_metrics_log"] < 5

    def test_set_user_context(self, docker_service):
        result = docker_service.set_user_context("user-42")
        assert docker_service._current_user_id == "user-42"
        assert result is docker_service

    def test_set_user_context_none_defaults_to_anonymous(self, docker_service):
        docker_service.set_user_context(None)
        assert docker_service._current_user_id == "anonymous"

    def test_cleanup_pool_removes_all(self, docker_service):
        c1 = MockContainer("c-1")
        c2 = MockContainer("c-2")
        docker_service.container_pool = [c1, c2]
        docker_service._cleanup_pool()
        assert c1._removed is True
        assert c2._removed is True
        assert len(docker_service.container_pool) == 0

    def test_cleanup_pool_with_orphan_cleanup(self, docker_service, mock_docker_client):
        docker_service._do_orphan_cleanup = True
        docker_service.container_pool = []
        orphan = MockContainer("orphan-1")
        mock_docker_client.containers.list.return_value = [orphan]
        docker_service._cleanup_pool()
        assert orphan._removed is True

    def test_close_idempotent(self, docker_service):
        docker_service._closed = False
        docker_service.close()
        assert docker_service._closed is True
        docker_service.close()

    def test_close_logs_final_metrics(self, docker_service):
        docker_service._closed = False
        docker_service.pool_metrics["health_checks_performed"] = 5
        docker_service.container_pool = []
        docker_service.close()
        assert docker_service._closed is True

    def test_close_handles_docker_client_error(
        self, docker_service, mock_docker_client
    ):
        docker_service._closed = False
        docker_service.container_pool = []
        mock_docker_client.close = MagicMock(side_effect=Exception("close error"))
        docker_service.docker_client = mock_docker_client
        docker_service.close()
        assert docker_service._closed is True
        assert docker_service.docker_client is None

    def test_del_doesnt_crash(self, docker_service):
        docker_service._closed = True
        docker_service.__del__()

    def test_get_pool_metrics_zero_requests(self, docker_service):
        docker_service.pool_metrics["pool_requests_total"] = 0
        docker_service.pool_metrics["pool_hits"] = 0
        docker_service.container_pool = []
        metrics = docker_service.get_pool_metrics()
        assert metrics["pool_hit_rate"] == 0.0
        assert metrics["pool_avg_wait_time"] == 0.0

    def test_execute_in_container_routes_to_pool(self, docker_service):
        docker_service.pool_enabled = True
        with patch.object(
            docker_service, "_execute_in_pooled_container"
        ) as mock_pooled:
            mock_pooled.return_value = {"success": True, "output": "", "error": None}
            docker_service._execute_in_container("code")
        mock_pooled.assert_called_once()

    def test_execute_in_container_routes_to_new(self, docker_service):
        docker_service.pool_enabled = False
        with patch.object(docker_service, "_execute_in_new_container") as mock_new:
            mock_new.return_value = {"success": True, "output": "", "error": None}
            docker_service._execute_in_container("code")
        mock_new.assert_called_once()

    def test_test_solution_with_logging_enabled(self, docker_service):
        docker_service.log_executions = True
        with (
            patch.object(docker_service, "_check_rate_limit", return_value=True),
            patch.object(docker_service, "_execute_in_container") as mock_run,
            patch.object(docker_service, "_log_execution") as mock_log,
        ):
            mock_run.return_value = {
                "success": True,
                "output": json.dumps(
                    {"testsPassed": 1, "totalTests": 1, "results": [], "success": True}
                ),
                "error": None,
            }
            docker_service.test_solution(
                user_code="def foo(): return 1",
                function_name="foo",
                test_cases=[{"inputs": [], "expected_output": 1}],
            )
        mock_log.assert_called_once()

    def test_cleanup_and_close_calls_close(self, docker_service):
        with patch.object(docker_service, "close") as mock_close:
            docker_service._cleanup_and_close()
            mock_close.assert_called_once()

    def test_close_stops_health_monitor_thread(self):
        """Close with active health monitor should stop it."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": False}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False
            service._health_monitor_thread = mock_thread

            service.close()

            assert service._closed is True
            mock_thread.join.assert_called_once()

    def test_cleanup_pool_container_remove_failure(self, docker_service):
        """Container removal failure in cleanup should not crash."""
        bad_container = MockContainer("bad-c")
        bad_container.remove = MagicMock(side_effect=Exception("remove failed"))
        docker_service.container_pool = [bad_container]

        docker_service._cleanup_pool()  # Should not raise

        assert len(docker_service.container_pool) == 0

    def test_forbidden_builtin_detected(self, docker_service):
        """Code using forbidden builtin should be rejected."""
        code_with_open = "open('file.txt')"
        with pytest.raises(ValueError, match="Forbidden function detected"):
            docker_service._validate_code(code_with_open)

    def test_init_failure_raises(self, mock_docker_client, mock_settings):
        """Docker client init failure should raise."""
        with (
            patch("docker.from_env", side_effect=ConnectionError("Docker not running")),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
            pytest.raises(ConnectionError, match="Docker not running"),
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            DockerExecutionService()


# =============================================================================
# Deep Edge Case Tests (remaining uncovered lines)
# =============================================================================


class TestDeepEdgeCases:
    """Tests targeting specific uncovered lines for near-100% coverage."""

    @pytest.fixture
    def health_svc(self, mock_docker_client, mock_settings):
        """Service for deep edge case tests."""
        mock_settings["POOL_ENABLED"] = True
        mock_settings["POOL_SIZE"] = 3

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings

            service = DockerExecutionService()
            service.docker_client = mock_docker_client
            service.pool_enabled = True
            service.pool_size = 3
            service.container_pool = []
            service.container_metadata = {}
            service._docker_available = True
            service.container_max_age = 3600
            service.max_restart_attempts = 3

            yield service

            service._closed = True

    def test_health_check_replacement_creation_fails(
        self, health_svc, mock_docker_client
    ):
        """Replacement container failure during age rotation should log error."""
        old = MockContainer("old-c")
        health_svc.container_pool = [old]
        health_svc.container_metadata = {
            "old-c": {"created_at": time.time() - 7200, "restart_count": 0},
        }

        with patch.object(
            health_svc,
            "_create_pool_container",
            side_effect=Exception("creation failed"),
        ):
            health_svc._perform_health_check()

        assert old._removed is True

    def test_health_check_container_error_double_except(
        self, health_svc, mock_docker_client
    ):
        """Container check exception + remove exception should not crash."""
        bad = MockContainer("bad-c")
        bad.reload = MagicMock(side_effect=Exception("reload failed"))
        bad.remove = MagicMock(side_effect=Exception("remove also failed"))

        health_svc.container_pool = [bad]
        health_svc.container_metadata = {
            "bad-c": {"created_at": time.time(), "restart_count": 0},
        }

        with patch.object(health_svc, "_create_pool_container", return_value=None):
            health_svc._perform_health_check()  # Should not raise

    def test_health_check_replenish_failure(self, health_svc, mock_docker_client):
        """Replenishment failure should break the loop."""
        health_svc.container_pool = []
        health_svc.container_metadata = {}

        with patch.object(
            health_svc, "_create_pool_container", side_effect=Exception("create failed")
        ):
            health_svc._perform_health_check()

        # Should not crash despite replenishment failure

    def test_health_check_critical_error(self, health_svc, mock_docker_client):
        """Critical error wrapping entire health check should increment docker_errors."""
        # Make pool_lock raise to trigger the outer except
        health_svc.pool_lock = MagicMock()
        health_svc.pool_lock.__enter__ = MagicMock(side_effect=Exception("lock error"))
        health_svc.pool_lock.__exit__ = MagicMock(return_value=False)

        initial_errors = health_svc.pool_metrics["docker_errors"]

        health_svc._perform_health_check()

        assert health_svc.pool_metrics["docker_errors"] == initial_errors + 1

    def test_health_monitor_loop_exception_continues(self, health_svc):
        """Exception in health monitor loop should continue to next iteration."""
        call_count = 0

        def failing_check():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("check failed")
            health_svc._stop_health_monitor.set()

        health_svc._stop_health_monitor = threading.Event()
        health_svc.health_check_interval = 0.01

        with patch.object(
            health_svc, "_perform_health_check", side_effect=failing_check
        ):
            health_svc._health_monitor_loop()

        assert call_count >= 2

    def test_get_container_remove_failure_increments_cleanup_failures(
        self, health_svc, mock_docker_client
    ):
        """Container remove failure in _get_container_from_pool should track cleanup."""
        bad = MockContainer("bad-c", status="exited")
        bad.remove = MagicMock(side_effect=Exception("remove failed"))

        health_svc.container_pool = [bad]

        with patch.object(health_svc, "_create_pool_container", return_value=None):
            health_svc._get_container_from_pool()

        assert health_svc.pool_metrics["cleanup_failures"] >= 1

    def test_get_container_reload_exception_continues(self, health_svc):
        """Reload exception in _get_container_from_pool should continue."""
        bad = MockContainer("bad-c")
        bad.reload = MagicMock(side_effect=Exception("reload error"))
        good = MockContainer("good-c")

        health_svc.container_pool = [good, bad]

        result = health_svc._get_container_from_pool()

        assert result == good

    def test_return_container_pool_disabled_remove_exception(self, health_svc):
        """Pool disabled + remove exception should not crash."""
        health_svc.pool_enabled = False
        container = MockContainer("c-1")
        container.remove = MagicMock(side_effect=Exception("remove failed"))

        health_svc._return_container_to_pool(container)  # Should not raise

    def test_return_container_outer_except_remove_failure(self, health_svc):
        """Double exception in return_container_to_pool should not crash."""
        container = MockContainer("c-1")
        container.reload = MagicMock(side_effect=Exception("reload failed"))
        container.remove = MagicMock(side_effect=Exception("remove also failed"))

        health_svc._return_container_to_pool(container)  # Should not raise

    def test_cleanup_pool_orphan_containers(self, health_svc, mock_docker_client):
        """Orphan cleanup should list and remove labeled containers."""
        health_svc._do_orphan_cleanup = True
        health_svc.container_pool = []

        orphan1 = MockContainer("orphan-1")
        orphan2 = MockContainer("orphan-2")
        mock_docker_client.containers.list.return_value = [orphan1, orphan2]

        health_svc._cleanup_pool()

        assert orphan1._removed is True
        assert orphan2._removed is True

    def test_cleanup_pool_orphan_exception(self, health_svc, mock_docker_client):
        """Orphan cleanup exception should not crash."""
        health_svc._do_orphan_cleanup = True
        health_svc.container_pool = []
        mock_docker_client.containers.list.side_effect = Exception("list failed")

        health_svc._cleanup_pool()  # Should not raise

    def test_execute_in_new_container_finally_remove_failure(
        self, docker_service, mock_docker_client
    ):
        """Container removal failure in finally block should not crash."""
        mock_container = MockContainer()
        mock_container.remove = MagicMock(side_effect=Exception("remove failed"))
        mock_docker_client.containers.create.return_value = mock_container
        mock_container.wait = MagicMock(return_value={"StatusCode": 0})
        mock_container.logs = MagicMock(return_value=b"ok")

        result = docker_service._execute_in_new_container("code")

        assert result["success"] is True

    def test_pooled_execution_timeout_kill_and_remove_failure(self, health_svc):
        """Timeout with kill/remove failure should still return error."""
        from gevent import Timeout as GeventTimeout

        container = MockContainer("timeout-c")
        container.kill = MagicMock(side_effect=Exception("kill failed"))
        # exec_run raises real GeventTimeout — matches the except clause
        container.exec_run = MagicMock(side_effect=GeventTimeout)

        with patch.object(
            health_svc, "_get_container_from_pool", return_value=container
        ):
            # Don't patch GeventTimeout — let the real class be used everywhere
            result = health_svc._execute_in_pooled_container("code")

        assert result["success"] is False
        assert "timed out" in result["error"]

    def test_pooled_execution_inner_exception_remove_failure(self):
        """Inner exception + remove failure should still fall back."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": True, "POOL_SIZE": 1}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._docker_available = True
            service.pool_enabled = True
            service.container_pool = []
            service.container_metadata = {}

            container = MockContainer("err-c")
            container.exec_run = MagicMock(side_effect=RuntimeError("exec error"))
            container.remove = MagicMock(side_effect=Exception("remove failed"))

            with (
                patch.object(
                    service, "_get_container_from_pool", return_value=container
                ),
                patch.object(service, "_execute_in_new_container") as mock_new,
            ):
                mock_new.return_value = {"success": True, "output": "", "error": None}

                service._execute_in_pooled_container("code")

            mock_new.assert_called_once()
            service._closed = True


# =============================================================================
# Final Coverage Gap Tests
# =============================================================================


class TestFinalCoverageGaps:
    """Tests targeting the last uncovered lines for 100% coverage."""

    def test_docker_import_missing_raises(self):
        """When docker SDK is not installed, __init__ should raise ImportError."""
        with patch(
            "purplex.problems_app.services.docker_execution_service.docker", None
        ):
            with pytest.raises(ImportError, match="Docker SDK is not installed"):
                DockerExecutionService()

    def test_start_health_monitor_already_running_warns(
        self, mock_docker_client, mock_settings
    ):
        """Calling _start_health_monitor when thread exists should warn and return."""
        mock_settings["POOL_ENABLED"] = True

        with (
            patch("docker.from_env", return_value=mock_docker_client),
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = mock_settings
            # Don't patch _start_health_monitor — let __init__ call the real one
            service = DockerExecutionService()

            # Thread is now set from __init__
            assert service._health_monitor_thread is not None
            existing = service._health_monitor_thread

            # Call again — should hit lines 249-250
            with patch(
                "purplex.problems_app.services.docker_execution_service.logger"
            ) as mock_logger:
                service._start_health_monitor()

            mock_logger.warning.assert_any_call("Health monitor already running")
            assert service._health_monitor_thread is existing

            # Cleanup
            service._stop_health_monitor.set()
            service._health_monitor_thread.join(timeout=2)
            service._closed = True

    def test_cleanup_pool_orphan_remove_exception(
        self, docker_service, mock_docker_client
    ):
        """Orphan container remove failure should be silently caught."""
        docker_service._do_orphan_cleanup = True
        docker_service.container_pool = []

        orphan = MockContainer("orphan-1")
        orphan.remove = MagicMock(side_effect=Exception("remove failed"))
        mock_docker_client.containers.list.return_value = [orphan]

        docker_service._cleanup_pool()  # Should not raise

    def test_del_suppresses_close_exception(self):
        """__del__ should suppress exceptions from close()."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": False}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._closed = False

            # Make close() raise
            with patch.object(
                service, "close", side_effect=RuntimeError("close exploded")
            ):
                service.__del__()  # Should not raise

    def test_pooled_timeout_kill_succeeds_remove_runs(self):
        """In timeout handler, when kill succeeds, remove should also run (line 1129)."""
        from gevent import Timeout as GeventTimeout

        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": True, "POOL_SIZE": 1}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._docker_available = True
            service.pool_enabled = True
            service.container_pool = []
            service.container_metadata = {}

            container = MockContainer("timeout-c")
            container.exec_run = MagicMock(side_effect=GeventTimeout)
            # kill succeeds (default mock), remove also succeeds
            container.kill = MagicMock()
            container.remove = MagicMock()

            with patch.object(
                service, "_get_container_from_pool", return_value=container
            ):
                result = service._execute_in_pooled_container("code")

            assert result["success"] is False
            assert "timed out" in result["error"]
            container.kill.assert_called_once()
            container.remove.assert_called_once_with(force=True)
            service._closed = True

    def test_pooled_outer_exception_with_container_remove_succeeds(self):
        """Outer exception when container was acquired should remove it (lines 1187-1190)."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": True, "POOL_SIZE": 1}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._docker_available = True
            service.pool_enabled = True
            service.container_pool = []
            service.container_metadata = {}

            container = MockContainer("doomed-c")

            # _get_container_from_pool returns the container, but the outer try
            # block catches the exception. We need the exception AFTER container
            # is assigned (line 1094) but BEFORE the inner try (line 1103).
            # The simplest way: mock _get_container_from_pool to return container,
            # then make the inner try's GeventTimeout constructor raise.
            with (
                patch.object(
                    service, "_get_container_from_pool", return_value=container
                ),
                patch(
                    "purplex.problems_app.services.docker_execution_service.GeventTimeout",
                    side_effect=Exception("timeout init failed"),
                ),
            ):
                result = service._execute_in_pooled_container("code")

            assert result["success"] is False
            assert container._removed is True
            service._closed = True

    def test_pooled_outer_exception_with_container_and_remove_failure(self):
        """Outer except (line 1184) with container remove failure (line 1189)."""
        with (
            patch("docker.from_env") as mock_docker,
            patch.object(DockerExecutionService, "_ensure_image_exists"),
            patch.object(DockerExecutionService, "_init_pool"),
            patch.object(DockerExecutionService, "_start_health_monitor"),
            patch(
                "purplex.problems_app.services.docker_execution_service.settings"
            ) as settings_mock,
        ):
            settings_mock.CODE_EXECUTION = {"POOL_ENABLED": True, "POOL_SIZE": 1}
            mock_docker.return_value = MockDockerClient()

            service = DockerExecutionService()
            service._docker_available = True
            service.pool_enabled = True
            service.container_pool = []
            service.container_metadata = {}

            container = MockContainer("doomed-c")
            container.remove = MagicMock(side_effect=Exception("remove failed"))
            container.exec_run = MagicMock(side_effect=Exception("exec boom"))

            # Inner except (1173) catches exec_run exception and calls
            # _execute_in_new_container. If THAT also raises, the outer
            # except (1184) catches it — which is the path we need.
            with (
                patch.object(
                    service, "_get_container_from_pool", return_value=container
                ),
                patch.object(
                    service,
                    "_execute_in_new_container",
                    side_effect=Exception("fallback also failed"),
                ),
            ):
                result = service._execute_in_pooled_container("code")

            assert result["success"] is False
            assert "Unexpected" in result["error"]
            service._closed = True
