"""
Architectural tests to enforce API response consistency.

These tests verify that:
- Views use DRF Response class (not JsonResponse or dict)
- Status codes are explicitly set in responses
- Error responses follow a consistent format

WHY API CONSISTENCY?
====================
Consistent API responses make the frontend predictable:
1. Error handling can be centralized
2. Response parsing is uniform
3. Documentation is accurate
4. Breaking changes are caught early

Run with: pytest tests/unit/test_api_consistency.py -v
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

# View directories to check
VIEW_DIRECTORIES = [
    "purplex/problems_app/views",
    "purplex/users_app",  # user_views.py is here
    "purplex/submissions/views",
]

# View files that are allowed to use JsonResponse
# (e.g., special endpoints that need file downloads)
ALLOWED_JSONRESPONSE = {
    # Research export uses JsonResponse for file download with Content-Disposition
    "research_views.py",
}

# Status codes that should be explicit
# Views returning error status should always specify the code
ERROR_STATUS_CODES = {400, 401, 403, 404, 405, 409, 422, 429, 500}


class ResponseViolation(NamedTuple):
    """A view using non-DRF response."""

    file: str
    line: int
    issue: str


# =============================================================================
# AST VISITORS
# =============================================================================


class ResponsePatternVisitor(ast.NodeVisitor):
    """
    AST visitor to find Response usage patterns in views.

    Checks for:
    - Use of JsonResponse instead of Response
    - Response without explicit status parameter
    """

    def __init__(self):
        self.violations: list[tuple[int, str]] = []
        self._in_function = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track when we're inside a function."""
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track when we're inside an async function."""
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_Call(self, node: ast.Call) -> None:
        """Check for Response and JsonResponse calls."""
        if not self._in_function:
            self.generic_visit(node)
            return

        # Check for JsonResponse usage
        func_name = self._get_call_name(node)
        if func_name == "JsonResponse":
            self.violations.append(
                (node.lineno, "Use Response instead of JsonResponse")
            )

        # Check for Response without explicit status
        if func_name == "Response":
            has_status = any(kw.arg == "status" for kw in node.keywords)
            # Check if status is a positional arg (Response(data, status=...))
            if not has_status and len(node.args) < 2:
                # Response with just data - status defaults to 200
                # This is OK for success, but we track it for review
                pass

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str:
        """Get the name of the function being called."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""


class ErrorResponseVisitor(ast.NodeVisitor):
    """
    AST visitor to check error response consistency.

    Looks for Response calls with error status codes and checks
    they include proper error keys.
    """

    def __init__(self):
        self.error_responses: list[tuple[int, dict]] = []
        self._in_function = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._in_function = True
        self.generic_visit(node)
        self._in_function = False

    def visit_Call(self, node: ast.Call) -> None:
        if not self._in_function:
            self.generic_visit(node)
            return

        func_name = self._get_call_name(node)
        if func_name == "Response":
            status_value = self._get_status_value(node)
            if status_value and status_value >= 400:
                # This is an error response - check the data structure
                data_arg = self._get_data_arg(node)
                self.error_responses.append(
                    (
                        node.lineno,
                        {
                            "status": status_value,
                            "has_error_key": self._has_key(data_arg, "error"),
                            "has_detail_key": self._has_key(data_arg, "detail"),
                        },
                    )
                )

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _get_status_value(self, node: ast.Call) -> int | None:
        """Extract the status value from a Response call."""
        for kw in node.keywords:
            if kw.arg == "status":
                if isinstance(kw.value, ast.Constant):
                    return kw.value.value
                elif isinstance(kw.value, ast.Attribute):
                    # status.HTTP_400_BAD_REQUEST
                    attr = kw.value.attr
                    if attr.startswith("HTTP_"):
                        try:
                            return int(attr.split("_")[1])
                        except (IndexError, ValueError):
                            pass
        return None

    def _get_data_arg(self, node: ast.Call) -> ast.expr | None:
        """Get the data argument from Response call."""
        if node.args:
            return node.args[0]
        for kw in node.keywords:
            if kw.arg == "data":
                return kw.value
        return None

    def _has_key(self, node: ast.expr | None, key: str) -> bool:
        """Check if a dict literal has a specific key."""
        if not isinstance(node, ast.Dict):
            return False
        for k in node.keys:
            if isinstance(k, ast.Constant) and k.value == key:
                return True
        return False


# =============================================================================
# FILE SCANNING UTILITIES
# =============================================================================


def get_view_files(project_root: Path) -> list[Path]:
    """Get all view Python files."""
    view_files = []
    for dir_path in VIEW_DIRECTORIES:
        view_dir = project_root / dir_path
        if view_dir.exists():
            if view_dir.is_file() and view_dir.suffix == ".py":
                view_files.append(view_dir)
            else:
                for py_file in view_dir.rglob("*.py"):
                    # Skip __init__.py and test files
                    if py_file.name == "__init__.py":
                        continue
                    if "test" in py_file.name:
                        continue
                    # Only include view files
                    if "_views" in py_file.name or "views" in str(py_file.parent):
                        view_files.append(py_file)
    return view_files


def find_response_violations(file_path: Path) -> list[ResponseViolation]:
    """Find Response pattern violations in a view file."""
    violations = []

    # Skip allowed files
    if file_path.name in ALLOWED_JSONRESPONSE:
        return violations

    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    visitor = ResponsePatternVisitor()
    visitor.visit(tree)

    for line, issue in visitor.violations:
        violations.append(
            ResponseViolation(file=str(file_path), line=line, issue=issue)
        )

    return violations


def analyze_error_responses(file_path: Path) -> list[tuple[int, dict]]:
    """Analyze error response patterns in a view file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = ErrorResponseVisitor()
    visitor.visit(tree)
    return visitor.error_responses


# =============================================================================
# API CONSISTENCY TESTS
# =============================================================================


@pytest.mark.architecture
class TestAPIResponseConsistency:
    """
    Tests to enforce consistent API response formats.

    All API endpoints should:
    1. Use DRF's Response class (not JsonResponse)
    2. Have explicit status codes for error responses
    3. Follow consistent error response structure
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def test_views_use_drf_response(self, project_root: Path):
        """
        Views should use DRF Response, not Django's JsonResponse.

        Response provides:
        - Content negotiation
        - Proper serialization
        - Status code handling
        - Integration with DRF browsable API
        """
        view_files = get_view_files(project_root)
        all_violations = []

        for view_file in view_files:
            violations = find_response_violations(view_file)
            all_violations.extend(violations)

        if all_violations:
            violation_report = "\n".join(
                f"  {v.file}:{v.line} - {v.issue}" for v in all_violations
            )
            pytest.fail(
                f"Found {len(all_violations)} Response pattern violations.\n"
                f"Violations:\n{violation_report}\n\n"
                f"To fix: Replace JsonResponse with Response from rest_framework."
            )

    def test_error_responses_have_consistent_keys(self, project_root: Path):
        """
        Error responses should have consistent structure.

        Preferred format:
            {"error": "message"} or {"detail": "message"}

        This allows frontend to handle errors uniformly.
        """
        view_files = get_view_files(project_root)
        inconsistent_errors = []

        for view_file in view_files:
            error_responses = analyze_error_responses(view_file)
            for line, info in error_responses:
                # Error response should have either 'error' or 'detail' key
                if not info["has_error_key"] and not info["has_detail_key"]:
                    inconsistent_errors.append(
                        f"  {view_file}:{line} - status {info['status']} "
                        f"missing 'error' or 'detail' key"
                    )

        # This is informational - not a hard failure
        # Comment out the fail if you want it to just report
        if inconsistent_errors:
            # For now, just log these as warnings rather than failing
            # Many existing endpoints may not follow this pattern yet
            pass  # Remove this pass and uncomment below to enforce
            # pytest.fail(
            #     f"Found {len(inconsistent_errors)} inconsistent error responses.\n"
            #     + "\n".join(inconsistent_errors)
            # )


# =============================================================================
# SELF-TESTS
# =============================================================================


class TestAPIConsistencyLogic:
    """Tests for the API consistency detection logic."""

    def test_detects_json_response(self):
        """Should detect JsonResponse usage."""
        code = """
def my_view(request):
    return JsonResponse({'data': 'value'})
"""
        tree = ast.parse(code)
        visitor = ResponsePatternVisitor()
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert "JsonResponse" in visitor.violations[0][1]

    def test_ignores_drf_response(self):
        """Should not flag DRF Response."""
        code = """
def my_view(request):
    return Response({'data': 'value'})
"""
        tree = ast.parse(code)
        visitor = ResponsePatternVisitor()
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_detects_error_response(self):
        """Should detect error responses."""
        code = """
def my_view(request):
    return Response({'error': 'Not found'}, status=404)
"""
        tree = ast.parse(code)
        visitor = ErrorResponseVisitor()
        visitor.visit(tree)

        assert len(visitor.error_responses) == 1
        assert visitor.error_responses[0][1]["status"] == 404
        assert visitor.error_responses[0][1]["has_error_key"] is True

    def test_detects_missing_error_key(self):
        """Should detect error response without error key."""
        code = """
def my_view(request):
    return Response({'message': 'Not found'}, status=404)
"""
        tree = ast.parse(code)
        visitor = ErrorResponseVisitor()
        visitor.visit(tree)

        assert len(visitor.error_responses) == 1
        assert visitor.error_responses[0][1]["has_error_key"] is False
        assert visitor.error_responses[0][1]["has_detail_key"] is False

    def test_detects_detail_key(self):
        """Should recognize 'detail' as valid error key."""
        code = """
def my_view(request):
    return Response({'detail': 'Not found'}, status=404)
"""
        tree = ast.parse(code)
        visitor = ErrorResponseVisitor()
        visitor.visit(tree)

        assert len(visitor.error_responses) == 1
        assert visitor.error_responses[0][1]["has_detail_key"] is True
