# Contributing to Purplex

Thank you for your interest in contributing to Purplex! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Report Bugs

1. Check the [existing issues](../../issues) to see if the bug has already been reported.
2. If not, [open a new issue](../../issues/new) with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected behavior vs. actual behavior
   - Your environment (OS, Python version, Node.js version, browser)
   - Screenshots or error logs if applicable

## How to Suggest Features

Open a [new issue](../../issues/new) with the label `enhancement` and describe:
- The problem your feature would solve
- Your proposed solution
- Any alternatives you've considered

## Development Setup

1. Fork and clone the repository
2. Follow the setup instructions in [README.md](README.md#quick-start-recommended)
3. The automated `./start.sh` script handles all service dependencies (PostgreSQL, Redis, Django, Celery, Vue)

For detailed architecture and patterns, see the `docs/` directory:
- [STANDARDS.md](docs/development/STANDARDS.md) — coding standards and naming conventions
- [PATTERNS.md](docs/development/PATTERNS.md) — implementation examples and code templates
- [TESTING_FRAMEWORK.md](tests/TESTING_FRAMEWORK.md) — testing guide and patterns

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**, following the project's coding standards:
   - **Python:** PEP 8, Google-style docstrings, type hints
   - **TypeScript:** ESLint configured, Vue 3 Composition API
   - **Models:** Singular names, snake_case fields
   - **API:** RESTful conventions, consistent error format

3. **Write tests** for your changes:
   ```bash
   # Run the full test suite
   make test

   # Run only unit tests
   make test-unit

   # Run frontend tests
   cd purplex/client && npm run test
   ```

4. **Run linters and formatters:**
   ```bash
   make lint
   make format
   ```

5. **Submit a pull request** with:
   - A clear description of the changes
   - Reference to any related issues
   - Confirmation that tests pass

## Project Structure

- `purplex/problems_app/` — Problems, problem sets, courses, hints, test cases
- `purplex/submissions/` — Code submissions, execution results, scoring
- `purplex/progress/` — User progress tracking, analytics
- `purplex/users_app/` — User management, Firebase integration
- `purplex/client/` — Vue 3 + TypeScript frontend

## Questions?

If you have questions about contributing, feel free to open a discussion or issue.
