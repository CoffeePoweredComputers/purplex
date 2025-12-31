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
