"""Unit tests for the bounded oracle subprocess (issue #174).

These spawn real child interpreters; no database access.
"""

import io
import json
import os
import resource
import signal
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.services.oracle_sandbox import main, run_oracle_sandboxed

pytestmark = [pytest.mark.unit]

MODULE = "purplex.problems_app.services.oracle_sandbox"
LIMITS = {"timeout_s": 3, "cpu_s": 2, "memory_mb": 256, "max_input_bytes": 10_000}


def _run(code, args=None, function_name="f", **overrides):
    return run_oracle_sandboxed(
        code, function_name, {} if args is None else args, **{**LIMITS, **overrides}
    )


class TestResults:
    def test_success_returns_native_int(self):
        outcome = _run("def f(x):\n    return x + 1", {"x": 1})
        assert outcome == {"ok": True, "result": 2}
        assert type(outcome["result"]) is int

    @pytest.mark.parametrize(
        "expression, expected",
        [
            ("(1, 2)", (1, 2)),
            ("{3, (1, 2)}", {3, (1, 2)}),
            ("frozenset([1])", frozenset([1])),
            ("{1: (2,), (3, 4): frozenset([5])}", {1: (2,), (3, 4): frozenset([5])}),
            (
                "{'__oracle_type__': 'tuple', 'items': [1]}",
                {"__oracle_type__": "tuple", "items": [1]},
            ),
            ("{'a': [1, {2}]}", {"a": [1, {2}]}),
        ],
    )
    def test_python_types_survive_round_trip(self, expression, expected):
        """Refute predicates such as ``result == (lo, hi)`` need the real type."""
        result = _run(f"def f():\n    return {expression}")["result"]
        assert result == expected
        assert type(result) is type(expected)

    def test_bytes_and_iterators_become_json_values(self):
        assert _run("def f():\n    return b'hi'")["result"] == "hi"
        assert _run("def f():\n    return map(str, [1, 2])")["result"] == ["1", "2"]

    def test_nan_is_serialization_error(self):
        outcome = _run("def f():\n    return float('nan')")
        assert outcome["ok"] is False
        assert outcome["error_type"] == "SerializationError"


class TestErrors:
    def test_type_error_preserved(self):
        outcome = _run("def f(x):\n    return x + 1", {"x": "abc"})
        assert outcome["ok"] is False
        assert outcome["error_type"] == "TypeError"

    def test_value_error_text_preserved(self):
        outcome = _run("def f(x):\n    return int(x)", {"x": "abc"})
        assert outcome["error_type"] == "ValueError"
        assert "invalid literal" in outcome["error"]

    def test_missing_function(self):
        outcome = _run("def g():\n    return 1")
        assert outcome == {"ok": False, "error_type": "FunctionNotFound", "error": "f"}

    def test_import_is_blocked(self):
        outcome = _run("import os\ndef f():\n    return 1")
        assert outcome["ok"] is False


class TestLimits:
    def test_infinite_loop_times_out(self):
        start = time.monotonic()
        outcome = _run("def f():\n    while True:\n        pass", timeout_s=1)
        elapsed = time.monotonic() - start
        assert outcome["ok"] is False
        assert outcome["error_type"] == "Timeout"
        assert elapsed < 3

    def test_cpu_limit_reported_as_timeout(self):
        outcome = _run("def f():\n    while True:\n        pass", timeout_s=10, cpu_s=1)
        assert outcome["error_type"] == "Timeout"

    def test_memory_bomb_fails_without_raising(self):
        outcome = _run("def f():\n    return [0] * (10**9)")
        assert outcome["ok"] is False
        assert outcome["error_type"] in ("MemoryError", "SandboxError")

    def test_child_gets_empty_environment(self):
        with patch(f"{MODULE}.subprocess.Popen", wraps=subprocess.Popen) as popen:
            outcome = _run("def f():\n    return 1")
        assert outcome == {"ok": True, "result": 1}
        assert popen.call_args.kwargs["env"] == {}

    def test_oversized_input_rejected_without_spawning(self):
        with patch(f"{MODULE}.subprocess.Popen") as popen:
            outcome = _run("def f(x):\n    return x", {"x": "a" * 20_000})
        popen.assert_not_called()
        assert outcome["ok"] is False
        assert outcome["error_type"] == "InputTooLarge"

    def test_timeout_kills_the_whole_process_group(self):
        """Grandchildren share the child's group; killing it frees the pipes."""
        with patch(f"{MODULE}.os.killpg", wraps=os.killpg) as killpg:
            outcome = _run("def f():\n    while True:\n        pass", timeout_s=1)
        assert outcome["error_type"] == "Timeout"
        killpg.assert_called_once()
        assert killpg.call_args.args[1] == signal.SIGKILL

    def test_limits_are_applied_by_the_child_not_preexec_fn(self):
        """preexec_fn is unsafe in a threaded (gevent) parent."""
        with patch(f"{MODULE}.subprocess.Popen", wraps=subprocess.Popen) as popen:
            outcome = _run("def f():\n    return 1", cpu_s=2, memory_mb=256)
        assert outcome == {"ok": True, "result": 1}
        assert "preexec_fn" not in popen.call_args.kwargs
        assert popen.call_args.args[0][-2:] == ["2", str(256 * 2**20)]


class TestChildMain:
    """Runs the child entry point in-process; setrlimit is always patched."""

    def _main(self, argv, stdin):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch(f"{MODULE}.sys.argv", argv),
            patch(f"{MODULE}.sys.stdin", io.StringIO(stdin)),
            patch(f"{MODULE}.sys.stdout", stdout),
            patch(f"{MODULE}.sys.stderr", stderr),
        ):
            main()
        return json.loads(stdout.getvalue()), stderr.getvalue()

    def test_limits_applied_before_running(self):
        request = json.dumps(
            {"code": "def f():\n    return 1", "function_name": "f", "args": {}}
        )
        with patch(f"{MODULE}.resource.setrlimit") as setrlimit:
            payload, _ = self._main(["sandbox", "2", "1024"], request)
        assert payload == {"ok": True, "result": 1}
        limits = [(c.args[0], c.args[1]) for c in setrlimit.call_args_list]
        assert limits == [
            (resource.RLIMIT_CORE, (0, 0)),
            (resource.RLIMIT_CPU, (2, 3)),
            (resource.RLIMIT_AS, (1024, 1024)),
        ]

    def test_rlimit_failure_emits_sandbox_error_without_running(self):
        """A hard rlimit below the requested one must not run the oracle."""
        request = json.dumps(
            {"code": "def f():\n    return 1", "function_name": "f", "args": {}}
        )
        with (
            patch(
                f"{MODULE}.resource.setrlimit", side_effect=ValueError("not allowed")
            ),
            patch(f"{MODULE}._run") as run,
        ):
            payload, stderr = self._main(["sandbox", "2", "1024"], request)
        run.assert_not_called()
        assert payload == {
            "ok": False,
            "error_type": "SandboxError",
            "error": "Oracle sandbox failed.",
        }
        assert "not allowed" in stderr


class TestSandboxFailures:
    def test_sigkill_is_logged_sandbox_error_not_timeout(self):
        """An OOM kill must not be reported to students as a CPU timeout."""
        proc = MagicMock()
        proc.__enter__.return_value = proc
        proc.communicate.return_value = (b"", b"")
        proc.returncode = -signal.SIGKILL
        with (
            patch(f"{MODULE}.subprocess.Popen", return_value=proc),
            patch(f"{MODULE}.logger") as logger,
        ):
            outcome = _run("def f():\n    return 1")
        assert outcome == {
            "ok": False,
            "error_type": "SandboxError",
            "error": "Oracle sandbox failed.",
        }
        logger.warning.assert_called_once()
        assert -signal.SIGKILL in logger.warning.call_args.args

    def test_spawn_os_error_is_sandbox_error(self):
        with patch(
            f"{MODULE}.subprocess.Popen", side_effect=OSError(11, "fork failed")
        ):
            outcome = _run("def f():\n    return 1")
        assert outcome["error_type"] == "SandboxError"


class TestConcurrencyAndCore:
    def test_busy_when_no_slot_frees_up(self):
        from purplex.problems_app.services import oracle_sandbox

        slots = oracle_sandbox._get_slots(2)
        held = 0
        # Hold every slot so the next call has to wait and give up.
        while slots.acquire(blocking=False):
            held += 1
        try:
            with patch(f"{MODULE}.subprocess.Popen") as popen:
                outcome = _run("def f():\n    return 1", queue_timeout_s=0.05)
        finally:
            for _ in range(held):
                slots.release()
        assert outcome["ok"] is False
        assert outcome["error_type"] == "Busy"
        popen.assert_not_called()

    def test_slot_is_released_after_a_run(self):
        from purplex.problems_app.services import oracle_sandbox

        slots = oracle_sandbox._get_slots(2)
        before = slots._value
        assert _run("def f():\n    return 1") == {"ok": True, "result": 1}
        assert slots._value == before

    def test_child_disables_core_dumps(self):
        import sys

        from purplex.problems_app.services import oracle_sandbox

        probe = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import resource, runpy, sys;"
                "m = runpy.run_path(sys.argv[1], run_name='probe');"
                "m['_apply_limits'](2, 256 * 2**20);"
                "print(resource.getrlimit(resource.RLIMIT_CORE))",
                oracle_sandbox.__file__,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        assert probe.stdout.strip() == "(0, 0)"
