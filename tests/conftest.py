"""
Pytest configuration and fixtures for Purplex test suite.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, TestCase, Course


# Counter for unique test users
_user_counter = 0


@pytest.fixture
def api_client():
    """Provide a Django test client for API testing."""
    return Client()


@pytest.fixture
def test_user(db):
    """Create a test user for authentication with unique username."""
    global _user_counter
    _user_counter += 1
    return User.objects.create_user(
        username=f'testuser{_user_counter}',
        email=f'test{_user_counter}@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, test_user, mock_firebase_auth):
    """Provide an authenticated test client with proper Firebase auth mocking."""
    # Force login for Django session
    api_client.force_login(test_user)

    # Mock Firebase authentication to return the test user
    mock_firebase_auth.return_value = (test_user, {'uid': f'test-uid-{test_user.id}'})

    return api_client


@pytest.fixture
def mock_firebase_auth(monkeypatch):
    """Mock Firebase authentication service globally."""
    mock = MagicMock()
    monkeypatch.setattr(
        'purplex.users_app.services.authentication_service.AuthenticationService.authenticate_token',
        mock
    )
    return mock


@pytest.fixture
def mock_docker_execution(monkeypatch):
    """Mock Docker execution service to avoid actual container creation."""
    def mock_execute(*args, **kwargs):
        return {
            'success': True,
            'results': [
                {
                    'test_number': 1,
                    'isSuccessful': True,
                    'actual_output': [0, 1],
                    'expected_output': [0, 1],
                    'inputs': {'nums': [2, 7, 11, 15], 'target': 9}
                }
            ],
            'testsPassed': 1,
            'totalTests': 1
        }

    mock = MagicMock(side_effect=mock_execute)
    monkeypatch.setattr(
        'purplex.problems_app.services.docker_execution_service.DockerExecutionService.execute_code_safely',
        mock
    )
    return mock


@pytest.fixture
def test_problem(db):
    """Create a test problem."""
    problem = Problem.objects.create(
        title="Two Sum",
        slug="two-sum",
        description="Find two numbers that add to target",
        difficulty="easy",
        function_name="two_sum",
        function_signature="def two_sum(nums: List[int], target: int) -> List[int]:",
        reference_solution="""def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []""",
        problem_type="function_redefinition",
        is_active=True
    )
    
    # Add test cases
    TestCase.objects.create(
        problem=problem,
        inputs={"nums": [2, 7, 11, 15], "target": 9},
        expected_output=[0, 1],
        description="Basic test case",
        is_hidden=False,
        order=1
    )
    
    TestCase.objects.create(
        problem=problem,
        inputs={"nums": [3, 2, 4], "target": 6},
        expected_output=[1, 2],
        description="Another test case",
        is_hidden=True,
        order=2
    )
    
    return problem


@pytest.fixture
def test_problem_set(db, test_problem):
    """Create a test problem set."""
    problem_set = ProblemSet.objects.create(
        title="Arrays and Hashing",
        slug="arrays-hashing",
        description="Basic array problems"
    )
    problem_set.problems.add(test_problem)
    return problem_set


@pytest.fixture
def test_course(db):
    """Create a test course."""
    return Course.objects.create(
        course_id="CS101",
        name="Introduction to Programming",
        description="Learn the basics of programming",
        is_active=True
    )


@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI API calls to avoid external dependencies."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []"""
            )
        )
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    # Mock both old and new OpenAI client formats
    monkeypatch.setattr("openai.ChatCompletion.create", lambda *args, **kwargs: mock_response)
    monkeypatch.setattr("openai.OpenAI", lambda *args, **kwargs: mock_client)

    return mock_client


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, db):
    """Auto-setup test environment variables and mocks for all tests."""
    # Set test environment variables
    monkeypatch.setenv('USE_MOCK_FIREBASE', 'true')
    monkeypatch.setenv('USE_MOCK_OPENAI', 'true')
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', 'purplex.settings')
    monkeypatch.setenv('PURPLEX_ENV', 'development')

    # Create a default test user for authentication
    from django.contrib.auth.models import User
    test_user, _ = User.objects.get_or_create(
        username='default_test_user',
        defaults={'email': 'default@test.com'}
    )

    # Mock Firebase authentication globally to return the test user
    def mock_authenticate(self, request):
        return (test_user, {'uid': f'test-uid-{test_user.id}'})

    monkeypatch.setattr(
        'purplex.users_app.authentication.PurplexAuthentication.authenticate',
        mock_authenticate
    )


@pytest.fixture
def bypass_authentication(monkeypatch):
    """Bypass authentication entirely for validation-focused tests."""
    def mock_auth(*args, **kwargs):
        # Return a mock user without actual authentication
        from django.contrib.auth.models import AnonymousUser
        return (AnonymousUser(), None)

    monkeypatch.setattr(
        'purplex.users_app.authentication.PurplexAuthentication.authenticate',
        mock_auth
    )