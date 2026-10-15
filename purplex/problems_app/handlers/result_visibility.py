"""Student-facing visibility rules for test results.

Pure helpers with no Django dependencies. Storage is never truncated; these
helpers only shape what a student sees after a submission.
"""

from typing import Any


def truncate_to_first_failure(
    rows: list[dict[str, Any]], *, passed_key: str
) -> tuple[list[dict[str, Any]], int]:
    """Keep rows up to and including the first failing row; lock the rest.

    Probeable Problems show a student only the first failing test after a
    submission and lock the remaining tests, so the test suite cannot stand in
    for probing (Denny et al., ITiCSE 2025, Section 4.2; Tang et al., ACE 2026,
    Section 3.1.5: "Subsequent test cases are intentionally locked to
    discourage students from discovering remaining ambiguities from viewing
    test cases").

    Args:
        rows: Test result rows in execution order.
        passed_key: Key whose truthy value marks a row as passed.

    Returns:
        A tuple ``(visible_rows, locked_count)`` where ``locked_count`` is
        ``len(rows) - len(visible_rows)``. If every row passes, nothing is
        locked.
    """
    visible: list[dict[str, Any]] = []
    for row in rows:
        visible.append(row)
        if not row.get(passed_key):
            break
    return visible, len(rows) - len(visible)
