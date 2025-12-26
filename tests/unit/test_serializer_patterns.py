"""
Architectural tests to enforce serializer best practices.

These tests verify that:
- Model serializers have proper Meta class configuration
- Serializers don't contain business logic (should be in services)
- create/update methods delegate to services when complex

WHY SERIALIZER PATTERNS?
========================
Serializers should be simple:
1. Data validation and transformation
2. Field definitions and read_only_fields
3. Simple create/update for basic CRUD

Complex logic belongs in services because:
- Services can be unit tested independently
- Services can be reused across endpoints
- Serializers stay focused on data shape

Run with: pytest tests/unit/test_serializer_patterns.py -v
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

# Serializer files to check
SERIALIZER_FILES = [
    "purplex/problems_app/serializers.py",
    "purplex/users_app/serializers.py",
]

# Classes that extend ModelSerializer - these need Meta class
MODEL_SERIALIZER_BASES = {
    "ModelSerializer",
    "HyperlinkedModelSerializer",
}

# Maximum allowed lines in create/update methods before it's "too complex"
MAX_CREATE_UPDATE_LINES = 20

# Known exceptions - serializers with complex but documented create/update methods
# These use transaction.atomic() and service layer calls which is acceptable
COMPLEX_CREATE_EXCEPTIONS = {
    # Admin problem serializer handles polymorphic type creation/update
    # Uses AdminProblemService for database operations
    "AdminProblemSerializer",
    # Course serializer has problem set management logic
    # Uses AdminProblemService for database operations
    "CourseCreateUpdateSerializer",
}


class SerializerIssue(NamedTuple):
    """An issue found in a serializer."""

    file: str
    class_name: str
    line: int
    issue: str


# =============================================================================
# AST VISITORS
# =============================================================================


class SerializerAnalyzer(ast.NodeVisitor):
    """
    AST visitor to analyze serializer class definitions.

    Checks for:
    - ModelSerializers without Meta class
    - Complex create/update methods
    - Business logic indicators (too many conditionals)
    """

    def __init__(self):
        self.issues: list[tuple[str, int, str]] = []
        self._current_class: str | None = None
        self._current_class_bases: set[str] = set()
        self._current_class_has_meta = False
        self._current_class_line = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze serializer class definitions."""
        self._current_class = node.name
        self._current_class_line = node.lineno
        self._current_class_has_meta = False

        # Get base class names
        self._current_class_bases = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                self._current_class_bases.add(base.id)
            elif isinstance(base, ast.Attribute):
                self._current_class_bases.add(base.attr)

        # Visit children to find Meta class and methods
        for child in node.body:
            if isinstance(child, ast.ClassDef) and child.name == "Meta":
                self._current_class_has_meta = True
                self._check_meta_class(child)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_method(child)

        # Check if ModelSerializer has Meta
        is_model_serializer = bool(self._current_class_bases & MODEL_SERIALIZER_BASES)
        if is_model_serializer and not self._current_class_has_meta:
            self.issues.append(
                (
                    self._current_class,
                    self._current_class_line,
                    f"ModelSerializer '{self._current_class}' missing Meta class",
                )
            )

        self._current_class = None

    def _check_meta_class(self, node: ast.ClassDef) -> None:
        """Check Meta class has recommended attributes."""
        has_fields = False

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "fields":
                            has_fields = True

        # Warning: ModelSerializer without fields definition
        if not has_fields and self._current_class_bases & MODEL_SERIALIZER_BASES:
            # This is common when using __all__ so we don't flag it
            pass

    def _check_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check create/update methods for complexity."""
        if node.name not in ("create", "update"):
            return

        # Skip if in exceptions
        if self._current_class in COMPLEX_CREATE_EXCEPTIONS:
            return

        # Count lines (rough complexity measure)
        method_lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        if method_lines > MAX_CREATE_UPDATE_LINES:
            self.issues.append(
                (
                    self._current_class,
                    node.lineno,
                    f"Method '{node.name}' has {method_lines} lines "
                    f"(max {MAX_CREATE_UPDATE_LINES}). Consider moving logic to service.",
                )
            )

        # Count conditionals (if statements)
        conditional_count = sum(
            1 for _ in ast.walk(node) if isinstance(_, (ast.If, ast.IfExp))
        )
        if conditional_count > 3:
            self.issues.append(
                (
                    self._current_class,
                    node.lineno,
                    f"Method '{node.name}' has {conditional_count} conditionals. "
                    f"Complex logic should be in services.",
                )
            )


class FieldDefinitionChecker(ast.NodeVisitor):
    """Check that serializers use proper field definitions."""

    def __init__(self):
        self.issues: list[tuple[str, int, str]] = []
        self._current_class: str | None = None
        self._current_class_line = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class for field definitions."""
        # Check if it's a serializer (ends with Serializer)
        if not node.name.endswith("Serializer"):
            return

        self._current_class = node.name
        self._current_class_line = node.lineno

        # Visit to check assignments
        self.generic_visit(node)

        self._current_class = None


# =============================================================================
# FILE SCANNING UTILITIES
# =============================================================================


def get_serializer_files(project_root: Path) -> list[Path]:
    """Get all serializer files."""
    files = []
    for file_path in SERIALIZER_FILES:
        full_path = project_root / file_path
        if full_path.exists():
            files.append(full_path)
    return files


def analyze_serializer_file(file_path: Path) -> list[SerializerIssue]:
    """Analyze a serializer file for issues."""
    issues = []

    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return issues

    analyzer = SerializerAnalyzer()
    analyzer.visit(tree)

    for class_name, line, issue in analyzer.issues:
        issues.append(
            SerializerIssue(
                file=str(file_path), class_name=class_name, line=line, issue=issue
            )
        )

    return issues


def count_serializer_classes(file_path: Path) -> int:
    """Count the number of serializer classes in a file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Serializer"):
            count += 1
    return count


# =============================================================================
# SERIALIZER PATTERN TESTS
# =============================================================================


@pytest.mark.architecture
class TestSerializerPatterns:
    """
    Tests to enforce serializer best practices.

    These tests ensure serializers are focused on data transformation,
    not business logic.
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_model_serializers_have_meta_class(self, project_root: Path):
        """
        ModelSerializers should have a Meta class defined.

        The Meta class specifies:
        - model: The model to serialize
        - fields: Which fields to include
        - read_only_fields: Fields that can't be set

        Missing Meta class often indicates incomplete implementation.
        """
        serializer_files = get_serializer_files(project_root)
        missing_meta = []

        for file_path in serializer_files:
            issues = analyze_serializer_file(file_path)
            for issue in issues:
                if "missing Meta class" in issue.issue:
                    missing_meta.append(
                        f"  {issue.file}:{issue.line} - {issue.class_name}"
                    )

        if missing_meta:
            pytest.fail(
                f"Found {len(missing_meta)} ModelSerializers without Meta class:\n"
                + "\n".join(missing_meta)
                + "\n\nTo fix: Add Meta class with model and fields attributes."
            )

    def test_create_update_methods_are_simple(self, project_root: Path):
        """
        create() and update() methods should be simple.

        Complex logic should be moved to services:
        - Better testability
        - Reusable across endpoints
        - Separation of concerns

        Thresholds:
        - Max {MAX_CREATE_UPDATE_LINES} lines
        - Max 3 conditional statements
        """
        serializer_files = get_serializer_files(project_root)
        complex_methods = []

        for file_path in serializer_files:
            issues = analyze_serializer_file(file_path)
            for issue in issues:
                if "Method" in issue.issue:
                    complex_methods.append(
                        f"  {issue.file}:{issue.line} - {issue.class_name}: {issue.issue}"
                    )

        if complex_methods:
            pytest.fail(
                f"Found {len(complex_methods)} complex serializer methods:\n"
                + "\n".join(complex_methods)
                + "\n\nTo fix: Move complex logic to a service class."
            )

    def test_serializer_files_exist(self, project_root: Path):
        """
        Verify that expected serializer files exist.

        This is a sanity check that the test configuration is correct.
        """
        for file_path in SERIALIZER_FILES:
            full_path = project_root / file_path
            assert full_path.exists(), f"Serializer file not found: {file_path}"


# =============================================================================
# SELF-TESTS
# =============================================================================


class TestSerializerPatternLogic:
    """Tests for the serializer pattern detection logic."""

    def test_detects_missing_meta(self):
        """Should detect ModelSerializer without Meta."""
        code = """
class UserSerializer(ModelSerializer):
    name = CharField()
"""
        tree = ast.parse(code)
        analyzer = SerializerAnalyzer()
        analyzer.visit(tree)

        assert len(analyzer.issues) == 1
        assert "missing Meta class" in analyzer.issues[0][2]

    def test_ignores_serializer_with_meta(self):
        """Should not flag serializer with Meta class."""
        code = """
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name']
"""
        tree = ast.parse(code)
        analyzer = SerializerAnalyzer()
        analyzer.visit(tree)

        # No issues - has Meta
        meta_issues = [i for i in analyzer.issues if "missing Meta" in i[2]]
        assert len(meta_issues) == 0

    def test_detects_complex_create(self):
        """Should detect complex create method."""
        # Create a method with > 20 lines
        method_body = "\n".join([f"        x = {i}" for i in range(25)])
        code = f"""
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id']

    def create(self, validated_data):
{method_body}
        return validated_data
"""
        tree = ast.parse(code)
        analyzer = SerializerAnalyzer()
        analyzer.visit(tree)

        complex_issues = [i for i in analyzer.issues if "lines" in i[2]]
        assert len(complex_issues) == 1

    def test_detects_too_many_conditionals(self):
        """Should detect create with too many if statements."""
        code = """
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id']

    def create(self, validated_data):
        if a:
            pass
        if b:
            pass
        if c:
            pass
        if d:
            pass
        return validated_data
"""
        tree = ast.parse(code)
        analyzer = SerializerAnalyzer()
        analyzer.visit(tree)

        conditional_issues = [i for i in analyzer.issues if "conditionals" in i[2]]
        assert len(conditional_issues) == 1

    def test_ignores_non_serializer_classes(self):
        """Should not check classes that don't end with Serializer."""
        code = """
class SomeService(BaseService):
    class Meta:
        pass
"""
        tree = ast.parse(code)
        analyzer = SerializerAnalyzer()
        analyzer.visit(tree)

        # Analyzer only checks serializer classes based on inheritance
        assert len(analyzer.issues) == 0
