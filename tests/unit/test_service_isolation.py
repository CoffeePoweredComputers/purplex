"""
Architectural tests to enforce service layer isolation.

These tests verify that:
- Services do not import views (proper dependency direction)
- Services use TYPE_CHECKING for model imports where possible
- Services have no circular dependencies

WHY SERVICE ISOLATION?
======================
Services contain business logic and should:
1. Not depend on views (views depend on services, not vice versa)
2. Not create circular import issues
3. Import models carefully to avoid import-time database access

Run with: pytest tests/unit/test_service_isolation.py -v
Run architecture tests only: pytest -m architecture
"""

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# Mark all tests in this module as unit tests and architecture tests
pytestmark = [pytest.mark.unit, pytest.mark.architecture]


# =============================================================================
# CONFIGURATION
# =============================================================================

# Service directories to check
SERVICE_DIRECTORIES = [
    "purplex/problems_app/services",
    "purplex/users_app/services",
    "purplex/submissions",
]

# Patterns that indicate a view import
VIEW_IMPORT_PATTERNS = [
    "_views",
    ".views",
    "from views",
]

# Model module patterns - imports from these should ideally be in TYPE_CHECKING
MODEL_MODULES = [
    "purplex.problems_app.models",
    "purplex.users_app.models",
    "purplex.submissions.models",
]

# Services that legitimately need runtime model imports
# (e.g., for isinstance checks, direct model instantiation, ORM queries)
# NOTE: These are documented exceptions - each should have a clear reason
ALLOWED_RUNTIME_MODEL_IMPORTS = {
    # Pipeline tasks need models at runtime for type dispatch
    "pipeline.py": {"Submission", "McqProblem", "Problem"},
    # Grading service needs model access
    "grading_service.py": {"Submission", "CodeVariation"},
    # Services that validate/create model instances
    "submission_validation_service.py": {"Course"},
    # Progress tracking - needs direct model access for transactions
    "progress_service.py": {
        "UserProgress",
        "UserProblemSetProgress",
        "ProgressSnapshot",
        "Submission",
    },
    # Analytics services - need models for complex aggregation queries
    "instructor_analytics_service.py": {
        "Problem",
        "Course",
        "UserProgress",
        "UserProblemSetProgress",
        "ProgressSnapshot",
        "CourseEnrollment",
        "Submission",
        "HintActivation",
        "TestExecution",
    },
    # Export services - need models for bulk data export
    "research_export_service.py": {
        "ProblemSet",
        "Course",
        "UserProgress",
        "ProgressSnapshot",
        "Submission",
        "HintActivation",
    },
    "course_export_service.py": {
        "Course",
        "UserProgress",
        "CourseEnrollment",
        "HintActivation",
    },
    # Hint service - tracks hint activations
    "hint_service.py": {"HintActivation"},
    # User service - needs profile and submission access
    "user_service.py": {"UserProfile", "Submission"},
    # Authentication service - works with user profiles
    "authentication_service.py": {"UserProfile"},
    # Submissions service - core submission handling
    "services.py": {"ProblemHint"},
    # Repository may need related models for prefetch
    "submission_repository.py": {"UserProgress"},
    # Activity event service - direct ORM for append-only event recording
    "activity_event_service.py": {"ActivityEvent"},
    # Data deletion service - needs models for anonymization/deletion pipeline
    "data_deletion_service.py": {
        "HintActivation",
        "SegmentationAnalysis",
        "Submission",
        "SubmissionFeedback",
        "ActivityEvent",
        "CourseEnrollment",
        "ProgressSnapshot",
        "UserProblemSetProgress",
        "UserProgress",
        "AgeVerification",
        "AuditAction",
        "DataAccessAuditLog",
        "DataPrincipalNominee",
        "UserConsent",
        "UserProfile",
    },
    # Data export service - needs models for GDPR Art. 15 export
    "data_export_service.py": {
        "Submission",
        "UserProgress",
        "CourseEnrollment",
        "HintActivation",
        "SegmentationAnalysis",
        "ActivityEvent",
    },
}


class ViewImportViolation(NamedTuple):
    """A service importing from views."""

    file: str
    line: int
    import_text: str


class CircularDependency(NamedTuple):
    """A circular service dependency."""

    cycle: tuple[str, ...]


# =============================================================================
# AST VISITORS
# =============================================================================


class ViewImportVisitor(ast.NodeVisitor):
    """AST visitor to find view imports in service files."""

    def __init__(self):
        self.violations: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Check simple imports: import foo.views"""
        for alias in node.names:
            if any(pattern in alias.name for pattern in VIEW_IMPORT_PATTERNS):
                self.violations.append((node.lineno, f"import {alias.name}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from imports: from foo.views import bar"""
        if node.module:
            if any(pattern in node.module for pattern in VIEW_IMPORT_PATTERNS):
                names = ", ".join(alias.name for alias in node.names)
                self.violations.append(
                    (node.lineno, f"from {node.module} import {names}")
                )
        self.generic_visit(node)


class ModelImportVisitor(ast.NodeVisitor):
    """
    AST visitor to check if model imports are in TYPE_CHECKING blocks.

    We want models imported like:
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from purplex.problems_app.models import Problem

    Not like:
        from purplex.problems_app.models import Problem  # at module level
    """

    def __init__(self):
        self.runtime_model_imports: list[tuple[int, str]] = []
        self._in_type_checking = False

    def visit_If(self, node: ast.If) -> None:
        """Track if we're inside a TYPE_CHECKING block."""
        # Check if this is `if TYPE_CHECKING:` or `if typing.TYPE_CHECKING:`
        is_type_checking = False
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            is_type_checking = True
        elif isinstance(node.test, ast.Attribute) and node.test.attr == "TYPE_CHECKING":
            is_type_checking = True

        if is_type_checking:
            # Don't visit the body - these imports are fine
            pass
        else:
            self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from imports for model imports outside TYPE_CHECKING."""
        if self._in_type_checking:
            return

        if node.module and any(mod in node.module for mod in MODEL_MODULES):
            names = [alias.name for alias in node.names]
            for name in names:
                self.runtime_model_imports.append((node.lineno, name))

        self.generic_visit(node)


class ServiceImportCollector(ast.NodeVisitor):
    """Collect all service imports from a service file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.imports: set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Collect imports from other services."""
        if node.module and "services" in node.module:
            self.imports.add(node.module)
        self.generic_visit(node)


# =============================================================================
# FILE SCANNING UTILITIES
# =============================================================================


def get_service_files(project_root: Path) -> list[Path]:
    """Get all service Python files."""
    service_files = []
    for dir_path in SERVICE_DIRECTORIES:
        service_dir = project_root / dir_path
        if service_dir.exists():
            for py_file in service_dir.rglob("*.py"):
                if py_file.name != "__init__.py":
                    service_files.append(py_file)
    return service_files


def find_view_imports(file_path: Path) -> list[ViewImportViolation]:
    """Find any view imports in a service file."""
    violations = []
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    visitor = ViewImportVisitor()
    visitor.visit(tree)

    for line, import_text in visitor.violations:
        violations.append(
            ViewImportViolation(file=str(file_path), line=line, import_text=import_text)
        )

    return violations


def find_runtime_model_imports(file_path: Path) -> list[tuple[int, str]]:
    """
    Find model imports that are NOT in TYPE_CHECKING blocks.

    Note: This is informational - not all runtime model imports are wrong,
    but they should be minimized and documented.
    """
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = ModelImportVisitor()
    visitor.visit(tree)

    # Filter out allowed imports for this file
    file_name = file_path.name
    allowed = ALLOWED_RUNTIME_MODEL_IMPORTS.get(file_name, set())

    return [
        (line, name)
        for line, name in visitor.runtime_model_imports
        if name not in allowed
    ]


def build_service_dependency_graph(
    project_root: Path,
) -> dict[str, set[str]]:
    """Build a graph of service-to-service dependencies."""
    graph: dict[str, set[str]] = {}

    for service_file in get_service_files(project_root):
        try:
            source = service_file.read_text()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        collector = ServiceImportCollector(service_file)
        collector.visit(tree)

        # Use relative path as key
        rel_path = str(service_file.relative_to(project_root))
        graph[rel_path] = collector.imports

    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """
    Find cycles in the dependency graph using DFS.

    Returns list of cycles found.
    """
    cycles = []
    visited = set()
    rec_stack = []

    def dfs(node: str, path: list[str]) -> None:
        if node in rec_stack:
            # Found cycle
            cycle_start = rec_stack.index(node)
            cycle = tuple(rec_stack[cycle_start:] + [node])
            cycles.append(cycle)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.append(node)

        for neighbor in graph.get(node, set()):
            # Convert module path to file path for lookup
            for key in graph:
                if (
                    neighbor in key
                    or key.replace("/", ".").replace(".py", "") in neighbor
                ):
                    dfs(key, path + [node])

        rec_stack.pop()

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


# =============================================================================
# SERVICE ISOLATION TESTS
# =============================================================================


@pytest.mark.architecture
class TestServiceIsolation:
    """
    Tests to enforce service layer isolation.

    These tests ensure proper dependency direction:
    - Views -> Services -> Repositories
    - Services should NOT import from views
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_services_do_not_import_views(self, project_root: Path):
        """
        Services should never import from views.

        The dependency direction should be: Views -> Services -> Repositories
        If a service needs something from a view, it's a sign of architectural issues.
        """
        service_files = get_service_files(project_root)
        all_violations = []

        for service_file in service_files:
            violations = find_view_imports(service_file)
            all_violations.extend(violations)

        if all_violations:
            violation_report = "\n".join(
                f"  {v.file}:{v.line} - {v.import_text}" for v in all_violations
            )
            pytest.fail(
                f"Found {len(all_violations)} view imports in service files.\n"
                f"Services should not depend on views.\n"
                f"Violations:\n{violation_report}\n\n"
                f"To fix: Move shared code to services or utilities."
            )

    def test_runtime_model_imports_are_documented(self, project_root: Path):
        """
        Model imports outside TYPE_CHECKING should be documented.

        While not strictly forbidden, runtime model imports can cause:
        - Import-time database queries
        - Circular import issues
        - Harder to mock in tests

        This test ensures all runtime model imports are explicitly allowed.
        """
        service_files = get_service_files(project_root)
        undocumented_imports = []

        for service_file in service_files:
            imports = find_runtime_model_imports(service_file)
            for line, name in imports:
                undocumented_imports.append(f"  {service_file}:{line} - {name}")

        if undocumented_imports:
            pytest.fail(
                f"Found {len(undocumented_imports)} undocumented runtime model imports.\n"
                f"These imports are outside TYPE_CHECKING blocks:\n"
                + "\n".join(undocumented_imports)
                + "\n\nTo fix: Either move import to TYPE_CHECKING block, or add to "
                "ALLOWED_RUNTIME_MODEL_IMPORTS in test_service_isolation.py"
            )

    def test_no_circular_service_dependencies(self, project_root: Path):
        """
        Services should not have circular dependencies.

        Circular dependencies make code hard to understand and test.
        If A depends on B and B depends on A, consider:
        - Moving shared logic to a new service
        - Using dependency injection
        - Restructuring the code
        """
        graph = build_service_dependency_graph(project_root)
        cycles = find_cycles(graph)

        if cycles:
            cycle_report = "\n".join(f"  {' -> '.join(cycle)}" for cycle in cycles)
            pytest.fail(
                f"Found {len(cycles)} circular service dependencies:\n"
                f"{cycle_report}\n\n"
                f"To fix: Extract shared logic to a new service or utility."
            )


# =============================================================================
# SELF-TESTS
# =============================================================================


class TestServiceIsolationLogic:
    """Tests for the service isolation detection logic."""

    def test_detects_view_import(self):
        """Should detect imports from views modules."""
        code = "from purplex.problems_app.views import admin_views"
        tree = ast.parse(code)
        visitor = ViewImportVisitor()
        visitor.visit(tree)

        assert len(visitor.violations) == 1

    def test_detects_views_in_module_path(self):
        """Should detect when 'views' is in the module path."""
        code = "from purplex.problems_app.views.admin_views import something"
        tree = ast.parse(code)
        visitor = ViewImportVisitor()
        visitor.visit(tree)

        assert len(visitor.violations) == 1

    def test_ignores_non_view_imports(self):
        """Should not flag non-view imports."""
        code = "from purplex.problems_app.services import some_service"
        tree = ast.parse(code)
        visitor = ViewImportVisitor()
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_detects_runtime_model_import(self):
        """Should detect model imports at module level."""
        code = "from purplex.problems_app.models import Problem"
        tree = ast.parse(code)
        visitor = ModelImportVisitor()
        visitor.visit(tree)

        assert len(visitor.runtime_model_imports) == 1

    def test_ignores_type_checking_model_import(self):
        """Should not flag model imports inside TYPE_CHECKING."""
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from purplex.problems_app.models import Problem
"""
        tree = ast.parse(code)
        visitor = ModelImportVisitor()
        visitor.visit(tree)

        # TYPE_CHECKING imports should not be collected
        assert len(visitor.runtime_model_imports) == 0
