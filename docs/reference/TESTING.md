# Testing Guide for Purplex

## Overview

Purplex has a comprehensive testing infrastructure with unit tests, integration tests, and performance tests, all integrated into GitHub Actions CI/CD.

## Test Structure

```
tests/
├── conftest.py              # Global test fixtures and configuration
├── __init__.py
├── factories/               # Test data factories (factory_boy)
│   └── __init__.py
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_api_consistency.py
│   ├── test_handlers.py
│   ├── test_registry_consistency.py
│   ├── test_repository_pattern.py
│   ├── test_serializer_patterns.py
│   └── test_service_isolation.py
└── integration/             # Integration tests (workflows)
    ├── test_polymorphic_comprehensive.py
    ├── test_polymorphic_edge_cases.py
    ├── test_polymorphic_grading.py
    ├── test_polymorphic_problems.py
    ├── test_polymorphic_serializers.py
    ├── test_polymorphic_services.py
    ├── test_problem_models.py
    └── test_supporting_models.py
```

## Running Tests Locally

### Prerequisites

```bash
# Ensure virtual environment is activated
source env/bin/activate

# Set environment variables
export DJANGO_SETTINGS_MODULE=purplex.settings
export PURPLEX_ENV=development
export USE_MOCK_FIREBASE=true
export USE_MOCK_OPENAI=true
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=purplex --cov-report=html
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Run tests in parallel (faster)
pytest -n auto

# Run specific test file
pytest tests/unit/test_handlers.py

# Run specific test
pytest tests/unit/test_handlers.py::TestHandlers::test_handler_exists
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run tests requiring database
pytest -m django_db

# Run architecture enforcement tests
pytest -m architecture
```

## Test Fixtures

### Available Fixtures (from `conftest.py`)

**API Clients:**
- `api_client` - DRF API client for API testing
- `authenticated_client` - API client authenticated as a regular user

**User Fixtures:**
- `user` - Standard test user with profile
- `instructor` - Instructor user with profile
- `admin_user` - Admin/superuser with profile

**Problem Fixtures:**
- `eipl_problem` - Standard EiPL (Explain in Plain Language) problem
- `mcq_problem` - Standard MCQ (Multiple Choice Question) problem
- `prompt_problem` - Standard Prompt-based problem

**Container Fixtures:**
- `problem_set` - Empty problem set
- `course` - Course with an instructor

### Using Fixtures

```python
@pytest.mark.django_db
class TestMyFeature:
    def test_something(self, authenticated_client, eipl_problem):
        response = authenticated_client.get(f'/api/problems/{eipl_problem.slug}/')
        assert response.status_code == 200
```

## Test Factories

Use factory_boy factories to create test data:

```python
from tests.factories import (
    UserFactory, UserProfileFactory,
    EiplProblemFactory, McqProblemFactory, PromptProblemFactory,
    ProblemSetFactory, ProblemSetMembershipFactory,
    CourseFactory, CourseEnrollmentFactory
)

def test_with_factories(self):
    # Create user with profile
    user = UserFactory.create(username='student1')
    UserProfileFactory.create(user=user)

    # Create different problem types
    eipl_problem = EiplProblemFactory.create(title='Custom EiPL Problem')
    mcq_problem = McqProblemFactory.create(title='Custom MCQ')

    # Create problem set with membership
    problem_set = ProblemSetFactory.create()
    ProblemSetMembershipFactory.create(
        problem_set=problem_set,
        problem=eipl_problem,
        order=0
    )

    # Create course with enrollment
    course = CourseFactory.create()
    CourseEnrollmentFactory.create(user=user, course=course)
```

### Available Factories

- `UserFactory` - Django User model
- `UserProfileFactory` - User profile with Firebase UID
- `EiplProblemFactory` - EiPL problems (code explanation)
- `McqProblemFactory` - Multiple choice problems
- `PromptProblemFactory` - Prompt-based problems (image analysis)
- `ProblemSetFactory` - Problem set containers
- `ProblemSetMembershipFactory` - Problem-to-set relationships
- `CourseFactory` - Courses with instructors
- `CourseEnrollmentFactory` - User-to-course enrollments

## CI/CD Integration

### GitHub Actions Workflows

There are multiple workflow files:

- `.github/workflows/ci.yml` - Main CI pipeline
- `.github/workflows/postgres-tests.yml` - PostgreSQL-specific tests
- `.github/workflows/postgres-load-tests.yml` - Load testing with Locust
- `.github/workflows/security.yml` - Security scanning

### Triggers

**Main CI (`ci.yml`)** runs on:
- Push to `main`, `develop`, or `feature/**` branches
- Pull requests to `main` or `develop`

**PostgreSQL Tests (`postgres-tests.yml`)** runs on:
- All branches (push and pull request)

**Load Tests (`postgres-load-tests.yml`)** runs on:
- Manual trigger (workflow_dispatch)
- Weekly schedule (Sundays at 2 AM)
- Pull requests with `load-test` label

**Security Scans (`security.yml`)** runs on:
- Daily at 2 AM UTC
- Push/PR to `master` or `main` (for specific file changes)

### Test Matrix

- **Unit Tests**: Run on Python 3.11 and 3.12 (parallel with pytest-xdist)
- **Integration Tests**: Run on Python 3.11 (depends on unit tests passing)
- **Frontend Tests**: Run with Node 20 and Yarn

### Coverage Requirements

- **Unit Tests**: Minimum 30% coverage (enforced via `--cov-fail-under=30`)
- Coverage uploaded to Codecov for both unit and integration tests

### CI Jobs (Main Pipeline)

1. **Lint** - Code quality checks (flake8, black, isort for Python; ESLint, TypeScript for frontend)
2. **Unit Tests** - Fast, isolated tests with parallel execution (`-n auto`)
3. **Integration Tests** - Workflow tests (depends on unit tests, allowed to fail)
4. **Frontend Tests** - Vue component and composable tests with coverage
5. **Security** - Bandit security scan, Safety dependency check, Trivy container scan
6. **Build** - Docker image builds (depends on all tests passing)
7. **Test Summary** - Aggregated results (fails if unit or frontend tests fail)

### Viewing Results

- **GitHub Actions**: See workflow runs in the Actions tab
- **Codecov**: Coverage reports uploaded automatically
- **Test Summary**: View in PR checks and workflow summary
- **Load Test Artifacts**: HTML reports and CSV results uploaded as artifacts

## Writing New Tests

### Unit Test Example

```python
"""
Test my new feature.
"""
import pytest
from tests.factories import UserFactory, UserProfileFactory, EiplProblemFactory


@pytest.mark.django_db
@pytest.mark.unit
class TestMyFeature:
    """Test description."""

    def test_feature_works(self):
        """Test that feature works correctly."""
        # Arrange
        user = UserFactory.create()
        UserProfileFactory.create(user=user)
        problem = EiplProblemFactory.create()

        # Act
        result = my_function(user, problem)

        # Assert
        assert result == "expected"
```

### Integration Test Example

```python
"""
Test complete workflow.
"""
import pytest
from tests.factories import (
    EiplProblemFactory, ProblemSetFactory,
    ProblemSetMembershipFactory
)


@pytest.mark.django_db
@pytest.mark.integration
class TestPolymorphicWorkflow:
    """Test polymorphic problem workflow."""

    def test_problem_set_workflow(self, authenticated_client):
        """Test problem set with multiple problem types."""
        # Create test data
        problem = EiplProblemFactory.create()
        problem_set = ProblemSetFactory.create()
        ProblemSetMembershipFactory.create(
            problem_set=problem_set,
            problem=problem,
            order=0
        )

        # Access problem via API
        response = authenticated_client.get(
            f'/api/problems/{problem.slug}/'
        )

        # Verify response
        assert response.status_code == 200
        assert response.data['slug'] == problem.slug
```

## Debugging Tests

### Run with verbose output

```bash
pytest -vv --tb=long
```

### Run with pdb debugger

```bash
pytest --pdb
```

### Show print statements

```bash
pytest -s
```

### Re-run only failed tests

```bash
pytest --lf
```

## Load Testing

Load testing is run via GitHub Actions using Locust. See `.github/workflows/postgres-load-tests.yml`.

**Triggers:**
- Manual: workflow_dispatch
- Weekly: Sundays at 2 AM
- PR label: `load-test`

**What it tests:**
- Problem browsing workflows
- Problem set access
- Concurrent database connections
- API response times under load (up to 200-300 concurrent users)

**Viewing results:**
- HTML reports and CSV files uploaded as GitHub Actions artifacts
- Database connection statistics logged in workflow output

## Common Issues

### Authentication Errors (403)

If you see 403 errors in tests:

1. Check that the `authenticated_client` fixture is used (it calls `force_authenticate`)
2. Ensure the `user` fixture is being injected (required by `authenticated_client`)
3. Verify environment variables are set correctly:
   - `USE_MOCK_FIREBASE=true`
   - `USE_MOCK_OPENAI=true`

### Database Issues

```bash
# Reset test database
python manage.py flush --database=default

# Re-run migrations
python manage.py migrate --database=default
```

### File Logging Permission Errors

```bash
# Disable file logging for tests
export DISABLE_FILE_LOGGING=true
```

## Coverage Reports

### Generate HTML Coverage Report

```bash
pytest --cov=purplex --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### View Missing Coverage

```bash
pytest --cov=purplex --cov-report=term-missing
```

## Best Practices

1. **Keep tests fast** - Mock external services (AI, Docker, Firebase)
2. **Use factories** - Use factory_boy factories from `tests/factories/` instead of creating data manually
3. **Descriptive names** - Test names should describe what they test
4. **One assertion per test** - Focus tests on single behaviors
5. **Arrange-Act-Assert** - Structure tests clearly
6. **Use fixtures** - Leverage pytest fixtures from `conftest.py` for common setup
7. **Test edge cases** - Not just happy paths
8. **Mark tests appropriately** - Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.architecture`, etc.
9. **Use pytest style** - Prefer pytest-style assertions (`assert x == y`) over unittest-style (`self.assertEqual`)

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Codecov Documentation](https://docs.codecov.com/)
