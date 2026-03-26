"""
Architectural tests to enforce test code conventions.

These tests verify that:
- Tests use Factory Boy factories instead of Model.objects.create()
- Test files follow project naming and marking conventions

Run with: pytest tests/unit/test_test_patterns.py -v
Run architecture tests only: pytest -m architecture
"""

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.architecture]

# Files that are allowed to use objects.create().
# Pre-existing files are grandfathered in — do NOT add new files here.
# Fix the violation by using factories instead.
ALLOWED_FILES = {
    "conftest.py",
    "test_test_patterns.py",
    # Pre-existing (grandfathered) — tracked for cleanup
    "test_admin_problem_crud.py",
    "test_comprehension_level_normalization.py",
    "test_contract_fixes.py",
    "test_course_problem_set_models.py",
    "test_course_service.py",
    "test_due_date_contract.py",
    "test_f_expression_bug.py",
    "test_hint_api.py",
    "test_hint_integration.py",
    "test_hint_models.py",
    "test_on_delete_behavior.py",
    "test_polymorphic_comprehensive.py",
    "test_polymorphic_edge_cases.py",
    "test_polymorphic_grading.py",
    "test_polymorphic_problems.py",
    "test_polymorphic_serializers.py",
    "test_polymorphic_services.py",
    "test_problem_models.py",
    "test_progress_publishing.py",
    "test_submission_defaults.py",
    "test_submission_no_duplicates.py",
    "test_supporting_models.py",
    "test_uniqueness_constraints.py",
}


@pytest.mark.architecture
class TestFactoryEnforcement:
    """
    Tests must use Factory Boy factories, not Model.objects.create().

    All test data should come from factories in tests/factories/__init__.py.
    This ensures consistent defaults, proper relationships, and
    reusable test setup.

    If no factory exists for a model, add one before using it in tests.
    """

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def test_no_objects_create_in_tests(self, project_root: Path):
        """Test files must not use Model.objects.create()."""
        test_dirs = [
            project_root / "tests" / "unit",
            project_root / "tests" / "integration",
        ]

        # Pattern matches .objects.create( — captures the model name
        pattern = re.compile(r"\b(\w+)\.objects\.create\(")

        violations = []
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
            for py_file in test_dir.rglob("test_*.py"):
                if py_file.name in ALLOWED_FILES:
                    continue
                try:
                    source = py_file.read_text()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(source.splitlines(), 1):
                    match = pattern.search(line)
                    if match:
                        violations.append(f"  {py_file}:{i} - {match.group(0)})")

        if violations:
            report = "\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} uses of Model.objects.create() in tests.\n"
                f"Use Factory Boy factories instead (tests/factories/__init__.py).\n"
                f"Violations:\n{report}"
            )
