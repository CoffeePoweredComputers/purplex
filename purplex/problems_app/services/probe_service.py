"""
Probe Service for Probeable Code problems.

Handles:
- Oracle execution (running reference_solution with student-provided inputs)
- Probe count tracking in Redis
- Probe limit enforcement based on probe_mode
"""

import json
import logging
from typing import TYPE_CHECKING, Any

from django.conf import settings

from purplex.utils.redis_client import get_rate_limit_client

from .oracle_sandbox import run_oracle_sandboxed

if TYPE_CHECKING:
    from purplex.problems_app.models import ProbeableCodeProblem

logger = logging.getLogger(__name__)

# Redis key prefixes
PROBE_COUNT_PREFIX = "probe:count:"
SUBMISSION_COUNT_PREFIX = "probe:submissions:"
PROBE_HISTORY_PREFIX = "probe:history:"

# TTL for probe data (7 days)
PROBE_DATA_TTL = 60 * 60 * 24 * 7

# Shown instead of the raw oracle exception when the signature is hidden, so the
# error text cannot reveal parameter types the instructor chose to hide.
HIDDEN_ORACLE_ERROR = "These inputs could not be evaluated. Try different values."

# Shown in both reveal modes: neither reveals anything about parameter types.
ORACLE_TIMEOUT_ERROR = "The oracle took too long on these inputs. Try smaller values."
ORACLE_MEMORY_ERROR = (
    "The oracle ran out of memory on these inputs. Try smaller values."
)
ORACLE_INPUT_TOO_LARGE_ERROR = "Probe inputs are too large."
ORACLE_BUSY_ERROR = "The oracle is busy right now. Try again in a moment."


def get_sandbox_limits() -> dict[str, Any]:
    """Return run_oracle_sandboxed limit kwargs from settings.PROBE_SANDBOX.

    The settings dict (purplex/settings/base.py) is the single source of the
    values; every key is required.
    """
    config = settings.PROBE_SANDBOX
    return {
        "timeout_s": config["TIMEOUT_SECONDS"],
        "cpu_s": config["CPU_SECONDS"],
        "memory_mb": config["MEMORY_MB"],
        "max_input_bytes": config["MAX_INPUT_BYTES"],
        "max_concurrent": config["MAX_CONCURRENT"],
        "queue_timeout_s": config["QUEUE_TIMEOUT_SECONDS"],
    }


# Primitive type hints that probe inputs are checked against. Keys are lowercase
# aliases; values are canonical kinds. Must stay in sync with normalizePrimitiveType
# in purplex/client/src/components/activities/inputs/shared/useProbeState.ts.
_PRIMITIVE_ALIASES: dict[str, str] = {
    "int": "int",
    "integer": "int",
    "float": "float",
    "number": "float",
    "bool": "bool",
    "boolean": "bool",
    "str": "str",
    "string": "str",
}

# Indefinite article per canonical kind, for error messages.
_KIND_ARTICLES: dict[str, str] = {
    "int": "an",
    "float": "a",
    "bool": "a",
    "str": "a",
}


class ProbeService:
    """Service for handling probe queries in Probeable Code problems."""

    @classmethod
    def execute_probe(
        cls, problem: "ProbeableCodeProblem", user_id: int, probe_input: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a probe query against the oracle (reference_solution).

        Args:
            problem: The ProbeableCodeProblem instance
            user_id: ID of the user making the probe
            probe_input: Dictionary of input parameter values

        Returns:
            Dict with success, result, error, and probe_status fields
        """
        # Check probe limits first
        can_probe, probe_status = cls.check_probe_limit(problem, user_id)
        if not can_probe:
            return {
                "success": False,
                "result": None,
                "error": probe_status.get("message", "Probe limit reached"),
                "probe_status": probe_status,
            }

        # Execute the oracle
        result = cls._execute_oracle(
            problem.reference_solution,
            problem.function_name,
            probe_input,
            reveal_types=getattr(problem, "show_function_signature", True),
        )

        if result["success"]:
            # Increment probe count and store in history
            cls._record_probe(problem, user_id, probe_input, result["result"])

        # Get updated probe status
        _, updated_status = cls.check_probe_limit(problem, user_id)

        return {
            "success": result["success"],
            "result": result["result"],
            "error": result.get("error"),
            "probe_status": updated_status,
        }

    @classmethod
    def validate_input(
        cls, problem: "ProbeableCodeProblem", probe_input: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Validate probe input against the problem's function signature.

        Type names appear in error messages only when the problem shows its
        signature to students.

        Args:
            problem: The probeable problem being probed.
            probe_input: Dictionary of parameter name -> value.

        Returns:
            Tuple of (is_valid, error_message).
        """
        return validate_probe_input(
            problem.function_signature,
            probe_input,
            reveal_types=getattr(problem, "show_function_signature", True),
        )

    @classmethod
    def check_probe_limit(
        cls, problem: "ProbeableCodeProblem", user_id: int
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if user can make another probe based on probe_mode.

        Args:
            problem: The ProbeableCodeProblem instance
            user_id: ID of the user

        Returns:
            Tuple of (can_probe: bool, status: dict)
            Status includes: remaining_probes, total_used, mode, message
        """
        mode = problem.probe_mode
        max_probes = problem.max_probes

        if mode == "explore":
            # Unlimited probing
            probes_used = cls._get_probe_count(problem.id, user_id)
            return True, {
                "mode": "explore",
                "remaining": None,  # Unlimited
                "used": probes_used,
                "can_probe": True,
                "message": "Unlimited probes available",
            }

        probes_used = cls._get_probe_count(problem.id, user_id)

        if mode == "block":
            # N probes total, then disabled
            remaining = max(0, max_probes - probes_used)
            can_probe = remaining > 0

            return can_probe, {
                "mode": "block",
                "remaining": remaining,
                "used": probes_used,
                "max_probes": max_probes,
                "can_probe": can_probe,
                "message": (
                    f"{remaining} probes remaining"
                    if can_probe
                    else "No probes remaining"
                ),
            }

        elif mode == "cooldown":
            # N probes -> submit X times -> get M more probes
            submissions_since_refill = cls._get_submission_count_since_refill(
                problem.id, user_id
            )
            cooldown_attempts = problem.cooldown_attempts
            cooldown_refill = problem.cooldown_refill

            # Calculate effective probe budget
            # Start with max_probes, add cooldown_refill for each completed cooldown cycle
            refill_cycles = submissions_since_refill // cooldown_attempts
            effective_budget = max_probes + (refill_cycles * cooldown_refill)
            remaining = max(0, effective_budget - probes_used)
            can_probe = remaining > 0

            # Calculate submissions needed for next refill
            submissions_to_next_refill = cooldown_attempts - (
                submissions_since_refill % cooldown_attempts
            )

            return can_probe, {
                "mode": "cooldown",
                "remaining": remaining,
                "used": probes_used,
                "max_probes": max_probes,
                "can_probe": can_probe,
                "cooldown_attempts": cooldown_attempts,
                "cooldown_refill": cooldown_refill,
                "submissions_since_refill": submissions_since_refill,
                "submissions_to_next_refill": (
                    submissions_to_next_refill if not can_probe else None
                ),
                "message": cls._build_cooldown_message(
                    remaining, submissions_to_next_refill, can_probe
                ),
            }

        # Unknown mode - default to allowing
        logger.warning(f"Unknown probe_mode: {mode} for problem {problem.id}")
        return True, {
            "mode": mode,
            "remaining": None,
            "used": probes_used,
            "can_probe": True,
            "message": "Probing allowed",
        }

    @classmethod
    def record_submission(cls, problem_id: int, user_id: int) -> None:
        """
        Record a code submission for cooldown tracking.

        Called after a user submits code (not probe queries).
        """
        redis = get_rate_limit_client()
        key = f"{SUBMISSION_COUNT_PREFIX}{problem_id}:{user_id}"

        try:
            redis.incr(key)
            redis.expire(key, PROBE_DATA_TTL)
            logger.debug(
                f"Recorded submission for problem {problem_id}, user {user_id}"
            )
        except Exception as e:
            logger.error(f"Failed to record submission count: {e}")

    @classmethod
    def get_probe_history(
        cls, problem_id: int, user_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get the user's probe history for a problem.

        Args:
            problem_id: The problem ID
            user_id: The user ID
            limit: Maximum number of history entries to return

        Returns:
            List of probe history entries (most recent first)
        """
        redis = get_rate_limit_client()
        key = f"{PROBE_HISTORY_PREFIX}{problem_id}:{user_id}"

        try:
            # Get most recent entries
            history_json = redis.lrange(key, 0, limit - 1)
            history = []
            for entry_json in history_json:
                try:
                    history.append(json.loads(entry_json))
                except json.JSONDecodeError:
                    continue
            return history
        except Exception as e:
            logger.error(f"Failed to get probe history: {e}")
            return []

    @classmethod
    def get_probe_status(
        cls, problem: "ProbeableCodeProblem", user_id: int
    ) -> dict[str, Any]:
        """
        Get current probe status without executing a probe.

        Useful for frontend to display probe availability.
        """
        _, status = cls.check_probe_limit(problem, user_id)
        return status

    # --- Private Methods ---

    @classmethod
    def _execute_oracle(
        cls,
        reference_code: str,
        function_name: str,
        args: dict[str, Any],
        *,
        reveal_types: bool = True,
    ) -> dict[str, Any]:
        """
        Execute the oracle (reference_solution) with provided arguments.

        Runs in a separate, resource-limited process (see oracle_sandbox) so a
        slow or memory-hungry oracle cannot stall the web worker.

        Args:
            reference_code: The reference solution code
            function_name: Name of the function to call
            args: Arguments to pass to the function
            reveal_types: When False (signature hidden), oracle exceptions are
                replaced by HIDDEN_ORACLE_ERROR so their text cannot leak
                parameter types.

        Returns:
            Dict with 'success', 'result', 'error' keys.
        """
        outcome = run_oracle_sandboxed(
            reference_code, function_name, args, **get_sandbox_limits()
        )
        if outcome["ok"]:
            return {"success": True, "result": outcome["result"], "error": None}

        error_type = outcome.get("error_type")
        error = outcome.get("error", "")

        if error_type == "FunctionNotFound":
            message = f"Function '{function_name}' not defined in reference solution"
        elif error_type == "Timeout":
            message = ORACLE_TIMEOUT_ERROR
        elif error_type == "MemoryError":
            message = ORACLE_MEMORY_ERROR
        elif error_type == "InputTooLarge":
            message = ORACLE_INPUT_TOO_LARGE_ERROR
        elif error_type == "Busy":
            message = ORACLE_BUSY_ERROR
        elif not reveal_types:
            logger.info("Oracle %s hidden from student: %s", error_type, error)
            message = HIDDEN_ORACLE_ERROR
        elif error_type == "TypeError":
            # Usually wrong number/type of arguments
            message = f"Invalid arguments: {error}"
        else:
            message = error

        return {"success": False, "result": None, "error": message}

    @classmethod
    def _get_probe_count(cls, problem_id: int, user_id: int) -> int:
        """Get the number of probes used by a user for a problem."""
        redis = get_rate_limit_client()
        key = f"{PROBE_COUNT_PREFIX}{problem_id}:{user_id}"

        try:
            count = redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get probe count: {e}")
            return 0

    @classmethod
    def _get_submission_count_since_refill(cls, problem_id: int, user_id: int) -> int:
        """Get the number of code submissions since last probe refill."""
        redis = get_rate_limit_client()
        key = f"{SUBMISSION_COUNT_PREFIX}{problem_id}:{user_id}"

        try:
            count = redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get submission count: {e}")
            return 0

    @classmethod
    def _record_probe(
        cls,
        problem: "ProbeableCodeProblem",
        user_id: int,
        probe_input: dict[str, Any],
        result: Any,
    ) -> None:
        """Record a successful probe in Redis."""
        redis = get_rate_limit_client()
        problem_id = problem.id

        try:
            # Increment probe count
            count_key = f"{PROBE_COUNT_PREFIX}{problem_id}:{user_id}"
            redis.incr(count_key)
            redis.expire(count_key, PROBE_DATA_TTL)

            # Add to history (LPUSH for most recent first)
            history_key = f"{PROBE_HISTORY_PREFIX}{problem_id}:{user_id}"
            history_entry = json.dumps(
                {
                    "input": probe_input,
                    "output": cls._serialize_result(result),
                    "timestamp": cls._get_timestamp(),
                }
            )
            redis.lpush(history_key, history_entry)
            redis.ltrim(history_key, 0, 99)  # Keep last 100 probes
            redis.expire(history_key, PROBE_DATA_TTL)

            logger.debug(
                f"Recorded probe for problem {problem_id}, user {user_id}: "
                f"input={probe_input}"
            )
        except Exception as e:
            logger.error(f"Failed to record probe: {e}")

    @staticmethod
    def _serialize_result(result: Any) -> Any:
        """Serialize a probe result for storage/transmission."""
        # Handle common types that need special serialization
        if isinstance(result, (set, frozenset)):
            return list(result)
        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")
        # Default: return as-is (json.dumps will handle most cases)
        return result

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _build_cooldown_message(
        remaining: int, submissions_to_next: int, can_probe: bool
    ) -> str:
        """Build a user-friendly message for cooldown mode."""
        if can_probe:
            return f"{remaining} probes remaining"
        else:
            if submissions_to_next == 1:
                return f"No probes remaining. Submit {submissions_to_next} more time to unlock more probes."
            return f"No probes remaining. Submit {submissions_to_next} more times to unlock more probes."


_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = frozenset(_OPENERS.values())


def _split_top_level(text: str, sep: str = ",") -> list[str]:
    """Split ``text`` on ``sep`` where it is not nested or quoted.

    Brackets ``()``, ``[]`` and ``{}`` raise the nesting depth; single- and
    double-quoted strings (with backslash escapes) are skipped. Unbalanced
    input is tolerated: depth never drops below zero.

    Args:
        text: Text to split, such as a parameter list.
        sep: Single-character separator.

    Returns:
        The pieces between top-level separators, unstripped.
    """
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    current: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            current.append(ch)
            if ch == "\\" and i + 1 < len(text):
                current.append(text[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            current.append(ch)
        elif ch in _OPENERS:
            depth += 1
            current.append(ch)
        elif ch in _CLOSERS:
            depth = max(depth - 1, 0)
            current.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


def _extract_params_str(signature: str) -> str | None:
    """Return the text between the signature's outermost parentheses.

    Scans from the first ``(`` to its matching ``)``, so parentheses inside
    defaults (``x: tuple = (1, 2)``) do not end the parameter list early.

    Args:
        signature: Function signature like ``"f(x: int) -> bool"``.

    Returns:
        The parameter list text, or None when there is no ``(``.
    """
    open_idx = signature.find("(")
    if open_idx == -1:
        return None
    depth = 0
    quote: str | None = None
    i = open_idx
    while i < len(signature):
        ch = signature[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch in _OPENERS:
            depth += 1
        elif ch in _CLOSERS:
            depth -= 1
            if depth == 0:
                return signature[open_idx + 1 : i]
        i += 1
    # Unterminated: take everything after "(".
    return signature[open_idx + 1 :]


def parse_function_signature(signature: str) -> list[dict[str, str]]:
    """
    Parse function signature to extract parameter names and types.

    Parameters are split on top-level commas only, so bracketed annotations
    such as ``dict[str, int]`` or ``tuple[int, str]`` and bracketed defaults
    stay one parameter (issue #160). The type keeps any default text
    (``"int = 3"``); normalize_primitive_type and normalize_container_type
    strip it.

    Args:
        signature: Function signature like "f(x: int, y: str) -> bool"

    Returns:
        List of dicts with 'name' and 'type' keys
    """
    params_str = _extract_params_str(signature)
    if params_str is None:
        return []

    params_str = params_str.strip()
    if not params_str:
        return []

    params = []
    for param in _split_top_level(params_str):
        param = param.strip()
        if not param:
            continue  # trailing comma
        # Typed only when the colon comes before any default, so an untyped
        # default containing a colon (sep="a:b") stays one name (mirrors
        # parseSignatureParams in probeArgs.ts)
        colon = param.find(":")
        equals = param.find("=")
        if colon != -1 and (equals == -1 or colon < equals):
            name, type_hint = param[:colon], param[colon + 1 :]
            params.append({"name": name.strip(), "type": type_hint.strip()})
        else:
            name = param.split("=", 1)[0]
            params.append({"name": name.strip(), "type": "Any"})

    return params


def normalize_primitive_type(type_hint: str | None) -> str | None:
    """Map a parameter type hint to a canonical primitive kind.

    Text after ``=`` (a default value) is dropped, then the hint is stripped,
    lowercased and looked up in the alias table. A ``None`` default marks an
    implicit ``Optional`` and is not checked, matching ``Optional[T]``.

    Args:
        type_hint: Raw type hint such as ``"int"``, ``"Number"`` or ``"int = 3"``.

    Returns:
        One of ``"int"``, ``"float"``, ``"bool"``, ``"str"``, or None when the
        hint is missing or not a checked primitive (``Any``, ``list[int]``, ...).
    """
    if not type_hint:
        return None
    base, _, default = type_hint.partition("=")
    if default.strip() == "None":
        return None
    return _PRIMITIVE_ALIASES.get(base.strip().lower())


def _matches_primitive(value: Any, kind: str) -> bool:
    """Check whether a JSON-decoded value satisfies a canonical primitive kind.

    ``bool`` is a subclass of ``int`` in Python, so it is excluded explicitly
    from the numeric kinds.

    Args:
        value: The probe value.
        kind: Canonical kind from normalize_primitive_type.

    Returns:
        True if the value is acceptable for the kind.
    """
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "str":
        return isinstance(value, str)
    return True


_CONTAINER_ALIASES: dict[str, str] = {
    "list": "list",
    "tuple": "tuple",
    "set": "set",
    "dict": "dict",
}


def _split_type_hint(type_hint: str | None) -> str | None:
    """Drop a default from a type hint; None for missing or implicit Optional.

    Args:
        type_hint: Raw type hint such as ``"list[int] = []"``.

    Returns:
        The stripped annotation, or None when the hint is empty or the default
        is ``None`` (an implicit ``Optional``, which is not checked).
    """
    if not type_hint:
        return None
    # "=" never appears inside an annotation, but may appear in a default
    # string, so split at the first top-level "=" only.
    base = _split_top_level(type_hint, "=")[0]
    default = type_hint[len(base) + 1 :] if len(base) < len(type_hint) else ""
    if default.strip() == "None":
        return None
    base = base.strip()
    return base or None


def normalize_container_type(type_hint: str | None) -> dict[str, Any] | None:
    """Map a parameter type hint to a one-level container description.

    Recognises ``list``, ``tuple``, ``set`` and ``dict`` (and the ``typing``
    aliases ``List``, ``Tuple``, ``Set``, ``Dict``; case-insensitive), bare or
    subscripted. Item, key and value kinds are canonical primitive kinds from
    the alias table, or None when the argument is not a primitive (nested
    containers, ``Any``, classes), in which case only the shape is checked.

    ``tuple[T]`` and ``tuple[T, ...]`` are treated as homogeneous tuples of
    ``T``. A fixed-shape tuple such as ``tuple[int, str]`` is checked as shape
    only (no per-position checks).

    ``Optional[...]``, ``X | None`` and a ``None`` default are not containers
    here, so they stay unchecked.

    Args:
        type_hint: Raw type hint such as ``"list[int]"`` or ``"Dict[str, int]"``.

    Returns:
        None when the hint is not a checked container, otherwise
        ``{"kind": "list"|"tuple"|"set", "item": kind|None}`` or
        ``{"kind": "dict", "key": kind|None, "value": kind|None}``.
    """
    base = _split_type_hint(type_hint)
    if base is None:
        return None
    if len(_split_top_level(base, "|")) > 1:
        return None

    bracket = base.find("[")
    if bracket == -1:
        head, args = base, None
    else:
        if not base.endswith("]"):
            return None
        head, args = base[:bracket], base[bracket + 1 : -1]

    kind = _CONTAINER_ALIASES.get(head.strip().lower())
    if kind is None:
        return None

    arg_list = [a.strip() for a in _split_top_level(args)] if args is not None else []

    def _primitive(arg: str) -> str | None:
        return _PRIMITIVE_ALIASES.get(arg.lower())

    if kind == "dict":
        if len(arg_list) == 2:
            return {
                "kind": "dict",
                "key": _primitive(arg_list[0]),
                "value": _primitive(arg_list[1]),
            }
        return {"kind": "dict", "key": None, "value": None}

    item = None
    if len(arg_list) == 1 or (
        kind == "tuple" and len(arg_list) == 2 and arg_list[1] == "..."
    ):
        item = _primitive(arg_list[0])
    return {"kind": kind, "item": item}


def _matches_container(value: Any, spec: dict[str, Any]) -> bool:
    """Check a JSON-decoded value against a normalize_container_type spec.

    list, tuple and set values arrive as JSON arrays. Dict keys arrive as JSON
    object keys, which are always strings, so keys are only checked against a
    ``str`` key kind; other key kinds are not checkable on the wire.

    Args:
        value: The probe value.
        spec: Output of normalize_container_type.

    Returns:
        True if the value has the container shape and every checked item,
        key and value matches its primitive kind.
    """
    if spec["kind"] == "dict":
        if not isinstance(value, dict):
            return False
        key_kind, value_kind = spec["key"], spec["value"]
        if key_kind == "str" and not all(_matches_primitive(k, "str") for k in value):
            return False
        if value_kind and not all(
            _matches_primitive(v, value_kind) for v in value.values()
        ):
            return False
        return True

    if not isinstance(value, list):
        return False
    item_kind = spec["item"]
    if item_kind and not all(_matches_primitive(v, item_kind) for v in value):
        return False
    return True


def _container_description(spec: dict[str, Any]) -> str:
    """Describe a container spec for a revealed-type error message.

    Args:
        spec: Output of normalize_container_type.

    Returns:
        Text such as ``"a list of str"``, ``"a dict of str to int"`` or
        ``"a list"`` when the item kinds are unchecked.
    """
    kind = spec["kind"]
    if kind == "dict":
        if spec["key"] and spec["value"]:
            return f"a dict of {spec['key']} to {spec['value']}"
        return "a dict"
    if spec["item"]:
        return f"a {kind} of {spec['item']}"
    return f"a {kind}"


def validate_probe_input(
    signature: str, probe_input: dict[str, Any], *, reveal_types: bool = True
) -> tuple[bool, str | None]:
    """
    Validate probe input against function signature.

    Parameter names are checked first (missing, then unknown). Then, in
    signature order, each parameter with a primitive type hint (int, float,
    bool, str and their aliases) is checked against its value, and each
    one-level container hint (list/tuple/set/dict, see
    normalize_container_type) is checked for shape and primitive items.
    Other hints (Any, Optional, nested item types, classes) are not checked.

    Args:
        signature: The function signature
        probe_input: Dictionary of parameter name -> value
        reveal_types: When False, type-mismatch messages do not name the
            expected type (used when the signature is hidden from students).

    Returns:
        Tuple of (is_valid, error_message)
    """
    params = parse_function_signature(signature)

    if not params:
        # Can't validate without signature info
        return True, None

    param_names = {p["name"] for p in params}
    input_names = set(probe_input.keys())

    # Check for missing required parameters
    missing = param_names - input_names
    if missing:
        return False, f"Missing required parameters: {', '.join(missing)}"

    # Check for extra parameters
    extra = input_names - param_names
    if extra:
        return False, f"Unknown parameters: {', '.join(extra)}"

    # Check primitive and container types in signature order
    for param in params:
        name = param["name"]
        value = probe_input[name]
        kind = normalize_primitive_type(param["type"])
        if kind is not None:
            if _matches_primitive(value, kind):
                continue
            if not reveal_types:
                return False, f"That value is not valid for parameter '{name}'"
            return False, f"Parameter '{name}' must be {_KIND_ARTICLES[kind]} {kind}"
        spec = normalize_container_type(param["type"])
        if spec is None or _matches_container(value, spec):
            continue
        if not reveal_types:
            return False, f"That value is not valid for parameter '{name}'"
        return False, f"Parameter '{name}' must be {_container_description(spec)}"

    return True, None
