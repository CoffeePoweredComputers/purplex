"""Unit tests for how ProbeService and Refute map sandbox outcomes (issue #174).

Most tests patch the sandbox out; none touch the database or Redis.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from purplex.problems_app.handlers.refute.handler import _safe_execute
from purplex.problems_app.services.probe_service import (
    HIDDEN_ORACLE_ERROR,
    ORACLE_INPUT_TOO_LARGE_ERROR,
    ORACLE_MEMORY_ERROR,
    ORACLE_TIMEOUT_ERROR,
    ProbeService,
)

pytestmark = [pytest.mark.unit]

SANDBOX = "purplex.problems_app.services.probe_service.run_oracle_sandboxed"
# _safe_execute imports the function lazily, so patch it at its source.
SANDBOX_SOURCE = "purplex.problems_app.services.oracle_sandbox.run_oracle_sandboxed"
TIMEOUT = {"ok": False, "error_type": "Timeout", "error": "too slow"}
# str(MemoryError()) is empty, so the raw error text would be blank.
MEMORY = {"ok": False, "error_type": "MemoryError", "error": ""}
NOT_FOUND = {"ok": False, "error_type": "FunctionNotFound", "error": "f"}
TOO_LARGE = {"ok": False, "error_type": "InputTooLarge", "error": "too big"}


class TestOracleMapping:
    @pytest.mark.parametrize("reveal_types", [True, False])
    @pytest.mark.parametrize(
        "outcome, message",
        [(TIMEOUT, ORACLE_TIMEOUT_ERROR), (MEMORY, ORACLE_MEMORY_ERROR)],
        ids=["timeout", "memory"],
    )
    def test_resource_limit_message_in_both_modes(self, outcome, message, reveal_types):
        with patch(SANDBOX, return_value=outcome):
            result = ProbeService._execute_oracle(
                "def f(x):\n    return x", "f", {"x": 1}, reveal_types=reveal_types
            )
        assert result == {"success": False, "result": None, "error": message}
        assert "Try smaller values." in result["error"]

    @pytest.mark.parametrize("reveal_types", [True, False])
    @pytest.mark.parametrize(
        "outcome, message",
        [
            (NOT_FOUND, "Function 'f' not defined in reference solution"),
            (TOO_LARGE, ORACLE_INPUT_TOO_LARGE_ERROR),
        ],
        ids=["function-not-found", "input-too-large"],
    )
    def test_fixed_messages_in_both_modes(self, outcome, message, reveal_types):
        with patch(SANDBOX, return_value=outcome):
            result = ProbeService._execute_oracle(
                "def f(x):\n    return x", "f", {"x": 1}, reveal_types=reveal_types
            )
        assert result == {"success": False, "result": None, "error": message}

    def test_revealed_type_error_keeps_prefix(self):
        outcome = {"ok": False, "error_type": "TypeError", "error": "str + int"}
        with patch(SANDBOX, return_value=outcome):
            result = ProbeService._execute_oracle(
                "def f(x):\n    return x", "f", {"x": 1}, reveal_types=True
            )
        assert result["error"].startswith("Invalid arguments:")

    def test_hidden_type_error_sanitised(self):
        outcome = {"ok": False, "error_type": "TypeError", "error": "str + int"}
        with patch(SANDBOX, return_value=outcome):
            result = ProbeService._execute_oracle(
                "def f(x):\n    return x", "f", {"x": 1}, reveal_types=False
            )
        assert result["error"] == HIDDEN_ORACLE_ERROR


class TestExecuteProbe:
    def test_timeout_does_not_charge_budget(self):
        problem = SimpleNamespace(
            id=1,
            reference_solution="def f(x):\n    return x",
            function_name="f",
            show_function_signature=True,
        )
        status = {"mode": "block", "remaining": 3, "can_probe": True}
        with (
            patch(SANDBOX, return_value=TIMEOUT),
            patch.object(
                ProbeService, "check_probe_limit", return_value=(True, status)
            ),
            patch.object(ProbeService, "_record_probe") as record,
        ):
            result = ProbeService.execute_probe(
                problem, user_id=7, probe_input={"x": 1}
            )
        record.assert_not_called()
        assert result["success"] is False
        assert result["error"] == ORACLE_TIMEOUT_ERROR


class TestRefuteSafeExecute:
    def test_tuple_result_keeps_its_type_for_claim_predicates(self):
        result = _safe_execute(
            "def f(lo, hi):\n    return (lo, hi)", "f", {"lo": 1, "hi": 2}
        )
        assert result == {"success": True, "result": (1, 2), "error": None}

    def test_memory_error_has_message(self):
        with patch(SANDBOX_SOURCE, return_value=MEMORY):
            result = _safe_execute("def f():\n    return 1", "f", {})
        assert result["success"] is False
        assert "ran out of memory" in result["error"]

    @pytest.mark.parametrize(
        "outcome, message",
        [
            (NOT_FOUND, "Function 'f' not defined in code"),
            (TOO_LARGE, "These inputs are too large."),
        ],
        ids=["function-not-found", "input-too-large"],
    )
    def test_fixed_messages(self, outcome, message):
        with patch(SANDBOX_SOURCE, return_value=outcome):
            result = _safe_execute("def f():\n    return 1", "f", {})
        assert result == {
            "success": False,
            "result": None,
            "error": message,
            "error_type": outcome["error_type"],
        }


BUSY = {"ok": False, "error_type": "Busy", "error": "busy"}
SANDBOX_DOWN = {"ok": False, "error_type": "SandboxError", "error": "down"}


class TestInfrastructureFailures:
    @pytest.mark.parametrize("reveal_types", [True, False])
    def test_busy_message_in_both_modes(self, reveal_types):
        from purplex.problems_app.services.probe_service import ORACLE_BUSY_ERROR

        with patch(SANDBOX, return_value=BUSY):
            result = ProbeService._execute_oracle(
                "def f(x):\n    return x", "f", {"x": 1}, reveal_types=reveal_types
            )
        assert result == {"success": False, "result": None, "error": ORACLE_BUSY_ERROR}

    @pytest.mark.parametrize("outcome", [BUSY, SANDBOX_DOWN], ids=["busy", "down"])
    def test_refute_submit_does_not_grade_on_sandbox_failure(self, outcome):
        from unittest.mock import MagicMock

        from purplex.problems_app.handlers import get_handler
        from purplex.problems_app.models import RefuteProblem

        problem = MagicMock(spec=RefuteProblem)
        problem.reference_solution = "def f(x):\n    return x * 2"
        problem.function_signature = "f(x: int) -> int"
        problem.claim_predicate = "result > 0"
        problem.claim_text = "always positive"
        submission = MagicMock()

        with patch(SANDBOX_SOURCE, return_value=outcome):
            result = get_handler("refute").submit(submission, '{"x": -5}', problem, {})

        assert result.error
        submission.save.assert_not_called()

    def test_refute_safe_execute_reports_error_type(self):
        with patch(SANDBOX_SOURCE, return_value=SANDBOX_DOWN):
            result = _safe_execute("def f(x):\n    return x", "f", {"x": 1})
        assert result["success"] is False
        assert result["error_type"] == "SandboxError"
        assert "temporarily unavailable" in result["error"]
