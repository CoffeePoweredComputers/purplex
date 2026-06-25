"""
Architectural test: test-case data is normalized exactly once.

``TestCase.inputs`` and ``TestCase.expected_output`` are ``JSONField``s. Django
deserializes them to native Python objects on read, so a stored string ``"123"``
comes back as the str ``"123"`` — that IS the final value, not JSON text awaiting
a parse.

Calling ``json.loads()`` on such a value a second time is a *double-decode* that
silently corrupts legitimately-string outputs (``"123" -> 123``, ``"true" ->
True``, ``"[1,2]" -> [1,2]``). When that re-decode lives in the student grading
path but not the instructor authoring path, the two panels disagree: a test case
passes in authoring and fails for students (see
``tests/integration/test_testcase_string_output_grading.py``). This bug shipped
twice; this test exists so it cannot ship a third time.

RULE: no ``json.loads(...)`` on a test-case ``inputs``/``expected_output`` value
anywhere downstream of the canonical loader
(``TestCaseService.get_test_cases_for_testing``). Consume those values as-is.

This mirrors the AST approach in ``tests/unit/test_repository_pattern.py`` (method-
call detection, not import detection). Run with: ``pytest -m architecture``.
"""

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.architecture]


class ReDecodeViolation(NamedTuple):
    """A json.loads() applied to a test-case JSONField value."""

    file: str
    line: int
    code: str


# =============================================================================
# CONFIGURATION
# =============================================================================

# Directories whose code consumes test cases for execution/grading. The canonical
# loader lives in services; these are the layers that must trust its output.
SCAN_DIRS = [
    "purplex/problems_app/tasks",
    "purplex/problems_app/services",
    "purplex/problems_app/handlers",
    "purplex/problems_app/views",
    "purplex/submissions",
]

# Substrings in the (unparsed) json.loads argument that identify a test-case
# field access. ``expected_output`` is unique enough to match bare; ``inputs`` is
# only matched as a field access to avoid catching unrelated variables.
TESTCASE_FIELD_MARKERS = (
    "expected_output",
    '["inputs"]',
    "['inputs']",
    ".inputs",
)

# Documented exceptions. Key: filename, Value: set of arg-substrings allowed.
# There are intentionally NONE. Do NOT add files here to silence a failure —
# remove the json.loads instead. The JSONField already gave you the value.
EXCEPTIONS: dict[str, set[str]] = {}


class ReDecodeVisitor(ast.NodeVisitor):
    """Detect ``json.loads(<...inputs/expected_output...>)`` calls."""

    def __init__(self) -> None:
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_json_loads(node.func) and node.args:
            arg_src = ast.unparse(node.args[0])
            if any(marker in arg_src for marker in TESTCASE_FIELD_MARKERS):
                self.violations.append((node.lineno, f"json.loads({arg_src})"))
        self.generic_visit(node)

    @staticmethod
    def _is_json_loads(func: ast.expr) -> bool:
        # json.loads(...)
        if isinstance(func, ast.Attribute) and func.attr == "loads":
            return True
        # loads(...)  (from json import loads)
        return isinstance(func, ast.Name) and func.id == "loads"


def find_redecode_violations(file_path: Path) -> list[ReDecodeViolation]:
    try:
        tree = ast.parse(file_path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = ReDecodeVisitor()
    visitor.visit(tree)

    allowed = EXCEPTIONS.get(file_path.name, set())
    return [
        ReDecodeViolation(file=str(file_path), line=line, code=code)
        for line, code in visitor.violations
        if not any(pattern in code for pattern in allowed)
    ]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scan_files() -> list[Path]:
    root = _project_root()
    files: list[Path] = []
    for rel in SCAN_DIRS:
        base = root / rel
        if base.exists():
            files.extend(p for p in base.rglob("*.py") if p.name != "__init__.py")
    return files


class TestTestCaseNotReDecoded:
    """Enforce single-normalization of test-case data."""

    def test_no_json_loads_on_testcase_fields(self):
        violations: list[ReDecodeViolation] = []
        for py_file in _scan_files():
            violations.extend(find_redecode_violations(py_file))

        if violations:
            root = _project_root()
            report = "\n".join(
                f"  {Path(v.file).relative_to(root)}:{v.line} — {v.code}"
                for v in violations
            )
            pytest.fail(
                "json.loads() called on test-case inputs/expected_output. These "
                "are JSONField values — already deserialized by Django. Re-decoding "
                "corrupts string outputs and diverges student grading from instructor "
                "authoring. Use the value from "
                "TestCaseService.get_test_cases_for_testing() as-is.\n\n"
                f"{report}"
            )

    def test_detector_catches_a_known_violation(self):
        """Positive control: the visitor must actually flag the bug pattern,
        so this guard can't silently rot into a no-op."""
        source = 'import json\njson.loads(tc["expected_output"])\n'
        visitor = ReDecodeVisitor()
        visitor.visit(ast.parse(source))
        assert visitor.violations, "detector failed to flag a known re-decode"
