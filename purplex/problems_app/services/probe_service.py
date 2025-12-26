"""
Probe Service for Probeable Code problems.

Handles:
- Oracle execution (running reference_solution with student-provided inputs)
- Probe count tracking in Redis
- Probe limit enforcement based on probe_mode
"""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from purplex.utils.redis_client import get_rate_limit_client

if TYPE_CHECKING:
    from purplex.problems_app.models import ProbeableCodeProblem

logger = logging.getLogger(__name__)

# Redis key prefixes
PROBE_COUNT_PREFIX = "probe:count:"
SUBMISSION_COUNT_PREFIX = "probe:submissions:"
PROBE_HISTORY_PREFIX = "probe:history:"

# TTL for probe data (7 days)
PROBE_DATA_TTL = 60 * 60 * 24 * 7


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
            problem.reference_solution, problem.function_name, probe_input
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
        cls, reference_code: str, function_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute the oracle (reference_solution) with provided arguments.

        Uses a restricted environment to prevent dangerous operations.
        This is synchronous and runs in-memory (no Docker) for fast response.

        Args:
            reference_code: The reference solution code
            function_name: Name of the function to call
            args: Arguments to pass to the function

        Returns:
            Dict with 'success', 'result', 'error' keys
        """
        # Restricted builtins - only safe operations
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "chr": chr,
            "dict": dict,
            "divmod": divmod,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "frozenset": frozenset,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "ord": ord,
            "pow": pow,
            "range": range,
            "reversed": reversed,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "True": True,
            "False": False,
            "None": None,
        }

        # Create restricted globals
        restricted_globals = {
            "__builtins__": safe_builtins,
        }

        try:
            # Execute the function definition
            # nosec B102: exec used with restricted_globals (safe_builtins only, no file/network access)
            exec(reference_code, restricted_globals)  # nosec B102

            # Check if function was defined
            if function_name not in restricted_globals:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Function '{function_name}' not defined in reference solution",
                }

            # Get the function
            func = restricted_globals[function_name]

            # Call the function with provided args
            result = func(**args)

            return {"success": True, "result": result, "error": None}

        except TypeError as e:
            # Usually wrong number/type of arguments
            return {
                "success": False,
                "result": None,
                "error": f"Invalid arguments: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "result": None, "error": str(e)}

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


def parse_function_signature(signature: str) -> list[dict[str, str]]:
    """
    Parse function signature to extract parameter names and types.

    Args:
        signature: Function signature like "f(x: int, y: str) -> bool"

    Returns:
        List of dicts with 'name' and 'type' keys
    """
    # Extract the part between parentheses
    match = re.search(r"\(([^)]*)\)", signature)
    if not match:
        return []

    params_str = match.group(1).strip()
    if not params_str:
        return []

    params = []
    for param in params_str.split(","):
        param = param.strip()
        if ":" in param:
            name, type_hint = param.split(":", 1)
            params.append({"name": name.strip(), "type": type_hint.strip()})
        else:
            params.append({"name": param, "type": "Any"})

    return params


def validate_probe_input(
    signature: str, probe_input: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate probe input against function signature.

    Args:
        signature: The function signature
        probe_input: Dictionary of parameter name -> value

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

    return True, None
