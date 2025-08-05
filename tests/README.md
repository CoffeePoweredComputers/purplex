# Purplex Test Suite

## Getting Started

### Installation
```bash
# Activate virtual environment
source env/bin/activate

# Install test dependencies (already in requirements.txt)
pip install pytest pytest-django pytest-cov
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=purplex

# Run specific test file
pytest tests/unit/test_validation.py

# Run tests matching a pattern
pytest -k "rate_limit"

# Run with short traceback
pytest --tb=short
```

### Test Structure
```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   └── test_validation.py
├── integration/         # Integration tests
│   └── test_rate_limiting.py
└── test_setup.py        # Basic setup verification
```

### Common Issues

1. **Import Errors**: Make sure to use full module paths (e.g., `purplex.problems_app.models`)
2. **Database Errors**: Tests use a separate test database that's created/destroyed automatically
3. **URL Reverse Errors**: Check `urls.py` for correct URL names

### Writing New Tests

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Use fixtures from `conftest.py` for common test data
4. Mark database tests with `@pytest.mark.django_db`

### CI/CD

Tests run automatically on GitHub Actions for every push and PR. See `.github/workflows/tests.yml` for configuration.