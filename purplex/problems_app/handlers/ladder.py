"""Student-facing test ladder shared by the probeable activity types.

``probeable_code`` (the student's code) and ``probeable_spec`` (one version the
LLM wrote from the student's explanation) both grade a single piece of code and
show its tests as one ordered ladder: rows up to and including the first
failure are visible, the rest are locked (see ``truncate_to_first_failure``).
"""

from typing import TYPE_CHECKING, Any

from .base import ActivityHandler
from .result_visibility import truncate_to_first_failure

if TYPE_CHECKING:
    from purplex.problems_app.models import Problem
    from purplex.submissions.models import Submission


def build_test_ladder(
    submission: "Submission", problem: "Problem"
) -> list[dict[str, Any]]:
    """Return the single-entry ladder for a submission's graded code.

    Pass counts cover every test; only the visible rows are truncated.

    Returns:
        ``[]`` when the submission has no code variation, otherwise one dict
        with ``success``, ``testsPassed``, ``totalTests``, ``test_results``
        (and its alias ``results``), ``lockedCount`` and ``visibleCount``.
    """
    if (
        not hasattr(submission, "code_variations")
        or not submission.code_variations.exists()
    ):
        return []

    variation = submission.code_variations.first()
    if not variation:
        return []

    rows = []
    test_execs = variation.test_executions.all().order_by("execution_order")
    if test_execs.exists():
        for test_exec in test_execs:
            rows.append(
                {
                    "isSuccessful": test_exec.passed,
                    "function_call": ActivityHandler._format_function_call(
                        problem.function_name, test_exec.input_values
                    ),
                    "expected_output": test_exec.expected_output,
                    "actual_output": test_exec.actual_output,
                    "error": test_exec.error_message,
                }
            )

    visible, locked = truncate_to_first_failure(rows, passed_key="isSuccessful")
    return [
        {
            "success": variation.tests_passed == variation.tests_total
            and variation.tests_total > 0,
            "testsPassed": variation.tests_passed,
            "totalTests": variation.tests_total,
            "test_results": visible,
            "results": visible,  # Duplicate for frontend compatibility
            "lockedCount": locked,
            "visibleCount": len(visible),
        }
    ]
