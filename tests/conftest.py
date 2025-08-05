"""
Pytest configuration and fixtures for Purplex test suite.
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, TestCase, Course


@pytest.fixture
def api_client():
    """Provide a Django test client for API testing."""
    return Client()


@pytest.fixture
def test_user(db):
    """Create a test user for authentication."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Provide an authenticated test client."""
    api_client.force_login(test_user)
    return api_client


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
    def mock_create(*args, **kwargs):
        return {
            "choices": [{
                "message": {
                    "content": """def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []"""
                }
            }]
        }
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)