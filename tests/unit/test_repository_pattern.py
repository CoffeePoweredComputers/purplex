"""
Architectural tests to enforce repository pattern in views.

These tests verify that:
- Views use repositories instead of direct ORM calls
- Models are not directly queried with .objects in view files
- Repository abstraction is consistently applied

WHY THIS APPROACH?
==================
This uses Python's AST module to detect `Model.objects.*` method calls in view
files. This is superior to import-based tools (import-linter, pytest-archon,
PyTestArch) because:

1. Import-based tools can only enforce "module A cannot import module B"
2. Views legitimately need to import models for type hints, isinstance checks, etc.
3. We need to detect METHOD CALLS (`.objects.get()`), not import statements

Alternative approaches considered:
- Ruff: Does not support custom rules (all rules are built-in)
- Flake8 plugin: Would work but requires package + entry points setup
- Semgrep: Would work with YAML rules but adds tooling overhead

REFERENCES:
- Cosmic Python book: https://www.cosmicpython.com/book/appendix_django.html
- PyTestArch (for import rules): https://pypi.org/project/PyTestArch/
- import-linter (for layer enforcement): https://github.com/seddonym/import-linter

Run with: pytest tests/unit/test_repository_pattern.py -v
Run architecture tests only: pytest -m architecture
"""

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# Mark all tests in this module as unit tests and architecture tests
pytestmark = [pytest.mark.unit, pytest.mark.architecture]


class ORMViolation(NamedTuple):
    """Represents a direct ORM call violation."""

    file: str
    line: int
    code: str
    model: str


# =============================================================================
# CONFIGURATION - Customize these for your project
# =============================================================================

# Models that should be accessed through repositories.
# Add any model that has a corresponding repository class.
PROTECTED_MODELS = {
    # Core models
    "Problem",
    "ProblemSet",
    "Course",
    "User",
    "Submission",
    "TestCase",
    "Hint",
    "ProblemHint",
    "ProgressSnapshot",
    "CourseEnrollment",
    "ProblemSetMembership",
    "ProblemCategory",
    # Progress tracking models
    "UserProgress",
    "UserProblemSetProgress",
    "HintActivation",
    # Polymorphic subclasses
    "EiplProblem",
    "McqProblem",
    "PromptProblem",
}

# Directories that are allowed to use direct ORM.
# These patterns match against any part of the file path.
ALLOWED_PATHS = {
    "repositories",  # Repositories ARE the ORM abstraction
    "migrations",  # Django migrations need direct model access
    "admin.py",  # Django admin customization
    "management",  # Management commands
    "tests",  # Test files can use direct ORM for setup
}

# Serializer files that should be checked for ORM violations.
# Serializers should NOT contain direct ORM calls - delegate to services.
SERIALIZER_FILES = [
    "purplex/problems_app/serializers.py",
    "purplex/users_app/serializers.py",
]

# Service files that should be checked for ORM violations.
# Services should use repositories, not direct ORM.
SERVICE_PATTERNS = [
    "purplex/problems_app/services",
    "purplex/users_app/services",
    "purplex/submissions",  # submissions services
]

# Handler files that should be checked for ORM violations.
# Handlers process problem type logic and should receive properly-typed objects
# from services/views, not query the database directly.
# This is critical for maintaining clean architecture as new problem types are added.
HANDLER_PATTERNS = [
    "purplex/problems_app/handlers",
]

# Specific files with documented exceptions.
# Key: filename, Value: set of patterns that are allowed.
# Use this for complex queries that don't fit standard repository patterns.
#
# NOTE: As of 2025-12, ALL exceptions have been eliminated.
# All ORM calls now go through the repository layer.
# This dictionary is intentionally empty to enforce zero exceptions.
EXCEPTIONS = {}


# =============================================================================
# AST VISITOR IMPLEMENTATION
# =============================================================================


class ORMUsageVisitor(ast.NodeVisitor):
    """
    AST visitor to find direct .objects calls on protected models.

    Detects patterns like:
        User.objects.get(id=1)
        Problem.objects.filter(active=True)
        Course.objects.all()

    References:
    - Python AST docs: https://docs.python.org/3/library/ast.html
    - Green Tree Snakes: https://greentreesnakes.readthedocs.io/
    """

    def __init__(self, protected_models: set[str]):
        self.protected_models = protected_models
        self.violations: list[tuple[int, str, str]] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """
        Visit attribute access nodes to detect Model.objects patterns.

        The AST for `User.objects.get(id=1)` looks like:
            Call(
                func=Attribute(
                    value=Attribute(
                        value=Name(id='User'),  # <-- We detect this
                        attr='objects'           # <-- Combined with this
                    ),
                    attr='get'
                )
            )
        """
        # Look for pattern: Model.objects
        if (
            node.attr == "objects"
            and isinstance(node.value, ast.Name)
            and node.value.id in self.protected_models
        ):
            self.violations.append(
                (node.lineno, f"{node.value.id}.objects", node.value.id)
            )

        self.generic_visit(node)


# =============================================================================
# FILE SCANNING UTILITIES
# =============================================================================


def find_orm_violations(file_path: Path) -> list[ORMViolation]:
    """Find direct ORM calls in a Python file."""
    violations = []

    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    visitor = ORMUsageVisitor(PROTECTED_MODELS)
    visitor.visit(tree)

    # Filter out allowed exceptions for this file
    file_name = file_path.name
    allowed_patterns = EXCEPTIONS.get(file_name, set())

    for line, code, model in visitor.violations:
        # Check if this specific usage is in exceptions
        if not any(pattern in code for pattern in allowed_patterns):
            violations.append(
                ORMViolation(file=str(file_path), line=line, code=code, model=model)
            )

    return violations


def should_check_file(file_path: Path) -> bool:
    """
    Determine if a file should be checked for ORM violations.

    Only checks view files, excluding:
    - Repository files (they're supposed to use ORM)
    - Migration files
    - Admin files
    - Management commands
    - Test files
    """
    path_parts = file_path.parts

    # Skip files in allowed paths
    for allowed in ALLOWED_PATHS:
        if allowed in path_parts or file_path.name == allowed:
            return False

    # Only check Python files
    if file_path.suffix != ".py":
        return False

    # Only check view files
    return "views" in path_parts or file_path.name.endswith("_views.py")


def get_view_files(base_path: Path) -> list[Path]:
    """Get all view files that should be checked."""
    view_files = []

    for py_file in base_path.rglob("*.py"):
        if should_check_file(py_file):
            view_files.append(py_file)

    return view_files


def is_serializer_file(file_path: Path) -> bool:
    """Check if a file is a serializer file that should be checked."""
    path_str = str(file_path)
    return any(ser_file in path_str for ser_file in SERIALIZER_FILES)


def is_service_file(file_path: Path) -> bool:
    """
    Check if a file is a service file that should be checked.

    Excludes:
    - Repository files
    - __init__.py files
    - Test files
    """
    path_str = str(file_path)

    # Skip repositories and init files
    if "repositories" in path_str or file_path.name == "__init__.py":
        return False

    # Skip test files
    if "tests" in path_str:
        return False

    # Check if in a service directory
    return any(pattern in path_str for pattern in SERVICE_PATTERNS)


def get_serializer_files(project_root: Path) -> list[Path]:
    """Get all serializer files that should be checked."""
    serializer_files = []
    for ser_path in SERIALIZER_FILES:
        full_path = project_root / ser_path
        if full_path.exists():
            serializer_files.append(full_path)
    return serializer_files


def get_service_files(project_root: Path) -> list[Path]:
    """Get all service files that should be checked."""
    service_files = []

    for pattern in SERVICE_PATTERNS:
        service_dir = project_root / pattern
        if service_dir.exists():
            if service_dir.is_file():
                # Direct file reference
                service_files.append(service_dir)
            else:
                # Directory - get all Python files
                for py_file in service_dir.rglob("*.py"):
                    if is_service_file(py_file):
                        service_files.append(py_file)

    return service_files


def is_handler_file(file_path: Path) -> bool:
    """
    Check if a file is a handler file that should be checked.

    Handlers are problem-type-specific processors (eipl, mcq, prompt, etc.)
    that should receive properly-typed objects from the service layer,
    not query the database directly.

    Excludes:
    - __init__.py files
    - Test files
    - Base handler (may have legitimate patterns)
    """
    path_str = str(file_path)

    # Skip init files
    if file_path.name == "__init__.py":
        return False

    # Skip test files
    if "tests" in path_str:
        return False

    # Check if in a handler directory
    return any(pattern in path_str for pattern in HANDLER_PATTERNS)


def get_handler_files(project_root: Path) -> list[Path]:
    """
    Get all handler files that should be checked.

    This is critical for enforcing clean architecture as new problem types
    (question types) are added. Each handler should:
    - Receive properly-typed model instances from views/services
    - NOT query the database directly
    - Focus on processing logic, not data access
    """
    handler_files = []

    for pattern in HANDLER_PATTERNS:
        handler_dir = project_root / pattern
        if handler_dir.exists():
            for py_file in handler_dir.rglob("*.py"):
                if is_handler_file(py_file):
                    handler_files.append(py_file)

    return handler_files


# =============================================================================
# ARCHITECTURE ENFORCEMENT TESTS
# =============================================================================


@pytest.mark.architecture
class TestRepositoryPatternEnforcement:
    """
    Tests to enforce repository pattern usage in views.

    These tests will fail if any view file contains direct ORM calls like:
        user = User.objects.get(id=1)  # FAILS
        user = UserRepository.get_by_id(user_id)  # PASSES

    To fix violations:
    1. Create/use a repository method for the data access
    2. Or add the file/pattern to EXCEPTIONS with documentation
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def problems_app_path(self, project_root: Path) -> Path:
        """Get the problems_app directory."""
        return project_root / "purplex" / "problems_app"

    @pytest.fixture
    def submissions_app_path(self, project_root: Path) -> Path:
        """Get the submissions directory."""
        return project_root / "purplex" / "submissions"

    @pytest.fixture
    def users_app_path(self, project_root: Path) -> Path:
        """Get the users_app directory."""
        return project_root / "purplex" / "users_app"

    def _check_app_for_violations(self, app_path: Path, app_name: str) -> None:
        """Check an app's view files for ORM violations."""
        view_files = get_view_files(app_path)
        all_violations = []

        for view_file in view_files:
            violations = find_orm_violations(view_file)
            all_violations.extend(violations)

        if all_violations:
            violation_report = "\n".join(
                f"  {v.file}:{v.line} - {v.code}" for v in all_violations
            )
            pytest.fail(
                f"Found {len(all_violations)} direct ORM calls in {app_name} view files.\n"
                f"Use repository methods instead:\n{violation_report}\n\n"
                f"To fix: Replace `{all_violations[0].model}.objects.method()` "
                f"with `{all_violations[0].model}Repository.method()`"
            )

    def test_violation_detection_triggers_failure(self, tmp_path: Path):
        """Should fail with clear message when violations are found."""
        # Create a fake views directory with a violation
        views_dir = tmp_path / "views"
        views_dir.mkdir()
        bad_view = views_dir / "bad_view.py"
        bad_view.write_text("user = User.objects.get(id=1)")

        with pytest.raises(pytest.fail.Exception) as exc_info:
            self._check_app_for_violations(tmp_path, "test_app")

        error_message = str(exc_info.value)
        assert "Found 1 direct ORM calls" in error_message
        assert "User.objects" in error_message
        assert "UserRepository" in error_message

    def test_problems_app_views_use_repositories(self, problems_app_path: Path):
        """Views in problems_app should use repositories instead of direct ORM."""
        self._check_app_for_violations(problems_app_path, "problems_app")

    def test_submissions_views_use_repositories(self, submissions_app_path: Path):
        """Views in submissions should use repositories instead of direct ORM."""
        self._check_app_for_violations(submissions_app_path, "submissions")

    def test_users_app_views_use_repositories(self, users_app_path: Path):
        """Views in users_app should use repositories instead of direct ORM."""
        self._check_app_for_violations(users_app_path, "users_app")

    # -------------------------------------------------------------------------
    # SERIALIZER PATTERN ENFORCEMENT
    # -------------------------------------------------------------------------

    def _check_files_for_violations(self, files: list[Path], file_type: str) -> None:
        """Check a list of files for ORM violations."""
        all_violations = []

        for file_path in files:
            violations = find_orm_violations(file_path)
            all_violations.extend(violations)

        if all_violations:
            violation_report = "\n".join(
                f"  {v.file}:{v.line} - {v.code}" for v in all_violations
            )
            pytest.fail(
                f"Found {len(all_violations)} direct ORM calls in {file_type} files.\n"
                f"Serializers should delegate to services, services should use repositories.\n"
                f"Violations:\n{violation_report}\n\n"
                f"To fix: Move ORM call to repository layer or add to EXCEPTIONS with documentation."
            )

    def test_serializers_do_not_use_orm(self, project_root: Path):
        """
        Serializers should not contain direct ORM calls.

        Serializers are for data validation and transformation.
        Business logic with ORM should be in services.
        """
        serializer_files = get_serializer_files(project_root)
        self._check_files_for_violations(serializer_files, "serializer")

    # -------------------------------------------------------------------------
    # SERVICE PATTERN ENFORCEMENT
    # -------------------------------------------------------------------------

    def test_services_use_repositories(self, project_root: Path):
        """
        Services should use repositories instead of direct ORM calls.

        Services contain business logic. Data access should be delegated
        to the repository layer for:
        - Testability (repositories can be mocked)
        - Consistency (all queries go through one place)
        - Separation of concerns
        """
        service_files = get_service_files(project_root)
        self._check_files_for_violations(service_files, "service")

    # -------------------------------------------------------------------------
    # HANDLER PATTERN ENFORCEMENT
    # -------------------------------------------------------------------------

    def test_handlers_do_not_use_orm(self, project_root: Path):
        """
        Handlers should not contain direct ORM calls.

        Handlers are problem-type-specific processors (eipl, mcq, prompt, etc.)
        that implement the logic for each question type. They should:

        1. Receive properly-typed model instances from views/services
        2. NOT query the database directly
        3. Focus on processing logic (validation, grading, config generation)

        This test is CRITICAL for maintaining clean architecture as new
        problem types are added. When you create a new handler:

        - Views/services should resolve the correct model subclass
        - Pass the typed instance to the handler
        - Handler should never call Model.objects.*

        Example violation:
            def process(self, problem):
                mcq = McqProblem.objects.get(pk=problem.pk)  # BAD!

        Correct approach:
            def process(self, problem: McqProblem):
                # problem is already the correct type
                return problem.options  # GOOD!
        """
        handler_files = get_handler_files(project_root)
        self._check_files_for_violations(handler_files, "handler")

    # -------------------------------------------------------------------------
    # BARE EXCEPT ENFORCEMENT
    # -------------------------------------------------------------------------

    # Pre-existing bare except Exception in views — tracked for cleanup.
    # Do NOT add new files here. Fix the violation instead.
    # Pre-existing bare except Exception — tracked for cleanup.
    # Do NOT add new files here. Fix the violation instead.
    _BARE_EXCEPT_ALLOWED = {
        "health_views.py",  # Health check catches all for uptime reporting
        "submission_views.py",  # Pre-existing; needs service refactor
        "progress_views.py",  # Pre-existing; needs service refactor
        "instructor_views.py",  # Pre-existing; needs service refactor
        "instructor_content_views.py",  # Pre-existing; needs service refactor
        "instructor_analytics_views.py",  # Pre-existing; needs service refactor
        "admin_views.py",  # Pre-existing; needs service refactor
        "sse.py",  # SSE streaming catches all for connection cleanup
    }

    def test_views_no_bare_except_exception(self, project_root: Path):
        """
        Views must not use bare `except Exception`.

        The custom exception handler returns JSON 500 for unhandled exceptions.
        Bare `except Exception` hides bugs. If a service call should be
        fire-and-forget, the service must provide a *_best_effort() wrapper
        that handles errors internally.

        Correct approach:
            # In service:
            ActivityEventService.record_best_effort(...)

            # NOT in view:
            try:
                ActivityEventService.record(...)
            except Exception:
                logger.warning(...)  # BAD! Hides bugs.
        """
        view_dirs = [
            project_root / "purplex" / "problems_app" / "views",
            project_root / "purplex" / "users_app" / "views",
        ]

        violations = []
        for view_dir in view_dirs:
            if not view_dir.exists():
                continue
            for py_file in view_dir.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                if py_file.name in self._BARE_EXCEPT_ALLOWED:
                    continue
                violations.extend(_find_bare_except_exception(py_file))

        if violations:
            report = "\n".join(
                f"  {v[0]}:{v[1]} - except Exception" for v in violations
            )
            pytest.fail(
                f"Found {len(violations)} bare `except Exception` in view files.\n"
                f"Move error handling to a service *_best_effort() method.\n"
                f"Violations:\n{report}"
            )


def _find_bare_except_exception(file_path: Path) -> list[tuple[str, int]]:
    """Find bare `except Exception:` patterns in a file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                violations.append((str(file_path), node.lineno))
    return violations


# =============================================================================
# SELF-TESTS FOR THE VIOLATION DETECTION LOGIC
# =============================================================================


class TestORMViolationDetection:
    """
    Tests for the ORM violation detection logic itself.

    These ensure the AST visitor correctly identifies patterns.
    """

    def test_detects_simple_objects_call(self):
        """Should detect Model.objects.get() pattern."""
        code = "user = User.objects.get(id=1)"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0][2] == "User"

    def test_detects_objects_filter(self):
        """Should detect Model.objects.filter() pattern."""
        code = "problems = Problem.objects.filter(active=True)"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0][2] == "Problem"

    def test_detects_objects_all(self):
        """Should detect Model.objects.all() pattern."""
        code = "courses = Course.objects.all()"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0][2] == "Course"

    def test_detects_objects_with_select_related(self):
        """Should detect Model.objects with chained methods."""
        code = "subs = Submission.objects.select_related('user').filter()"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0][2] == "Submission"

    def test_ignores_unprotected_models(self):
        """Should ignore models not in protected list."""
        code = "items = SomeOtherModel.objects.all()"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_detects_polymorphic_subclass(self):
        """Should detect polymorphic model subclass access."""
        code = "mcq = McqProblem.objects.get(slug='test')"
        tree = ast.parse(code)
        visitor = ORMUsageVisitor(PROTECTED_MODELS)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0][2] == "McqProblem"

    def test_allows_repository_objects_access(self):
        """Repository files should be allowed to use .objects."""
        file_path = Path("purplex/problems_app/repositories/problem_repository.py")
        assert not should_check_file(file_path)

    def test_checks_view_files(self):
        """View files should be checked."""
        file_path = Path("purplex/problems_app/views/admin_views.py")
        assert should_check_file(file_path)

    def test_skips_migration_files(self):
        """Migration files should not be checked."""
        file_path = Path("purplex/problems_app/migrations/0001_initial.py")
        assert not should_check_file(file_path)

    def test_skips_test_files(self):
        """Test files should not be checked."""
        file_path = Path("tests/unit/test_views.py")
        assert not should_check_file(file_path)

    def test_skips_admin_file(self):
        """Admin.py files should not be checked."""
        file_path = Path("purplex/problems_app/admin.py")
        assert not should_check_file(file_path)

    def test_skips_management_commands(self):
        """Management command files should not be checked."""
        file_path = Path("purplex/problems_app/management/commands/seed_db.py")
        assert not should_check_file(file_path)

    def test_skips_non_python_files(self):
        """Non-Python files should not be checked."""
        file_path = Path("purplex/problems_app/views/README.md")
        assert not should_check_file(file_path)

    def test_handles_syntax_error_gracefully(self, tmp_path: Path):
        """Should handle files with syntax errors gracefully."""
        bad_file = tmp_path / "bad_syntax.py"
        bad_file.write_text("def broken(:\n    pass")

        violations = find_orm_violations(bad_file)
        assert violations == []

    def test_handles_unicode_error_gracefully(self, tmp_path: Path):
        """Should handle files with encoding errors gracefully."""
        bad_file = tmp_path / "bad_encoding.py"
        bad_file.write_bytes(b"\xff\xfe invalid utf-8")

        violations = find_orm_violations(bad_file)
        assert violations == []

    def test_zero_exception_policy_detects_all_violations(self, tmp_path: Path):
        """
        With zero-exception policy, ALL ORM calls should be detected.

        As of 2025-12, we eliminated all exceptions. Every file is now
        checked for ORM violations without any allowed patterns.
        """
        # Even files that previously had exceptions now have violations detected
        view_file = tmp_path / "research_views.py"
        view_file.write_text("x = ProgressSnapshot.objects.all()")

        violations = find_orm_violations(view_file)
        # Should now detect violation - no exceptions exist
        assert len(violations) == 1
        assert violations[0].model == "ProgressSnapshot"

    def test_all_protected_models_detected(self, tmp_path: Path):
        """All protected models should be detected without exceptions."""
        view_file = tmp_path / "any_view.py"
        view_file.write_text("x = User.objects.get(id=1)")

        violations = find_orm_violations(view_file)
        assert len(violations) == 1
        assert violations[0].model == "User"
