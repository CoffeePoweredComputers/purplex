"""Run an instructor oracle function in a bounded child process.

The probe and refute features call the instructor-written reference solution
with student-chosen arguments. Running it inside the web worker lets one slow
or memory-hungry call stall the whole (gevent) worker, so it runs here instead:
a fresh interpreter with CPU, memory and wall-clock limits and an empty
environment, so no secrets from the worker's environment reach the child.

This is a resource boundary, not a security boundary. The reference solution
is trusted code written by an instructor or TA (students only supply JSON
arguments). The restricted builtins only guard against accidents: Python code
can escape them, and the child runs as the same OS user with the same
filesystem and network access as the worker.

This module is stdlib-only and has no Django imports. The parent runs it as a
plain script by file path (``python -I -S oracle_sandbox.py``), so the child
never imports ``purplex.problems_app.services``.

Child protocol: argv carries the limits (``<cpu_s> <memory_bytes>``), which the
child applies to itself before reading its request; then one JSON object
``{"code", "function_name", "args"}`` on stdin and exactly one JSON line on
stdout: ``{"ok": true, "result": ...}`` or
``{"ok": false, "error_type": ..., "error": ...}``. Tuples, sets, frozensets
and dicts with non-string keys are tagged on the wire and rebuilt by the
parent, so callers receive the same Python types the oracle returned.
"""

import builtins
import json
import logging
import os
import resource
import signal
import subprocess  # nosec B404 - fixed argv, no shell
import sys
from typing import Any

logger = logging.getLogger(__name__)

# Builtins available to oracle code. Single source of truth for the probe
# service and the refute handler. No __import__ or __build_class__.
SAFE_BUILTIN_NAMES: tuple[str, ...] = (
    "abs",
    "all",
    "any",
    "bool",
    "chr",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "frozenset",
    "int",
    "isinstance",
    "len",
    "list",
    "map",
    "max",
    "min",
    "ord",
    "pow",
    "range",
    "reversed",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    "True",
    "False",
    "None",
)

# Largest encoded result the child will emit.
MAX_OUTPUT_BYTES = 1024 * 1024

# Message for any failure of the sandbox itself; details go to the logs.
SANDBOX_FAILED = "Oracle sandbox failed."


# --- Child side ---------------------------------------------------------------


def _safe_builtins() -> dict[str, Any]:
    return {name: getattr(builtins, name) for name in SAFE_BUILTIN_NAMES}


# Wire tag for values JSON cannot represent natively. Any dict carrying this
# key on the wire is a tag; real dicts that contain it are always tagged.
_TYPE_TAG = "__oracle_type__"


def _to_wire(obj: Any) -> Any:
    """Convert a result to JSON-encodable form, tagging non-JSON containers."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, list):
        return [_to_wire(item) for item in obj]
    for kind, container in (("tuple", tuple), ("frozenset", frozenset), ("set", set)):
        if isinstance(obj, container):
            return {_TYPE_TAG: kind, "items": [_to_wire(item) for item in obj]}
    if isinstance(obj, dict):
        if all(isinstance(key, str) for key in obj) and _TYPE_TAG not in obj:
            return {key: _to_wire(value) for key, value in obj.items()}
        return {
            _TYPE_TAG: "dict",
            "items": [[_to_wire(key), _to_wire(value)] for key, value in obj.items()],
        }
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).decode("utf-8", "replace")
    try:
        iterator = iter(obj)
    except TypeError:
        raise TypeError(
            f"Result of type {type(obj).__name__} is not JSON serializable"
        ) from None
    return [_to_wire(item) for item in iterator]


def _from_wire(obj: dict[str, Any]) -> Any:
    """json object_hook: rebuild values tagged by _to_wire."""
    kind = obj.get(_TYPE_TAG)
    if kind is None:
        return obj
    items = obj["items"]
    if kind == "tuple":
        return tuple(items)
    if kind == "set":
        return set(items)
    if kind == "frozenset":
        return frozenset(items)
    if kind == "dict":
        return dict(items)
    raise ValueError(f"Unknown oracle wire tag: {kind}")


def _encode(payload: dict[str, Any]) -> str:
    return json.dumps(_to_wire(payload), allow_nan=False)


def _failure(error_type: str, error: str) -> dict[str, Any]:
    return {"ok": False, "error_type": error_type, "error": error}


def _run(request: dict[str, Any]) -> dict[str, Any]:
    code = request["code"]
    function_name = request["function_name"]
    args = request["args"]

    restricted_globals: dict[str, Any] = {"__builtins__": _safe_builtins()}
    try:
        # nosec B102: trusted instructor code; rlimits bound resources only
        exec(code, restricted_globals)  # nosec B102
        if function_name not in restricted_globals:
            return _failure("FunctionNotFound", function_name)
        result = restricted_globals[function_name](**args)
    except BaseException as e:  # noqa: BLE001 - must always emit a JSON line
        return _failure(e.__class__.__name__, str(e))
    return {"ok": True, "result": result}


def _apply_limits(cpu_s: int, memory_bytes: int) -> None:
    """Limit this (child) process's CPU time and address space.

    The child limits itself instead of the parent using Popen's preexec_fn,
    which is unsafe when the parent has OS threads (gevent's threadpool).
    """
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))


def main() -> None:
    """Child entry point: limit itself, read one request, write one JSON line."""
    try:
        _apply_limits(int(sys.argv[1]), int(sys.argv[2]))
    except BaseException as e:  # noqa: BLE001 - must always emit a JSON line
        # Never run the oracle unlimited (e.g. the worker's hard rlimit is
        # below the requested one); the parent logs this stderr line.
        sys.stderr.write(f"Could not apply oracle limits: {e}\n")
        payload = _failure("SandboxError", SANDBOX_FAILED)
    else:
        try:
            request = json.loads(sys.stdin.read())
            payload = _run(request)
        except BaseException as e:  # noqa: BLE001 - must always emit a JSON line
            payload = _failure("SandboxError", f"Bad sandbox request: {e}")

    try:
        line = _encode(payload)
        if len(line.encode("utf-8")) > MAX_OUTPUT_BYTES:
            line = _encode(_failure("SerializationError", "Result is too large."))
    except Exception as e:
        line = _encode(
            _failure("SerializationError", f"Result could not be serialized: {e}")
        )
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


# --- Parent side --------------------------------------------------------------


def _kill_process_group(proc: subprocess.Popen) -> None:
    """SIGKILL the child and anything it spawned in its process group."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        proc.kill()  # group already gone; make sure the child itself is


def run_oracle_sandboxed(
    code: str,
    function_name: str,
    args: dict[str, Any],
    *,
    timeout_s: float,
    cpu_s: int,
    memory_mb: int,
    max_input_bytes: int,
) -> dict[str, Any]:
    """Call ``function_name(**args)`` from ``code`` in a limited subprocess.

    Args:
        code: Source defining the function.
        function_name: Name of the function to call.
        args: Keyword arguments (JSON-serializable).
        timeout_s: Wall-clock limit for the whole child process.
        cpu_s: RLIMIT_CPU soft limit in seconds (hard limit is one more).
        memory_mb: RLIMIT_AS limit in megabytes.
        max_input_bytes: Largest allowed JSON encoding of ``args``.

    Returns:
        ``{"ok": True, "result": <value>}`` or
        ``{"ok": False, "error_type": str, "error": str}``. error_type is the
        oracle's exception class name (e.g. TypeError, MemoryError), or one
        of FunctionNotFound, Timeout, InputTooLarge, SerializationError,
        SandboxError. The result keeps tuple, set, frozenset and non-string
        dict-key types; bytes become str and other iterables become lists.
    """
    try:
        encoded_args = json.dumps(args)
    except (TypeError, ValueError) as e:
        return _failure("SerializationError", f"Inputs could not be encoded: {e}")
    if len(encoded_args) > max_input_bytes:
        return _failure(
            "InputTooLarge", f"Inputs exceed the {max_input_bytes}-byte limit."
        )

    request = json.dumps(
        {"code": code, "function_name": function_name, "args": args}
    ).encode("utf-8")
    memory_bytes = int(memory_mb * 2**20)

    try:
        # Popen rather than subprocess.run so a timeout can kill the child's
        # whole process group (start_new_session makes the child its leader):
        # draining the pipes would otherwise wait on any grandchild holding them.
        # The child applies the rlimits itself (see main), so no Python code
        # runs in the parent between fork and exec.
        with subprocess.Popen(  # nosec B603 - fixed argv, no shell
            [sys.executable, "-I", "-S", __file__, str(int(cpu_s)), str(memory_bytes)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={},  # keep the worker's secrets out of the child
            start_new_session=True,
        ) as proc:
            try:
                stdout, stderr = proc.communicate(input=request, timeout=timeout_s)
            except subprocess.TimeoutExpired:
                _kill_process_group(proc)
                proc.communicate()  # reap and drain; nothing holds the pipes now
                return _failure(
                    "Timeout", f"Oracle exceeded the {timeout_s}s time limit."
                )
            except BaseException:
                _kill_process_group(proc)
                raise
    except (subprocess.SubprocessError, OSError) as e:
        # Raised when fork/exec fails (e.g. the process table is full).
        logger.warning("Oracle sandbox could not run: %s", e)
        return _failure("SandboxError", SANDBOX_FAILED)
    returncode = proc.returncode

    # SIGXCPU at the CPU rlimit's soft limit: the oracle ran out of time, same
    # as a wall-clock timeout. Any other signal, including SIGKILL from the
    # OOM killer, falls through and is logged as a sandbox failure.
    if returncode == -signal.SIGXCPU:
        return _failure("Timeout", "Oracle exceeded its CPU time limit.")

    stderr_tail = stderr.decode("utf-8", "replace")[-500:]
    if returncode != 0:
        logger.warning(
            "Oracle sandbox exited with code %s: %s", returncode, stderr_tail
        )
        return _failure("SandboxError", SANDBOX_FAILED)

    lines = stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        payload = json.loads(lines[-1], object_hook=_from_wire)
    except (IndexError, KeyError, TypeError, ValueError):
        payload = None
    if not isinstance(payload, dict) or "ok" not in payload:
        logger.warning("Oracle sandbox produced unparsable output: %s", stderr_tail)
        return _failure("SandboxError", SANDBOX_FAILED)
    if payload.get("error_type") == "SandboxError":
        logger.warning("Oracle sandbox reported a failure: %s", stderr_tail)
    return payload


if __name__ == "__main__":
    main()
