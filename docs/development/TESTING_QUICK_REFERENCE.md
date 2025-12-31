# Testing Quick Reference Card

## Quick Start

```bash
# Setup (one time)
source env/bin/activate
export DJANGO_SETTINGS_MODULE=purplex.settings

# Run all tests
pytest

# Run with coverage
pytest --cov=purplex --cov-report=html
```

## Common Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest tests/unit/` | Run only unit tests |
| `pytest tests/integration/` | Run only integration tests |
| `pytest -m unit` | Run tests marked as unit |
| `pytest -m integration` | Run tests marked as integration |
| `pytest -n auto` | Run tests in parallel (faster) |
| `pytest -v` | Verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Re-run last failed tests |
| `pytest -k "test_name"` | Run tests matching pattern |
| `pytest --cov=purplex --cov-report=html` | Coverage report |

## Test Markers

| Marker | Usage | Description |
|--------|-------|-------------|
| `@pytest.mark.unit` | Unit tests | Fast, isolated tests |
| `@pytest.mark.integration` | Integration tests | Workflow tests |
| `@pytest.mark.django_db` | Database tests | Requires database access |
| `@pytest.mark.slow` | Slow tests | Skip with `-m "not slow"` |
| `@pytest.mark.architecture` | Architecture tests | Pattern enforcement tests |

## Fixtures

Defined in `tests/conftest.py`:

| Fixture | Description |
|---------|-------------|
| `api_client` | DRF API client for testing |
| `authenticated_client` | API client authenticated as regular user |
| `user` | Standard test user with profile |
| `instructor` | Instructor user with profile |
| `admin_user` | Admin/superuser with profile |
| `eipl_problem` | EiPL (Explain in Plain Language) problem |
| `mcq_problem` | Multiple Choice Question problem |
| `prompt_problem` | Prompt-based problem |
| `problem_set` | Empty problem set |
| `course` | Course with instructor |

## Factories

Defined in `tests/factories/__init__.py`:

```python
from tests.factories import (
    UserFactory, UserProfileFactory,
    EiplProblemFactory, McqProblemFactory, PromptProblemFactory,
    ProblemSetFactory, ProblemSetMembershipFactory,
    CourseFactory, CourseEnrollmentFactory
)

user = UserFactory.create(username='student1')
problem = EiplProblemFactory.create(title='Custom Problem')
course = CourseFactory.create(name='Test Course')
```

## CI/CD

Configured in `.github/workflows/ci.yml`.

### Status Checks

- **Lint** - Code quality (flake8, black, isort, eslint, typecheck)
- **Unit Tests** - Python 3.11 & 3.12 (min 30% coverage, required)
- **Integration Tests** - Workflow tests (allowed to fail)
- **Frontend Tests** - Vue component tests (required)
- **Security** - Bandit, Safety, Trivy scans
- **Build** - Docker images (depends on all tests passing)

### Coverage Requirements

- **Unit Tests**: >= 30% (enforced via --cov-fail-under=30)

## Debugging

```bash
# Verbose output
pytest -vv --tb=long

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show slow tests
pytest --durations=10
```

## Coverage

```bash
# Generate HTML report
pytest --cov=purplex --cov-report=html
open htmlcov/index.html

# Show missing lines
pytest --cov=purplex --cov-report=term-missing

# Coverage for specific module
pytest --cov=purplex.problems_app.services
```

## Environment Variables

```bash
export DJANGO_SETTINGS_MODULE=purplex.settings
export PURPLEX_ENV=development
export USE_MOCK_FIREBASE=true
export USE_MOCK_OPENAI=true
export DISABLE_FILE_LOGGING=true
```

## Test Template

```python
import pytest
from tests.factories import UserFactory, EiplProblemFactory


@pytest.mark.django_db
class TestMyFeature:
    """Test my feature."""

    def test_feature_works(self, user):
        """Test feature works correctly."""
        # Arrange
        problem = EiplProblemFactory.create()
        expected = "result"

        # Act
        result = my_function(user, problem)

        # Assert
        assert result == expected
```

## Common Issues

| Issue | Solution |
|-------|----------|
| 403 Forbidden | Use `authenticated_client` fixture |
| Database errors | Run `python manage.py migrate` |
| File logging errors | Set `DISABLE_FILE_LOGGING=true` |
| Import errors | Check `DJANGO_SETTINGS_MODULE` is set |
| Slow tests | Run with `-n auto` for parallel |

## Directory Structure

```
tests/
  conftest.py           # Shared fixtures
  factories/
    __init__.py         # Factory definitions
  unit/
    test_handlers.py
    test_registry_consistency.py
    test_service_isolation.py
    test_serializer_patterns.py
    test_repository_pattern.py
    test_api_consistency.py
  integration/
    test_polymorphic_*.py
    test_problem_models.py
    test_supporting_models.py
```

## Configuration Files

- Pytest config: `pytest.ini`
- CI workflow: `.github/workflows/ci.yml`
